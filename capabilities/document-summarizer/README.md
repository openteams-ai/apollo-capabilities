## Document Summarizer

A [pixi](https://pixi.sh)-based [Streamlit](https://streamlit.io) app that lets you upload a document (txt, md, pdf, docx), parses it to plain text, and generates a summary using a local LLM ([llama.cpp](https://github.com/ggerganov/llama.cpp), [Ollama](https://ollama.com), or [Docker Model Runner](https://docs.docker.com/desktop/features/model-runner/)) — or any OpenAI-compatible remote API.

Requires: `pixi` ([install](https://pixi.sh/latest/#installation))

```bash
pixi run launch
```

Streamlit listens on `http://localhost:8501` by default.

### Workflow

1. Pick a provider in **Settings** — llama.cpp, Ollama, Docker Model Runner, or a remote OpenAI-compatible API.
2. Click **Scan for running models** to populate the model selector with whatever the provider currently exposes.
3. Upload a `.txt`, `.md`, `.pdf`, or `.docx` document — or click **Load sample document** to try the bundled example.
4. Pick a summary length and click **Generate summary**. The summary streams back into the right-hand panel.

> ⚠ **Picking the remote provider sends your full document off this device** — the entire extracted text is transmitted to whatever API host you point it at. Use a local provider if the document is sensitive.

### Supported providers

| Provider | Default URL | Model discovery endpoint | OpenAI base URL | API key |
|---|---|---|---|---|
| llama.cpp | `http://localhost:8080` | `GET /v1/models` | `/v1` | — |
| Ollama | `http://localhost:11434` | `GET /api/tags` | `/v1` | — |
| Docker Model Runner | `http://localhost:12434` | `GET /engines/v1/models` | `/engines/v1` | — |
| Remote (OpenAI-compatible) | `https://api.openai.com/v1` | `GET /models` | (base URL itself) | required |

### Supported file types

| Extension | Parser |
|---|---|
| `.txt`, `.md` | Decoded as UTF-8 (with utf-16 / latin-1 fallback) |
| `.pdf` | [`pypdf`](https://pypdf.readthedocs.io) text extraction, page by page |
| `.docx` | [`python-docx`](https://python-docx.readthedocs.io) — paragraphs and tables |

The full extracted text is sent to the chosen provider as the user message. Make sure the model has a context window large enough for the document; the default `gemma-4-E4B-it` model in the companion `llamacpp` capability is configured with an 8k–24k context.

### Companion capability

The [`llamacpp`](../llamacpp) capability in this repo runs a llama.cpp server on `http://localhost:8080`. Start it in another terminal with:

```bash
cd ../llamacpp
pixi run serve         # CPU
pixi run -e gpu serve  # GPU (Vulkan / Metal / CUDA)
```

Document Summarizer's default base URL (`http://localhost:8080`) will then connect to it without further configuration.
