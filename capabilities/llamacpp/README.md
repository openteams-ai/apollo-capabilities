## Local LLM Server

A [pixi](https://pixi.sh)-based workflow downloads a precompiled [llama.cpp](https://github.com/ggml-org/llama.cpp) binary and model files, then launches a local inference server.

Requires: `pixi` ([install](https://pixi.sh/latest/#installation))

```bash
# CPU-only (all platforms)
pixi run serve

# GPU-accelerated (Vulkan on Linux, Metal on macOS, CUDA on Windows)
pixi run -e gpu serve
```

This automatically downloads the correct llama.cpp build for your platform, the model GGUF, and the mmproj file on first run. Subsequent runs skip downloads. The server listens on llama.cpp's default port 8080.

| Platform | `default` (CPU) | `gpu` |
|---|---|---|
| Linux x64 | Generic CPU build | Vulkan |
| macOS ARM (M-series) | CPU-only | Metal (built-in) |
| Windows x64 | CPU build | CUDA (auto-detected) |

The GPU environment requires a CUDA 12+ driver on Linux/Windows. On Windows, the download script detects your local CUDA version via `nvidia-smi` and picks the highest compatible build. To override detection: `CONDA_OVERRIDE_CUDA=12.4 pixi run -e gpu serve`.

To download assets without starting the server: `pixi run download` (or `pixi run -e gpu download`).

This set of tasks currently targets a q4 gemma4-26B MoE, which will need 24GB VRAM or URAM to fully run from GPU/metal. We may want to target a low-memory option as well in future versions.
