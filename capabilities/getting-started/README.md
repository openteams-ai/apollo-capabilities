# Getting Started

A welcome and getting started guide for Collab capabilities, served as a local web app.

Collab capabilities are made up of two kinds of reusable building blocks:

- **Progs** (Programs) are runnable apps, workflows, services, notebooks, and tools. They may use Cogs, but they do not have to.
- **Cogs** (Cognitive Workers) are AI-based workers: agents, assistants, model-backed automations, and other reusable cognitive services.

The examples in this repository are currently Progs. Future Cogs will live in the same capability catalog and can be launched directly or composed into Progs.

## Usage

```sh
pixi run launch
```

Opens a local web page at `http://localhost:8766` with:

- An overview of Progs and Cogs
- Step-by-step instructions for launching a capability
- Guidance for creating a new Prog or Cog
