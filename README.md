# Apollo Capabilities

A collection of reusable [Nebi](https://nebi.nebari.dev) capabilities — self-contained `pixi.toml` files that define a launch task and dependencies for common workflows.

## Structure

```
capabilities/
  <capability-name>/
    pixi.toml
```

Each capability lives in its own directory and is a standalone pixi project.

## Included capabilities

- `hello-world` — minimal capability that prints a greeting
- `jupyterlab` — launches JupyterLab with a base data stack
- `opencv-webcam` — webcam face detection demo (from Pixi OpenCV example, webcam capture only)

## Usage

### From the OCI registry (recommended)

Capabilities are published to `quay.io/openteams_capabilities`. Import one directly with [Nebi](https://nebi.nebari.dev):

```sh
nebi import quay.io/openteams_capabilities/hello-world:latest
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
2. Add a `pixi.toml` following the schema below.
3. Optionally add a `README.md` documenting tasks and any environment variables.

## `pixi.toml` Capability Schema

For the complete schema reference, see [`capabilities/SCHEMA.md`](capabilities/SCHEMA.md).

Every capability is a standard pixi workspace with an additional keyed capability section under `[tool.capability.<capability-key>]` (for example, `[tool.capability.jupyterlab]`).

```toml
[workspace]
name = "<capability-name>"
version = "0.1.0"
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64", "osx-64", "win-64"]

[dependencies]
# conda-forge packages required by this capability

[tool.capability.<capability-key>]
spec-version = 1
name = "<Human Readable Name>"
description = "<Short description of what this capability does>"
icon = "<URL to an icon image>"  # optional
author = { name = "<Author>", email = "<email>" }
deployment = ["local", "hub"]
tags = ["tag1", "tag2"] # optional

[tool.capability.<capability-key>.entrypoint]
type = "task"
task = "launch"
environment = "default" # optional, defaults to "default"

[tool.capability.<capability-key>.execution]
target = "local" # local | hub

[tasks]
launch = { cmd = "<command to run>" }
```

### `[tool.capability.<capability-key>]` Fields

| Field | Required | Description |
|---|---|---|
| `spec-version` | Yes | Schema version. Currently `1`. |
| `name` | Yes | Human-readable display name. |
| `description` | Yes | Short description of the capability. |
| `icon` | No | URL to an icon image. |
| `author` | No | Author name and email. |
| `deployment` | Yes | Deployment targets. Valid values: `"local"`, `"hub"`. |
| `tags` | No | Tags to support marketplace metadata. |

### `[tool.capability.<capability-key>.entrypoint]` Fields

| Field | Required | Description |
|---|---|---|
| `type` | Yes | Entrypoint type. Currently `"task"`. |
| `task` | Yes | Pixi task to run when launching the capability. |
| `environment` | No | Pixi environment to run in. Defaults to `"default"`. |

### `[tool.capability.<capability-key>.execution]` Fields

| Field | Required | Description |
|---|---|---|
| `target` | Yes | Execution target. Valid values: `"local"`, `"hub"`. |

### Capability key + compatibility note

The `<capability-key>` should be the capability identifier (typically the workspace name), e.g. `jupyterlab` in `[tool.capability.jupyterlab]`.

For unreleased manifests still on `spec-version = 1`, older runtimes may continue to infer defaults (`launch` + `local`) when explicit `entrypoint`/`execution` fields are missing. New capabilities should set these fields explicitly.
