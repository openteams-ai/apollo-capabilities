## Research Assistant

A web-based research agent that takes a topic, searches the web, and synthesizes findings into a structured Markdown answer with citations. Supports follow-up questions and five output modes.

The LLM provider is fully configurable at runtime — point it at any OpenAI-compatible endpoint (Ollama, llama.cpp, Docker Model Runner, OpenRouter, …) by entering a base URL, API key, and model name in the UI. Configuration is persisted in the browser and sent with each request.

Web search runs against DuckDuckGo via the `ddgs` library — no API key required.

Requires:
- [`pixi`](https://pixi.sh/latest/#installation)

```bash
pixi run launch
```

Open http://localhost:8765. The pre-built frontend is served by the FastAPI backend, so no Node/Bun toolchain is needed to run the app.

### Rebuilding the frontend (maintainers only)

The committed `frontend/dist/` is what the backend serves. After changing anything under `frontend/src/`, rebuild it with whichever JS package manager you prefer:

```bash
cd frontend
npm install && npm run build   # or bun install && bun run build
```

### Workflow

1. Click **Provider** in the top right and configure a base URL, API key, and model. Use the presets to pre-fill common providers, then click **Test connection** to populate the model dropdown.
2. Type a research topic and pick an output mode (Summary, Report, Pros & Cons, Timeline, Open Questions).
3. Click **Research**. The agent calls `web_search`, streams the draft as it writes, and posts the final synthesized result with citations.
4. Use the follow-up bar to extend the conversation in the same session.

### Output modes

| Mode | What you get |
|---|---|
| Summary | TL;DR paragraph + 5 bullet points |
| Report | Sectioned report with H2 headings and inline citations |
| Pros & Cons | Markdown table with two columns |
| Timeline | Chronological bulleted list with bold dates |
| Open Questions | Numbered list of gaps and unresolved questions |

### Provider examples

| Provider | Base URL | API key |
|---|---|---|
| llama.cpp (local) | `http://localhost:8080/v1` | any string |
| Ollama (local) | `http://localhost:11434/v1` | any string |
| Docker (local) | `http://localhost:12434/engines/v1` | any string |
| Custom (OpenAI spec) | _your endpoint_ | as required |
| OpenRouter | `https://openrouter.ai/api/v1` | required |

> The API key is held in memory only — base URL and model are persisted to `localStorage`, but the key is cleared on every page reload and must be re-entered.

### Architecture

```
research-assistant/
├── pixi.toml                  # api/ui/dev/setup tasks
├── backend/
│   ├── main.py                # FastAPI app + CORS
│   ├── models.py              # Pydantic request/response models
│   ├── sessions.py            # in-memory session store
│   ├── routers/
│   │   ├── provider.py        # GET /api/provider/models
│   │   └── research.py        # POST/GET /api/research/...
│   └── agents/
│       ├── runner.py          # agentic loop, AsyncOpenAI per request
│       ├── search.py          # DuckDuckGo via ddgs
│       └── synthesizer.py     # output-mode reformatting
└── frontend/
    ├── package.json
    ├── vite.config.ts         # proxies /api → :8765 (dev only)
    └── src/
        ├── App.tsx
        ├── store/providerStore.ts   # Zustand + localStorage persist
        ├── api/client.ts            # typed fetch + EventSource helper
        └── components/
            ├── ProviderConfig.tsx
            ├── QueryBar.tsx
            ├── StreamPanel.tsx
            ├── ResultView.tsx
            └── FollowUpBar.tsx
```

### Notes

- A new `AsyncOpenAI` client is instantiated **per request** using the provider config sent from the UI. No global client is cached.
- Sessions are stored in-process; restarting the backend drops all in-flight conversations.
- The agent loop runs at most 6 tool-call iterations per turn before forcing a final answer.
