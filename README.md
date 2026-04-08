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
2. Add a `pixi.toml` with the desired `[tasks]` and `[dependencies]`.
3. Document any required inputs or environment variables in a comment at the top of the file.
