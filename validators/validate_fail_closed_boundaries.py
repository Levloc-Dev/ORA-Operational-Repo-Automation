#!/usr/bin/env python3
"""Static Slice 1 fail-closed boundary validator."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_TEXT = {
    "README.md": "Excluded from repo birth:",
    "governance/policies/ORA_CAPABILITY_BOUNDARY.md": "Not allowed in Slice 1:",
    "governance/policies/ORA_FAIL_CLOSED_POLICY.md": "must stop without continuation",
    "src/ora/operations/runner.py": "not implemented in Slice 1",
}
FORBIDDEN_PATHS = [
    "runtime",
]


def main() -> int:
    errors: list[str] = []

    for relative_path, marker in REQUIRED_TEXT.items():
        path = ROOT / relative_path
        if not path.exists():
            errors.append(f"missing file: {relative_path}")
            continue
        if marker not in path.read_text(encoding="utf-8"):
            errors.append(f"{relative_path} missing marker {marker}")

    for relative_path in FORBIDDEN_PATHS:
        if (ROOT / relative_path).exists():
            errors.append(f"forbidden path present: {relative_path}")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("fail-closed boundary validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
