#!/usr/bin/env python3
"""Static Slice 1 contract-stack validator."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REQUIRED = [
    "PROJECT_CONTEXT.md",
    "ORA_SOURCE_CONTEXT_v1.0.0.md",
    "planning/architecture/ORA_v1_ARCHITECTURE_AND_REPO_TREE.md",
    "docs/architecture/ORA_SYSTEM_OVERVIEW.md",
    "docs/architecture/ORA_SUBSYSTEM_BOUNDARIES.md",
    "governance/policies/ORA_CAPABILITY_BOUNDARY.md",
    "governance/policies/ORA_FAIL_CLOSED_POLICY.md",
]


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    if missing:
        for path in missing:
            print(f"missing contract artifact: {path}", file=sys.stderr)
        return 1

    print("ora contract stack validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
