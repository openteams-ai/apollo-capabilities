# Collab programs

A collection of reusable [Nebi](https://nebi.nebari.dev) programs — self-contained `pixi.toml` files that define a launch task and dependencies for common workflows.

## Structure

```
spec/
  README.md
  SCHEMA.md
  program.schema.json
programs/
  <program-name>/
    pixi.toml
```

Each program lives in its own directory and is a standalone pixi project. The `spec/` directory contains the program standard; `programs/` contains only program implementations.

## Included programs

- `getting-started` - a welcome and getting started guide for Collab programs
- `jupyterlab` — launches JupyterLab with a base data stack
- `llamacpp` -  Runs a local llama.cpp server that automatically downloads model GGUFs from HuggingFace.
- `comfyui` - Runs a local ComfyUI server with base models.
- `data-explorer` — upload a CSV, browse it as a table, and chat with the data using a local LLM (llama.cpp, Ollama, or Docker Model Runner).
- `document-summarizer` — upload a document (txt, md, pdf, docx) and summarize it with a local llama.cpp LLM.

## Usage

### From the OCI registry (recommended)

programs are published to `quay.io/openteams_programs`. Import one directly with [Nebi](https://nebi.nebari.dev):

```sh
nebi import quay.io/openteams_programs/getting-started:latest
```

Then run it:

```sh
pixi run launch
```

### Local usage

Clone this repository, navigate into any program directory, and run its tasks with pixi:

```sh
cd programs/hello-world
pixi run launch
```

## Adding a program

1. Create a new directory under `programs/`.
2. Add a `pixi.toml` following the specification in [`spec/SCHEMA.md`](spec/SCHEMA.md) and [`spec/program.schema.json`](spec/program.schema.json).
3. Optionally add a `README.md` documenting tasks and any environment variables.

## Specification

The program standard lives under [`spec/`](spec/):

- [`spec/README.md`](spec/README.md) — overview of the specification artifacts
- [`spec/SCHEMA.md`](spec/SCHEMA.md) — human-readable schema, semantics, and conventions
- [`spec/program.schema.json`](spec/program.schema.json) — machine-readable JSON Schema for validating parsed manifests

The root README intentionally keeps only a short summary so the specification does not drift across multiple copies.
