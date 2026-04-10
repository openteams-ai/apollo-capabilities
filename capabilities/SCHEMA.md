# Capability Schema (spec-version = 1)

Apollo capabilities are Pixi manifests (`pixi.toml`) with keyed capability metadata under:

- `[tool.capability.<capability-key>]`
- `[tool.capability.<capability-key>.execution]`
- `[tool.capability.<capability-key>.execution.targets.<target>]`

> Note: This repo is still unreleased, so the schema remains on `spec-version = 1`.
>
> Capabilities are launched via Pixi tasks; task execution is implicit in the schema.

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
tags = ["tag1", "tag2"] # optional

[tool.capability.<capability-key>.execution]
default-target = "local"

[tool.capability.<capability-key>.execution.targets.local]
task = "launch"
environment = "default" # optional, defaults to default

[tool.capability.<capability-key>.execution.targets.hub]
task = "launch-hub"
environment = "default" # optional, defaults to default

[tasks]
launch = { cmd = "<command>" }
launch-hub = { cmd = "<command>" } # optional, only if hub differs
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
| `tags` | No | Discovery/marketplace tags. |

## `[tool.capability.<capability-key>.execution]`

| Field | Required | Description |
|---|---|---|
| `default-target` | Yes | Default execution target. Must match a key under `execution.targets`. Valid target values are currently `local` and `hub`. |

## `[tool.capability.<capability-key>.execution.targets.<target>]`

| Field | Required | Description |
|---|---|---|
| `task` | Yes | Pixi task name used to launch the capability on this target. |
| `environment` | No | Pixi environment name. Defaults to `default`. |

## Supported target keys

`<target>` is currently one of:

- `local`
- `hub`

A capability supports exactly the targets it defines under `execution.targets`.

## Capability key

`<capability-key>` is the unique capability identifier (typically equal to `workspace.name`).

Example:

- `[tool.capability.jupyterlab]`

## Compatibility defaults

Older manifests that used `entrypoint`, `deployment`, and `execution.target` can still be projected into the new shape:

- `entrypoint.task` -> each projected target's `task`
- `entrypoint.environment` -> each projected target's `environment`
- `deployment` -> the set of projected target keys
- `execution.target` -> `execution.default-target`

When older fields are omitted, runtimes may continue to infer:

- `task = "launch"`
- `environment = "default"`
- `default-target = "local"` if `local` is declared, otherwise the first declared target

New manifests should define `execution.targets` explicitly.
