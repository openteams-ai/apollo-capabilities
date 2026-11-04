#!/usr/bin/env python3
"""Fail when a capability lock or manifest is below a known security floor.

The floors are the first releases that no longer trust the intermediate CA keys
compromised in the October 2026 eMudhra incident
(https://emudhra.we-have-a-problem.com/). Raise a floor when a new incident
makes a newer release the minimum safe one, and lower none of them without a
documented reason. Re-lock a capability that fails with
``pixi update --manifest-path capabilities/<name>/pixi.toml <package>``.

Packages that are affected but have no fixed release a capability can use yet
are reported as warnings instead, so they stay visible without blocking CI.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
import tomllib

# Packages that carry or embed a trust store, with the first fixed release.
PACKAGE_FLOORS: dict[str, str] = {
    # Root bundles: Mozilla's store with "emSign ECC Root CA - G3" removed.
    "ca-certificates": "2026.10.19",
    "certifi": "2026.10.19",
    # pip verifies PyPI with its own vendored certifi.
    "pip": "26.2.2",
    # First releases built with rustls-webpki 0.103.16, which rejects chains
    # containing the compromised keys, cross-signs included.
    "uv": "0.13.5",
    "hf-xet": "1.7.1",
}

# CPython's ssl module denies the compromised keys (gh-160040,
# CVE-2026-115557) from these patch releases on. Older minors never got it:
# 3.10 is end of life, and 3.10.22 and earlier lack the denylist.
PYTHON_FLOORS: dict[tuple[int, int], str] = {
    (3, 11): "3.11.18",
    (3, 12): "3.12.16",
    (3, 13): "3.13.18",
    (3, 14): "3.14.10",
    (3, 15): "3.15.2",
}
PYTHON_PACKAGES = frozenset({"python", "cpython"})

# Affected packages a capability cannot move to a fixed release yet. Each is
# documented as a known issue in the README of the capability that uses it.
# polars below 2.1.0 ships rustls-webpki older than 0.103.16, and no 1.x
# release is fixed (see capabilities/jupyterlab/README.md).
POLARS_FIX = "2.1.0"
POLARS_PACKAGES = frozenset(
    {"polars", "polars-runtime-32", "polars-runtime-64", "polars-runtime-compat"}
)
# conda-forge's win-64 git repackages Git for Windows, which fixed its bundled
# CA file in v2.56.0.windows.3, but no conda-forge build of a fixed release
# exists yet (see capabilities/comfyui/README.md). Once one does, add "git" to
# PACKAGE_FLOORS and drop this warning.
WINDOWS_GIT_SUBDIR = "/win-64/"

# Pixi 0.82.1 is the first release whose embedded root store and verifier
# reject the compromised keys; see spec/SCHEMA.md.
PIXI_FLOOR = "0.82.1"

# Pixi writes one entry per package to the top-level `packages:` list, at
# column 0. PyPI entries also record `name:` and `version:` fields; conda
# entries carry both in their filename only.
ENTRY_RE = re.compile(r"^- (conda|pypi):\s*(.+?)\s*$")
FIELD_RE = re.compile(r"^  (name|version):\s*(.+?)\s*$")
CONDA_SUFFIXES = (".conda", ".tar.bz2")
SDIST_SUFFIXES = (".tar.gz", ".zip")
LOWER_BOUND_RE = re.compile(r">=\s*([0-9][0-9A-Za-z.]*)")
PRERELEASE_RE = re.compile(r"[.\-_]?(a|b|c|rc|alpha|beta|pre|preview|dev)\d*", re.I)


@dataclass
class LockEntry:
    kind: str
    url: str
    name: str | None = None
    version: str | None = None


def release_parts(version: str) -> tuple[int, ...]:
    """Return the leading numeric release components of a version string."""
    match = re.match(r"\d+(?:\.\d+)*", version)
    if not match:
        raise ValueError(f"unparseable version {version!r}")
    return tuple(int(part) for part in match.group(0).split("."))


def version_key(version: str) -> tuple[tuple[int, ...], int]:
    """Return a sort key that ignores trailing zeros and ranks pre-releases
    (``1.7.1rc0``, ``1.7.1.dev2``) below the final release they lead up to."""
    release = list(release_parts(version))
    while len(release) > 1 and release[-1] == 0:
        release.pop()
    suffix = re.sub(r"^\d+(?:\.\d+)*", "", version)
    return tuple(release), 0 if PRERELEASE_RE.match(suffix) else 1


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def parse_package_url(kind: str, url: str) -> tuple[str, str] | None:
    """Return (name, version) from a lock entry's filename, or None."""
    filename = url.split("#", 1)[0].split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]

    if kind == "conda":
        for suffix in CONDA_SUFFIXES:
            if filename.endswith(suffix):
                parts = filename[: -len(suffix)].rsplit("-", 2)
                if len(parts) == 3:
                    return normalize_name(parts[0]), parts[1]
        return None

    if filename.endswith(".whl"):
        parts = filename.split("-")
        if len(parts) >= 5:
            return normalize_name(parts[0]), parts[1]
        return None
    for suffix in SDIST_SUFFIXES:
        if filename.endswith(suffix):
            parts = filename[: -len(suffix)].rsplit("-", 1)
            if len(parts) == 2:
                return normalize_name(parts[0]), parts[1]
    return None


def lock_entries(lock_text: str) -> list[LockEntry]:
    """Return the entries of a lock's top-level `packages:` list."""
    entries: list[LockEntry] = []
    current: LockEntry | None = None
    for line in lock_text.splitlines():
        if match := ENTRY_RE.match(line):
            current = LockEntry(match.group(1), unquote(match.group(2)))
            entries.append(current)
        elif current is not None and line.startswith("  "):
            if field := FIELD_RE.match(line):
                setattr(current, field.group(1), unquote(field.group(2)))
        else:
            current = None
    return entries


def entry_name_version(entry: LockEntry) -> tuple[str, str] | None:
    if entry.name and entry.version:
        return normalize_name(entry.name), entry.version
    return parse_package_url(entry.kind, entry.url)


def package_violation(name: str, version: str) -> str | None:
    if name in PYTHON_PACKAGES:
        minor = release_parts(version)[:2]
        floor = PYTHON_FLOORS.get(minor)
        if floor is None:
            if minor < min(PYTHON_FLOORS):
                oldest = PYTHON_FLOORS[min(PYTHON_FLOORS)]
                return (
                    f"{name} {version}: no release of this minor version has "
                    f"the fix; use {oldest} or later"
                )
            return None  # Newer than every listed minor, so it has the fix.
    else:
        floor = PACKAGE_FLOORS.get(name)
        if floor is None:
            return None
    if version_key(version) < version_key(floor):
        return f"{name} {version} < {floor}"
    return None


def package_warning(name: str, version: str, url: str) -> str | None:
    if name in POLARS_PACKAGES and version_key(version) < version_key(POLARS_FIX):
        return (
            f"{name} {version} < {POLARS_FIX}: known issue, no fixed release "
            "this capability can use yet"
        )
    if name == "git" and WINDOWS_GIT_SUBDIR in url:
        return (
            f"git {version} (win-64): known issue, no conda-forge build of a "
            "fixed Git for Windows yet"
        )
    return None


def lock_findings(lock_text: str) -> tuple[list[str], list[str]]:
    """Return the (violations, warnings) for one lock."""
    entries = lock_entries(lock_text)
    if not entries:
        return ["no packages found in pixi.lock"], []
    violations: set[str] = set()
    warnings: set[str] = set()
    for entry in entries:
        parsed = entry_name_version(entry)
        if parsed is None:
            # Fail closed: an entry that cannot be read could be a floor package.
            violations.add(f"cannot read the package name and version of {entry.url}")
            continue
        name, version = parsed
        try:
            if violation := package_violation(name, version):
                violations.add(violation)
            if warning := package_warning(name, version, entry.url):
                warnings.add(warning)
        except ValueError:
            violations.add(f"cannot parse the version {version!r} of {name}")
    return sorted(violations), sorted(warnings)


def lock_violations(lock_text: str) -> list[str]:
    return lock_findings(lock_text)[0]


def lock_warnings(lock_text: str) -> list[str]:
    return lock_findings(lock_text)[1]


def manifest_violations(manifest_text: str) -> list[str]:
    manifest = tomllib.loads(manifest_text)
    spec = manifest.get("workspace", {}).get("requires-pixi")
    if not isinstance(spec, str) or not spec.strip():
        return [f'[workspace].requires-pixi is missing; set it to ">={PIXI_FLOOR}"']
    # Clauses joined by "," must all hold, so the highest >= bound applies;
    # alternatives joined by "|" are each enough, so the lowest one applies.
    lowest = None
    for alternative in spec.split("|"):
        bounds = LOWER_BOUND_RE.findall(alternative)
        if not bounds:
            return [f"requires-pixi {spec!r} has no >= lower bound"]
        bound = max(version_key(bound) for bound in bounds)
        lowest = bound if lowest is None else min(lowest, bound)
    if lowest < version_key(PIXI_FLOOR):
        return [f"requires-pixi {spec!r} allows Pixi older than {PIXI_FLOOR}"]
    return []


def capability_findings(capability_dir: Path) -> tuple[list[str], list[str]]:
    """Return the (violations, warnings) for one capability directory."""
    manifest = capability_dir / "pixi.toml"
    lock = capability_dir / "pixi.lock"
    violations = manifest_violations(manifest.read_text(encoding="utf-8"))
    if not lock.is_file():
        return [*violations, "pixi.lock is missing"], []
    lock_violations_, warnings = lock_findings(lock.read_text(encoding="utf-8"))
    return [*violations, *lock_violations_], warnings


def capability_violations(capability_dir: Path) -> list[str]:
    return capability_findings(capability_dir)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "capabilities", nargs="?", type=Path, default=Path("capabilities")
    )
    args = parser.parse_args()

    capability_dirs = sorted(
        path.parent for path in args.capabilities.glob("*/pixi.toml")
    )
    if not capability_dirs:
        # Fail closed: a moved or mistyped directory must not pass unchecked.
        print(f"No capabilities found under {args.capabilities}; nothing checked.")
        return 1

    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    failed = False
    for capability_dir in capability_dirs:
        violations, warnings = capability_findings(capability_dir)
        status = "FAILED" if violations else "OK"
        if warnings:
            status += f" ({len(warnings)} known-issue warning(s))"
        print(f"{capability_dir.name}: {status}")
        for violation in violations:
            print(f"  - {violation}")
        for warning in warnings:
            print(f"  ! {warning}")
            if in_actions:
                print(
                    f"::warning title=Security floor ({capability_dir.name})::{warning}"
                )
        failed = failed or bool(violations)

    if failed:
        print(
            "\nRe-lock each failing capability with Pixi "
            f">={PIXI_FLOOR}, e.g. `pixi update --manifest-path "
            "capabilities/<name>/pixi.toml <package>`."
        )
        return 1
    print(f"\nAll {len(capability_dirs)} capabilities meet the security floors.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
