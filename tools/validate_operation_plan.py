#!/usr/bin/env python3
"""Fail-closed static validation for Slice 1 operation-plan schema stubs."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas/operation/operation_plan.schema.json"
ALLOWED_MARKERS = [
    '"WRITE_FILE"',
    '"CREATE_DIRECTORY"',
    '"APPLY_TEMPLATE"',
    '"RUN_VALIDATOR"',
    '"PREPARE_COMMIT"',
    '"GENERATE_HANDOFF_PACKET"',
    '"REGISTER_QUEUE_ITEM"',
    '"UPDATE_QUEUE_ITEM"',
]
PROHIBITED_MARKERS = [
    '"ARBITRARY_SHELL"',
    '"DEPLOY"',
    '"MERGE"',
    '"DELETE_REMOTE"',
    '"MODIFY_GOVERNANCE_AUTHORITY"',
]


def main() -> int:
    if not SCHEMA_PATH.exists():
        print("missing file: schemas/operation/operation_plan.schema.json", file=sys.stderr)
        return 1

    text = SCHEMA_PATH.read_text(encoding="utf-8")
    errors = [
        f"operation schema missing marker {marker}"
        for marker in ALLOWED_MARKERS + PROHIBITED_MARKERS
        if marker not in text
    ]

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("operation plan validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
