## Document Summarizer

A [pixi](https://pixi.sh)-based [Streamlit](https://streamlit.io) app that lets you upload a document (txt, md, pdf, docx), parses it to plain text, and generates a summary using a local [llama.cpp](https://github.com/ggerganov/llama.cpp) server.

Requires: `pixi` ([install](https://pixi.sh/latest/#installation))

```bash
pixi run launch
```

Streamlit listens on `http://localhost:8501` by default.

### Workflow

1. Start a local llama.cpp server (see [Companion capability](#companion-capability) below) listening on `http://localhost:8080`.
2. Click **Scan for running models** in **Settings** to populate the model selector.
3. Upload a `.txt`, `.md`, `.pdf`, or `.docx` document — or click **Load sample document** to try the bundled example.
4. Pick a summary length and click **Generate summary**. The summary streams back into the right-hand panel.

### Supported file types

| Extension | Parser |
|---|---|
| `.txt`, `.md` | Decoded as UTF-8 (with utf-16 / latin-1 fallback) |
| `.pdf` | [`pypdf`](https://pypdf.readthedocs.io) text extraction, page by page |
| `.docx` | [`python-docx`](https://python-docx.readthedocs.io) — paragraphs and tables |

The full extracted text is sent to llama.cpp as the user message. Make sure the model you load has a context window large enough for the document; the default `gemma-4-E4B-it` model in the companion `llamacpp` capability is configured with an 8k–24k context.

### Companion capability

The [`llamacpp`](../llamacpp) capability in this repo runs a llama.cpp server on `http://localhost:8080`. Start it in another terminal with:

```bash
cd ../llamacpp
pixi run serve         # CPU
pixi run -e gpu serve  # GPU (Vulkan / Metal / CUDA)
```

Document Summarizer's default base URL (`http://localhost:8080`) will then connect to it without further configuration.
