#!/usr/bin/env python3
"""Fail-closed repository layout validator for the repo-birth baseline."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PATHS = [
    "README.md",
    "PROJECT_CONTEXT.md",
    "CHANGELOG.md",
    ".gitignore",
    "pyproject.toml",
    "LICENSE_PENDING.md",
    ".bootstrap/bootstrap_manifest.yaml",
    ".bootstrap/template_provenance.yaml",
    "governance/constitution",
    "governance/control_plane",
    "governance/workflows/governed_specs",
    "governance/workflows/validation_reports",
    "governance/reviews",
    "memory/evolution/decisions",
    "memory/evolution/executions",
    "memory/evolution/quarantine",
    "memory/indexes/decision_index.yaml",
    "planning/seeds",
    "planning/prompts",
    "planning/implementation_prompts",
    "docs/architecture/snapshots",
    "docs/contracts",
    "schemas",
    "src",
    "tools/validate_memory.py",
    "tools/check_memory_integrity.py",
    "tools/validate_execution_records.py",
    "tools/check_working_tree_artifact_admission.py",
    "tests/contract",
    "tests/unit",
    ".githooks/pre-commit",
    ".githooks/post-commit",
]

FORBIDDEN_PATHS = [
    "runtime",
    "automation",
    "orchestration",
    "queue",
    "dashboard",
    "bridges",
]


def main() -> int:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    forbidden = [path for path in FORBIDDEN_PATHS if (ROOT / path).exists()]

    if missing or forbidden:
        if missing:
            print("missing required paths:", file=sys.stderr)
            for path in missing:
                print(f"  - {path}", file=sys.stderr)
        if forbidden:
            print("forbidden baseline paths present:", file=sys.stderr)
            for path in forbidden:
                print(f"  - {path}", file=sys.stderr)
        return 1

    print("repository layout validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
