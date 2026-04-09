# Capability Schema (spec-version = 1)

Apollo capabilities are Pixi manifests (`pixi.toml`) with keyed capability metadata under:

- `[tool.capability.<capability-key>]`
- `[tool.capability.<capability-key>.entrypoint]`
- `[tool.capability.<capability-key>.execution]`

> Note: This repo is still unreleased, so the schema remains on `spec-version = 1`.

## Full shape

```toml
[workspace]
name = "<capability-name>"
version = "0.1.0"
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64", "osx-64", "win-64"]

[tool.capability.<capability-key>]
spec-version = 1
name = "<Human Readable Name>"
description = "<Short description>"
icon = "<URL>" # optional
author = { name = "<Name>", email = "<email>" } # optional
deployment = ["local", "hub"]
tags = ["tag1", "tag2"] # optional

[tool.capability.<capability-key>.entrypoint]
type = "task"
task = "launch"
environment = "default" # optional, defaults to default

[tool.capability.<capability-key>.execution]
target = "local" # local | hub

[tasks]
launch = { cmd = "<command>" }
```

## Field reference

## `[tool.capability.<capability-key>]`

| Field | Required | Description |
|---|---|---|
| `spec-version` | Yes | Schema version (currently `1`). |
| `name` | Yes | Human-readable display name. |
| `description` | Yes | Short capability description. |
| `icon` | No | Icon URL. |
| `author` | No | Author metadata (`name`, `email`). |
| `deployment` | Yes | Supported deployment targets. Values: `local`, `hub`. |
| `tags` | No | Discovery/marketplace tags. |

## `[tool.capability.<capability-key>.entrypoint]`

| Field | Required | Description |
|---|---|---|
| `type` | Yes | Entrypoint kind. Currently only `task`. |
| `task` | Yes | Pixi task name used to launch capability. |
| `environment` | No | Pixi environment name. Defaults to `default`. |

## `[tool.capability.<capability-key>.execution]`

| Field | Required | Description |
|---|---|---|
| `target` | Yes | Preferred execution target (`local` or `hub`). |

## Capability key

`<capability-key>` is the unique capability identifier (typically equal to `workspace.name`).

Example:

- `[tool.capability.jupyterlab]`

## Compatibility defaults

Older manifests that omit explicit sections can still be interpreted with defaults:

- `entrypoint.type = "task"`
- `entrypoint.task = "launch"`
- `entrypoint.environment = "default"`
- `execution.target = "local"` if present in `deployment`, otherwise first deployment value
