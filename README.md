# Apollo Capabilities

A collection of reusable [pixi](https://pixi.sh) capabilities — self-contained `pixi.toml` files that define tasks and dependencies for common workflows.

## Structure

```
capabilities/
  <capability-name>/
    pixi.toml
```

Each capability lives in its own directory and is a standalone pixi project.

## Usage

Navigate into any capability directory and run its tasks with pixi:

```sh
cd capabilities/hello-world
pixi run hello
```

## Adding a Capability

1. Create a new directory under `capabilities/`.
2. Add a `pixi.toml` following the schema below.
3. Optionally add a `README.md` documenting tasks and any environment variables.

## `pixi.toml` Capability Schema

Every capability is a standard pixi workspace with an additional `[tool.capability]` section.

```toml
[workspace]
name = "<capability-name>"
version = "0.1.0"
channels = ["conda-forge"]
platforms = ["linux-64", "osx-arm64", "osx-64", "win-64"]

[dependencies]
# conda-forge packages required by this capability

[tool.capability]
spec-version = 1

[tool.capability.<capability-name>]
name = "<Human Readable Name>"
description = "<Short description of what this capability does>"
icon = "<URL to an icon image>"  # optional
author = { name = "<Author>", email = "<email>" }

[tasks]
launch = { cmd = "<command to run>" }
```

### `[tool.capability]` Fields

| Field | Required | Description |
|---|---|---|
| `spec-version` | Yes | Schema version. Currently `1`. |

### `[tool.capability.<name>]` Fields

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Human-readable display name. |
| `description` | Yes | Short description of the capability. |
| `icon` | No | URL to an icon image. |
| `author` | No | Author name and email. |
