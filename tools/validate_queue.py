#!/usr/bin/env python3
"""Deterministic schema-backed validation for ORA queue artifacts."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.validation.schema_subset import (  # noqa: E402
    ValidationResult,
    build_collection_schema,
    load_json_file,
    load_yaml_subset_file,
    validate_instance,
)


QUEUE_ITEM_SCHEMA_PATH = "schemas/queue/queue_item.schema.json"
PROJECT_QUEUE_PATH = "queue/project_queue.yaml"
BLOCKERS_PATH = "queue/blockers.yaml"
ESCALATIONS_PATH = "queue/escalations.yaml"

BLOCKER_ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["blocker_id", "queue_item_id", "reason", "status"],
    "properties": {
        "blocker_id": {"type": "string"},
        "queue_item_id": {"type": "string"},
        "reason": {"type": "string"},
        "status": {"type": "string"},
    },
}

ESCALATION_ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["escalation_id", "queue_item_id", "reason", "status"],
    "properties": {
        "escalation_id": {"type": "string"},
        "queue_item_id": {"type": "string"},
        "reason": {"type": "string"},
        "status": {"type": "string"},
    },
}


def validate_queue(root: Path = ROOT) -> ValidationResult:
    errors: list[str] = []
    queue_item_schema_path = root / QUEUE_ITEM_SCHEMA_PATH
    project_queue_path = root / PROJECT_QUEUE_PATH
    blockers_path = root / BLOCKERS_PATH
    escalations_path = root / ESCALATIONS_PATH

    for relative_path, path in {
        QUEUE_ITEM_SCHEMA_PATH: queue_item_schema_path,
        PROJECT_QUEUE_PATH: project_queue_path,
        BLOCKERS_PATH: blockers_path,
        ESCALATIONS_PATH: escalations_path,
    }.items():
        if not path.exists():
            errors.append(f"missing file: {relative_path}")
    if errors:
        return ValidationResult(tuple(errors))

    queue_item_schema = load_json_file(queue_item_schema_path)
    project_queue_schema = build_collection_schema("queue_items", queue_item_schema)
    blockers_schema = build_collection_schema("blockers", BLOCKER_ITEM_SCHEMA)
    escalations_schema = build_collection_schema("escalations", ESCALATION_ITEM_SCHEMA)

    for relative_path, path, schema in [
        (PROJECT_QUEUE_PATH, project_queue_path, project_queue_schema),
        (BLOCKERS_PATH, blockers_path, blockers_schema),
        (ESCALATIONS_PATH, escalations_path, escalations_schema),
    ]:
        try:
            document = load_yaml_subset_file(path)
        except ValueError as exc:
            errors.append(f"{relative_path}: {exc}")
            continue
        errors.extend(validate_instance(document, schema, relative_path))

    return ValidationResult(tuple(errors))


def main() -> int:
    result = validate_queue()

    if not result.ok:
        for error in result.errors:
            print(error, file=sys.stderr)
        return 1

    print("queue validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
