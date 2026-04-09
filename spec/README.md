# Capability Specification

This directory contains the Apollo capability standard.

## Files

- [`SCHEMA.md`](SCHEMA.md) — human-readable schema, semantics, and conventions
- [`capability.schema.json`](capability.schema.json) — machine-readable JSON Schema for validating parsed manifests

## Why both?

Keeping both is useful:

- `SCHEMA.md` is easier for humans to read, review, and discuss
- `capability.schema.json` is the standard machine-readable format for validation and tooling

The JSON Schema validates the current manifest structure. The Markdown spec documents semantics and conventions that are awkward or impossible to express purely in JSON Schema.

## Current status

The current schema version is `"0.1.0"`, which intentionally signals that the standard is still pre-1.0 and may evolve.

Capability metadata is declared under `tool.capability`, with capability entries namespaced as `tool.capability.<org-name>.<capability-key>`.
