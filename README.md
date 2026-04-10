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

Every capability is a standard pixi workspace with an additional keyed capability section under `[tool.capability.<capability-key>]` (for example, `[tool.capability.jupyterlab]`). Launch is always done through Pixi tasks; task execution is implicit in the schema.

```toml
[workspace]
name = "<capability-name>"
version = "0.1.0"
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64", "osx-64", "win-64"]

[dependencies]
# conda-forge packages required by this capability

[tool.capability.<capability-key>]
spec-version = "0.1.0"
name = "<Human Readable Name>"
description = "<Short description of what this capability does>"
icon = "<URL to an icon image>"  # optional
author = { name = "<Author>", email = "<email>" }
tags = ["tag1", "tag2"] # optional

[tool.capability.<capability-key>.execution]
default-target = "local"

[tool.capability.<capability-key>.execution.targets.local]
task = "launch"
environment = "default" # optional, defaults to "default"

[tool.capability.<capability-key>.execution.targets.hub]
task = "launch-hub"
environment = "default" # optional, defaults to "default"

[tasks]
launch = { cmd = "<command to run>" }
launch-hub = { cmd = "<command to run on hub>" } # optional
```

### `[tool.capability.<capability-key>]` Fields

| Field | Required | Description |
|---|---|---|
| `spec-version` | Yes | Schema version as a semver-style string. Currently `"0.1.0"` to indicate the schema is still under development. |
| `name` | Yes | Human-readable display name. |
| `description` | Yes | Short description of the capability. |
| `icon` | No | URL to an icon image. |
| `author` | No | Author name and email. |
| `tags` | No | Tags to support marketplace metadata. |

### `[tool.capability.<capability-key>.execution]` Fields

| Field | Required | Description |
|---|---|---|
| `default-target` | Yes | Default execution target. Must match a key under `execution.targets`. Valid values are currently `"local"` and `"hub"`. |

### `[tool.capability.<capability-key>.execution.targets.<target>]` Fields

| Field | Required | Description |
|---|---|---|
| `task` | Yes | Pixi task to run when launching on this target. |
| `environment` | No | Pixi environment to run in. Defaults to `"default"`. |

### Capability key + compatibility note

The `<capability-key>` should be the capability identifier (typically the workspace name), e.g. `jupyterlab` in `[tool.capability.jupyterlab]`.

For unreleased manifests, the schema uses `spec-version = "0.1.0"` to make its pre-1.0, evolving status explicit. Older runtimes may continue to project legacy `entrypoint`, `deployment`, and `execution.target` fields into this shape. New capabilities should define `execution.targets` explicitly.
