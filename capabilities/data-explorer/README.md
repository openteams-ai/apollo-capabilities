## Data Explorer

A [pixi](https://pixi.sh)-based [Streamlit](https://streamlit.io) app that lets you upload a CSV, browse it as a pandas table, and chat with the data through a local LLM (or any OpenAI-compatible remote API).

Requires: `pixi` ([install](https://pixi.sh/latest/#installation))

```bash
pixi run launch
```

Streamlit listens on `http://localhost:8501` by default.

### Workflow

1. Upload a CSV in the sidebar — or click **Load sample data** to load the bundled `sample_orders.csv` (120 rows of synthetic e-commerce orders) for a quick demo.
2. Pick a provider — `llama.cpp`, `Ollama`, `Docker Model Runner`, or a remote OpenAI-compatible API.
3. Click **Scan for running models** to populate the model selector with whatever the provider currently has loaded.
4. Ask questions about the data in the chat panel.

The app keeps the dataframe in memory and forwards a compact context (schema, the first 20 rows, and `df.describe()`) to the model on each turn. For datasets where the full table matters, the assistant is prompted to say so rather than fabricating an answer.

> ⚠ **Picking the remote provider sends your data off this device** — the schema, first 20 rows, and summary statistics will be transmitted to whatever API host you point it at. Use a local provider if your CSV contains anything sensitive.

### Supported providers

| Provider | Default URL | Model discovery endpoint | OpenAI base URL | API key |
|---|---|---|---|---|
| llama.cpp | `http://localhost:8080` | `GET /v1/models` | `/v1` | — |
| Ollama | `http://localhost:11434` | `GET /api/tags` | `/v1` | — |
| Docker Model Runner | `http://localhost:12434` | `GET /engines/v1/models` | `/engines/v1` | — |
| Remote (OpenAI-compatible) | `https://api.openai.com/v1` | `GET /models` | (base URL itself) | required |

The base URL is editable in the sidebar if you've moved a provider off its default port or want to point the remote provider at a different host (Together, Groq, etc.). All four runtimes expose an OpenAI-compatible `chat/completions` endpoint, so the app uses the `openai` SDK with the appropriate `base_url`.

### Companion capabilities

- The [`llamacpp`](../llamacpp) capability in this repo runs a llama.cpp server on `http://localhost:8080` — start it (`pixi run -e gpu serve` or `pixi run serve`) and Data Explorer's default llama.cpp settings will Just Work.
- For Ollama, install [Ollama](https://ollama.com) and `ollama pull` any model. The desktop app starts the daemon for you.
- For Docker Model Runner, enable Model Runner in Docker Desktop settings and `docker model pull <model>`.
