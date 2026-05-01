## Research Assistant

A web-based research agent that takes a topic, searches the web, and synthesizes findings into a structured Markdown answer with citations. Supports follow-up questions, five output modes, and optional MCP exports to Notion / Linear / HubSpot.

The LLM provider is fully configurable at runtime — point it at any OpenAI-compatible endpoint (OpenAI, Groq, Together, OpenRouter, Ollama, LM Studio, llama.cpp, …) by entering a base URL, API key, and model name in the UI. Configuration is persisted in the browser and sent with each request.

Requires:
- [`pixi`](https://pixi.sh/latest/#installation)
- [`bun`](https://bun.sh) (`curl -fsSL https://bun.sh/install | bash`)

```bash
pixi run setup    # install frontend deps once
pixi run dev      # boots backend (8000) + frontend (5173)
```

Open http://localhost:5173.

### Workflow

1. Click **Provider** in the top right and configure a base URL, API key, and model. Use the presets to pre-fill common providers, then click **Test connection** to populate the model dropdown.
2. Type a research topic and pick an output mode (Summary, Report, Pros & Cons, Timeline, Open Questions).
3. Click **Research**. The agent runs `web_search` against the configured search backend, streams the draft as it writes, and posts the final synthesized result with citations.
4. Use the follow-up bar to extend the conversation in the same session.
5. Click **Save to Notion / Linear / HubSpot** on a result to export via MCP (requires backend env config — see below).

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

> ⚠ Your API key is stored in the browser's `localStorage`. Don't enter sensitive keys on shared machines.

### Web search backends

Configure via environment variables (copy `.env.example` to `.env`):

| `SEARCH_PROVIDER` | Required key | Notes |
|---|---|---|
| `tavily` | `TAVILY_API_KEY` | Best quality. Recommended. |
| `serper` | `SERPER_API_KEY` | Good quality. |
| `duckduckgo` | none | Default fallback. Limited results. |

If `SEARCH_PROVIDER` is unset, the backend picks the highest-quality provider whose key is present, falling back to DuckDuckGo.

### MCP exports

Exports use the Anthropic SDK to talk to MCP servers (independent of your LLM provider). To enable, set in `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
NOTION_MCP_URL=https://mcp.notion.com/mcp
LINEAR_MCP_URL=https://mcp.linear.app/sse
HUBSPOT_MCP_URL=https://mcp.hubspot.com/...
```

If the relevant URL or `ANTHROPIC_API_KEY` is missing, the export button reports a clear inline error rather than failing opaquely.

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
│   │   ├── research.py        # POST/GET /api/research/...
│   │   └── export.py          # POST /api/research/{id}/export
│   └── agents/
│       ├── runner.py          # agentic loop, AsyncOpenAI per request
│       ├── search.py          # tavily / serper / duckduckgo
│       └── synthesizer.py     # output-mode reformatting
└── frontend/
    ├── package.json
    ├── vite.config.ts         # proxies /api → :8000
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
