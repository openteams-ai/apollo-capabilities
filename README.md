# Collab Capabilities

A collection of reusable [Nebi](https://nebi.nebari.dev) capabilities packaged as self-contained `pixi.toml` projects. Capabilities are organized into two kinds:

- **Progs** (Programs) are apps, workflows, services, notebooks, and other runnable tools. A Prog may use one or more Cogs, but it does not have to.
- **Cogs** (Cognitive Workers) are AI-based workers: agents, assistants, model-backed automations, and other cognitive services that can be used directly or composed into Progs.

Together, Progs and Cogs make up the capability catalog: Progs provide usable surfaces and workflows, while Cogs provide reusable AI labor that other capabilities can call on.

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

Each capability lives in its own directory and is a standalone pixi project. The `spec/` directory contains the capability standard; `capabilities/` contains capability implementations for Progs and Cogs.

## Included capabilities

Current examples are Progs:

- `getting-started` - a welcome and getting started guide for Collab capabilities
- `jupyterlab` — launches JupyterLab with a base data stack
- `llamacpp` -  Runs a local llama.cpp server that automatically downloads model GGUFs from HuggingFace.
- `comfyui` - Runs a local ComfyUI server with base models.
- `data-explorer` — upload a CSV, browse it as a table, and chat with the data using a local LLM (llama.cpp, Ollama, or Docker Model Runner).
- `document-summarizer` — upload a document (txt, md, pdf, docx) and summarize it with a local llama.cpp LLM.

Cogs will appear in the same catalog as agent-style AI workers that can be launched on their own or used by Progs.

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
cd capabilities/getting-started
pixi run launch
```

## Adding a Capability

1. Create a new directory under `capabilities/`.
2. Decide whether the capability is a **Prog** or a **Cog**. Use Prog for an app, workflow, notebook, service, or other user-facing program; use Cog for an AI-based worker, agent, assistant, or cognitive service.
3. Add a `pixi.toml` following the specification in [`spec/SCHEMA.md`](spec/SCHEMA.md) and [`spec/capability.schema.json`](spec/capability.schema.json).
4. Optionally add a `README.md` documenting tasks, environment variables, and any Prog/Cog relationships.

## Specification

The capability standard lives under [`spec/`](spec/):

- [`spec/README.md`](spec/README.md) — overview of the specification artifacts
- [`spec/SCHEMA.md`](spec/SCHEMA.md) — human-readable schema, semantics, and conventions
- [`spec/capability.schema.json`](spec/capability.schema.json) — machine-readable JSON Schema for validating parsed manifests

The root README intentionally keeps only a short summary so the specification does not drift across multiple copies.
