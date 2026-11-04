#!/usr/bin/env python3
"""Fail when a capability lock or manifest is below a known security floor.

The floors are the first releases that no longer trust the intermediate CA keys
compromised in the October 2026 eMudhra incident
(https://emudhra.we-have-a-problem.com/). Raise a floor when a new incident
makes a newer release the minimum safe one, and lower none of them without a
documented reason. Re-lock a capability that fails with
``pixi update --manifest-path capabilities/<name>/pixi.toml <package>``.
"""

from __future__ import annotations

import argparse
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
    # conda-forge's win-64 git repackages Git for Windows, fixed in
    # v2.56.0.windows.3, but no conda-forge build of a fixed release exists
    # yet. Add a floor here once one does.
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

# Pixi 0.82.1 is the first release whose embedded root store and verifier
# reject the compromised keys; see spec/SCHEMA.md.
PIXI_FLOOR = "0.82.1"

LOCK_PACKAGE_RE = re.compile(r"^\s*-\s+(conda|pypi):\s+(\S+)\s*$", re.MULTILINE)
CONDA_SUFFIXES = (".conda", ".tar.bz2")
SDIST_SUFFIXES = (".tar.gz", ".zip")
LOWER_BOUND_RE = re.compile(r">=\s*([0-9][0-9A-Za-z.]*)")
PRERELEASE_RE = re.compile(r"[.\-_]?(a|b|c|rc|alpha|beta|pre|preview|dev)\d*", re.I)


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


def parse_package_url(kind: str, url: str) -> tuple[str, str] | None:
    """Return (name, version) from a lock entry URL, or None if it has none."""
    if kind == "pypi" and not url.startswith(("https://", "http://")):
        return None  # git+, path and editable sources carry no version.
    filename = url.rstrip("/").rsplit("/", 1)[-1]

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


def lock_packages(lock_text: str) -> tuple[set[tuple[str, str]], list[str]]:
    """Return the (name, version) pairs in a lock, plus the URLs of any
    downloadable entries whose name and version could not be read."""
    packages = set()
    unreadable = []
    for kind, url in LOCK_PACKAGE_RE.findall(lock_text):
        parsed = parse_package_url(kind, url)
        if parsed:
            packages.add(parsed)
        elif url.startswith(("https://", "http://")):
            unreadable.append(url)
    return packages, unreadable


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


def lock_violations(lock_text: str) -> list[str]:
    packages, unreadable = lock_packages(lock_text)
    violations = {
        violation
        for name, version in packages
        if (violation := package_violation(name, version))
    }
    # Fail closed: an entry the parser cannot read could be a floor package.
    violations.update(f"cannot read the package version of {url}" for url in unreadable)
    return sorted(violations)


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


def capability_violations(capability_dir: Path) -> list[str]:
    violations = []
    manifest = capability_dir / "pixi.toml"
    lock = capability_dir / "pixi.lock"
    violations.extend(manifest_violations(manifest.read_text(encoding="utf-8")))
    if lock.is_file():
        violations.extend(lock_violations(lock.read_text(encoding="utf-8")))
    else:
        violations.append("pixi.lock is missing")
    return violations


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
        print(f"No capabilities found under {args.capabilities}.")
        return 0

    failed = False
    for capability_dir in capability_dirs:
        violations = capability_violations(capability_dir)
        if violations:
            failed = True
            print(f"{capability_dir.name}: FAILED")
            for violation in violations:
                print(f"  - {violation}")
        else:
            print(f"{capability_dir.name}: OK")

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
