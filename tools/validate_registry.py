#!/usr/bin/env python3
"""Fail-closed static validation for Slice 1 registry stubs."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FILES_AND_MARKERS = {
    "schemas/registry/repo_registry.schema.json": '"repos"',
    "registry/repos.yaml": "repos:",
    "registry/projects.yaml": "projects:",
}


def main() -> int:
    errors: list[str] = []

    for relative_path, marker in FILES_AND_MARKERS.items():
        path = ROOT / relative_path
        if not path.exists():
            errors.append(f"missing file: {relative_path}")
            continue
        if marker not in path.read_text(encoding="utf-8"):
            errors.append(f"{relative_path} missing marker {marker}")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("registry validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
