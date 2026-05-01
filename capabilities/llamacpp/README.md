## Local LLM Server

A [pixi](https://pixi.sh)-based workflow downloads a precompiled [llama.cpp](https://github.com/ggml-org/llama.cpp) binary, pre-caches the selected model and mmproj GGUFs from HuggingFace with visible terminal status, then launches a local inference server.

Requires: `pixi` ([install](https://pixi.sh/latest/#installation))

```bash
# CPU-only (all platforms) — defaults to gemma-4-E4B Q4_K_M
pixi run serve

# GPU-accelerated (Vulkan on Linux, Metal on macOS, CUDA on Windows)
pixi run -e gpu serve

# Specify a different model
pixi run serve unsloth/gemma-4-26B-A4B-it-GGUF:Q4_K_M
pixi run -e gpu serve unsloth/gemma-4-26B-A4B-it-GGUF:Q4_K_M
```

This automatically downloads the correct llama.cpp build for your platform on first run. Before the server starts, a Python launcher checks the selected HuggingFace repo, pre-caches the matching model and mmproj GGUFs into a local `models/` HF cache (`HF_HOME=models`), and streams cache/download status to the terminal. Subsequent runs use the cached files. The server listens on llama.cpp's default port 8080.

The default model is [`unsloth/gemma-4-E4B-it-GGUF:Q4_K_M`](https://huggingface.co/unsloth/gemma-4-E4B-it-GGUF). Pass any HuggingFace GGUF repo as a positional argument to override (see examples above).

| Platform | `default` (CPU) | `gpu` |
|---|---|---|
| Linux x64 | Generic CPU build | Vulkan |
| macOS ARM (M-series) | CPU-only | Metal (built-in) |
| Windows x64 | CPU build | CUDA (auto-detected) |

The GPU environment requires a CUDA 12+ driver on Linux/Windows. On Windows, the download script detects your local CUDA version via `nvidia-smi` and picks the highest compatible build. To override detection: `CONDA_OVERRIDE_CUDA=12.4 pixi run -e gpu serve`.

To download just the llama.cpp binary without starting the server: `pixi run download-llamacpp` (or `pixi run -e gpu download-llamacpp`). Model GGUFs are fetched with visible progress on first `serve`.
