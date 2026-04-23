## Local ComfyUI Server

A [pixi](https://pixi.sh)-based workflow installs [ComfyUI](https://github.com/comfyanonymous/ComfyUI) via [comfy-cli](https://github.com/Comfy-Org/comfy-cli) - which auto-selects the GPU-specific PyTorch wheel - and fetches the [`z_image_turbo`](https://huggingface.co/Comfy-Org/z_image_turbo) model set for a ready-to-run default.

Requires: `pixi` ([install](https://pixi.sh/latest/#installation))

```bash
# End-to-end: install (if needed), pull default models (if needed), launch GUI.
# Default port: 8188.
pixi run serve
```

On first run `serve` clones the latest ComfyUI release into `./ComfyUI/`, installs torch and all requirements via `comfy install --fast-deps`, and downloads the z_image_turbo diffusion model, qwen_3_4b text encoder, and ae VAE into `ComfyUI/models/`. On subsequent runs those steps short-circuit on existing files and the GUI launches immediately.

| Platform | Backend |
|---|---|
| Linux x64 | NVIDIA CUDA (auto-detected via `nvidia-smi`) |
| Windows x64 | NVIDIA CUDA (auto-detected via `nvidia-smi`) |
| macOS ARM (M-series) | MPS (Apple Silicon) |

### Running z_image_turbo

On first launch the GUI opens to ComfyUI's built-in default graph. To run z_image_turbo, grab `zimage_turbo_workflow.json` (the example workflow) from the [Comfy-Org/z_image_turbo](https://huggingface.co/Comfy-Org/z_image_turbo) HuggingFace repo and drag it onto the ComfyUI browser window - the nodes reference the filenames already staged under `ComfyUI/models/`, so it runs without further wiring.

### Sub-tasks

To run setup without launching the GUI: `pixi run initialize` (install + model download only). To re-run a single stage: `pixi run install-comfyui` or `pixi run download-models`.

Analytics/tracking is disabled via `comfy tracking disable` before every install and launch.
