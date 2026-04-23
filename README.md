# Apollo Capabilities

A collection of reusable [Nebi](https://nebi.nebari.dev) capabilities — self-contained `pixi.toml` files that define a launch task and dependencies for common workflows.

## Structure

```
spec/
  README.md
  SCHEMA.md
  capability.schema.json
capabilities/
  <capability-name>/
    pixi.toml
```

Each capability lives in its own directory and is a standalone pixi project. The `spec/` directory contains the capability standard; `capabilities/` contains only capability implementations.

## Included capabilities

- `getting-started` - a welcome and getting started guide for Apollo capabilities
- `jupyterlab` — launches JupyterLab with a base data stack
- `opencv-webcam` — webcam face detection demo (from Pixi OpenCV example, webcam capture only)
- `llamacpp` -  Runs a local llama.cpp server that automatically downloads model GGUFs from HuggingFace.
- `comfyui` - Runs a local ComfyUI server with base models.

## Usage

### From the OCI registry (recommended)

Capabilities are published to `quay.io/openteams_capabilities`. Import one directly with [Nebi](https://nebi.nebari.dev):

```sh
nebi import quay.io/openteams_capabilities/getting-started:latest
```

Then run it:

```sh
pixi run launch
```

### Local usage

Clone this repository, navigate into any capability directory, and run its tasks with pixi:

```sh
cd capabilities/hello-world
pixi run launch
```

## Adding a Capability

1. Create a new directory under `capabilities/`.
2. Add a `pixi.toml` following the specification in [`spec/SCHEMA.md`](spec/SCHEMA.md) and [`spec/capability.schema.json`](spec/capability.schema.json).
3. Optionally add a `README.md` documenting tasks and any environment variables.

## Specification

The capability standard lives under [`spec/`](spec/):

- [`spec/README.md`](spec/README.md) — overview of the specification artifacts
- [`spec/SCHEMA.md`](spec/SCHEMA.md) — human-readable schema, semantics, and conventions
- [`spec/capability.schema.json`](spec/capability.schema.json) — machine-readable JSON Schema for validating parsed manifests

The root README intentionally keeps only a short summary so the specification does not drift across multiple copies.
