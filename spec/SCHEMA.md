# Program Schema (spec-version = "0.1.0")

This document is the human-readable specification for Collab program metadata. A machine-readable companion schema lives at [`program.schema.json`](program.schema.json).

Collab programs are Pixi manifests (`pixi.toml`) with program metadata under:

- `[tool.nebi.program]`
- `[tool.nebi.program.<org-name>.<program-key>]`
- `[tool.nebi.program.<org-name>.<program-key>.targets.<target>]`

> Note: This repo is still unreleased, so the schema uses `spec-version = "0.1.0"` to make its pre-1.0 status explicit.
>
> programs are launched via Pixi tasks; task execution is implicit in the schema.

## Why `spec-version` lives at `tool.nebi.program`

`spec-version` describes the shape of the program metadata block itself, not one individual program definition. Keeping it at `[tool.nebi.program]` avoids duplication and still leaves room for multiple program definitions in a single manifest file.

## Full shape

```toml
[workspace]
name = "<program-name>"
version = "0.1.0"
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64", "osx-64", "win-64"]

[tool.nebi.program]
spec-version = "0.1.0"

[tool.nebi.program.<org-name>.<program-key>]
name = "<Human Readable Name>"
description = "<Short description>"
icon = "<URL>" # optional
author = { name = "<Name>", email = "<email>" } # optional
tags = ["tag1", "tag2"] # optional
default-target = "local"

[tool.nebi.program.<org-name>.<program-key>.targets.local]
task = "launch"
environment = "default" # optional, defaults to default
runs-in = "browser" # optional: "app" | "browser" | "background"

[tool.nebi.program.<org-name>.<program-key>.targets.hub]
task = "launch-hub"
environment = "default" # optional, defaults to default
runs-in = "browser" # optional: "app" | "browser" | "background"

[tasks]
launch = { cmd = "<command>" }
launch-hub = { cmd = "<command>" } # optional, only if hub differs
```

## Field reference

## `[tool.nebi.program]`

| Field | Required | Description |
|---|---|---|
| `spec-version` | Yes | Schema version as a semver-style string (currently `"0.1.0"`). A pre-1.0 value signals the schema is still evolving. |

## `[tool.nebi.program.<org-name>.<program-key>]`

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Human-readable display name. |
| `description` | Yes | Short program description. |
| `icon` | No | Icon URL. |
| `author` | No | Author metadata (`name`, `email`). |
| `tags` | No | Discovery/marketplace tags. |
| `default-target` | Yes | Default execution target. Must match a key under `targets`. Valid target values are currently `local` and `hub`. |

## `[tool.nebi.program.<org-name>.<program-key>.targets.<target>]`

| Field | Required | Description |
|---|---|---|
| `task` | Yes | Pixi task name used to launch the program on this target. |
| `environment` | No | Pixi environment name. Defaults to `default`. |
| `runs-in` | No | How the program surfaces to the user. One of `"app"` (native window), `"browser"` (opens a web URL), or `"background"` (no UI). |

## Namespace keys

- `<org-name>` is the publisher namespace for the program, e.g. `openteams`.
- `<program-key>` is the program identifier within that namespace and should typically match `workspace.name`.
- The fully qualified program identifier is `<org-name>.<program-key>`.

## Supported target keys

`<target>` is currently one of:

- `local`
- `hub`

A program supports exactly the targets it defines under `targets`.

## Validation

The JSON Schema in [`program.schema.json`](program.schema.json) validates the current manifest shape after TOML has been parsed into a generic data structure.

Some conventions are still documented here rather than enforced in JSON Schema, including:

- `<program-key>` should typically match `workspace.name`
- `<org-name>` should be the stable publisher namespace used by the program author

New manifests should follow the shape described in this document.
