#!/usr/bin/env python3
"""Generate the public capability catalog from capability manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tomllib

REGISTRY_NAMESPACE = "openteams_capabilities"


def active_repositories(capabilities_dir: Path) -> list[dict[str, str]]:
    repositories: list[dict[str, str]] = []

    for manifest_path in sorted(capabilities_dir.glob("*/pixi.toml")):
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        repository_name = manifest_path.parent.name
        workspace_name = manifest["workspace"]["name"]
        if workspace_name != repository_name:
            raise ValueError(
                f"{manifest_path}: workspace.name {workspace_name!r} must match "
                f"the published repository name {repository_name!r}"
            )

        definitions = manifest["tool"]["nebi"]["capability"]
        statuses = [
            definition.get("catalog", {}).get("status", "active")
            for organization in definitions.values()
            if isinstance(organization, dict)
            for definition in organization.values()
            if isinstance(definition, dict)
        ]
        if len(set(statuses)) > 1:
            raise ValueError(
                f"{manifest_path}: every definition in one repository must have "
                "the same catalog status"
            )
        if statuses and statuses[0] == "active":
            repositories.append(
                {
                    "namespace": REGISTRY_NAMESPACE,
                    "name": repository_name,
                }
            )

    return repositories


def build_catalog(capabilities_dir: Path) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "repositories": active_repositories(capabilities_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capabilities", type=Path, default=Path("capabilities"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(build_catalog(args.capabilities), indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
