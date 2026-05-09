"""Deterministic queue registration and closed-set state updates for ORA."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ora.validation.schema_subset import load_json_file, load_yaml_subset_file, validate_instance


ROOT = Path(__file__).resolve().parents[3]
QUEUE_ITEM_SCHEMA_PATH = Path("schemas/queue/queue_item.schema.json")
REPO_REGISTRY_SCHEMA_PATH = Path("schemas/registry/repo_registry.schema.json")
PROJECT_QUEUE_PATH = Path("queue/project_queue.yaml")
BLOCKERS_PATH = Path("queue/blockers.yaml")
ESCALATIONS_PATH = Path("queue/escalations.yaml")
REPOS_REGISTRY_PATH = Path("registry/repos.yaml")

QUEUE_STATES = (
    "PROPOSED",
    "READY_FOR_BOOTSTRAP",
    "BOOTSTRAPPING",
    "READY_FOR_SLICE",
    "IN_SLICE",
    "VALIDATING",
    "BLOCKED",
    "ESCALATION_REQUIRED",
    "READY_FOR_COMMIT",
    "READY_FOR_SYNC",
    "COMPLETE",
    "ARCHIVED",
)
BLOCKED_STATE = "BLOCKED"
ESCALATION_REQUIRED_STATE = "ESCALATION_REQUIRED"
TERMINAL_STATES = frozenset({"COMPLETE", "ARCHIVED"})
ACTIVE_STATES = frozenset(
    state for state in QUEUE_STATES if state not in TERMINAL_STATES
)

QUEUE_ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["queue_item_id", "repo_id", "state", "next_action"],
    "properties": {
        "queue_item_id": {"type": "string"},
        "repo_id": {"type": "string"},
        "state": {"type": "string", "enum": list(QUEUE_STATES)},
        "next_action": {"type": "string"},
    },
}

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

BLOCKERS_DOCUMENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["blockers"],
    "properties": {
        "blockers": {
            "type": "array",
            "items": BLOCKER_ITEM_SCHEMA,
        }
    },
}

ESCALATIONS_DOCUMENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["escalations"],
    "properties": {
        "escalations": {
            "type": "array",
            "items": ESCALATION_ITEM_SCHEMA,
        }
    },
}


class QueueManagerError(ValueError):
    """Raised when queue state cannot be updated safely."""


def register_queue_item(
    repo_id: str,
    queue_item_id: str,
    state: str,
    next_action: str,
    *,
    root: Path = ROOT,
    reason: str | None = None,
) -> dict[str, Any]:
    """Register a new queue item and synchronize queue metadata."""

    if not queue_item_id:
        raise QueueManagerError("queue_item_id must be non-empty")

    if not repo_id:
        raise QueueManagerError("repo_id must be non-empty")

    if not next_action:
        raise QueueManagerError("next_action must be non-empty")

    _require_known_state(state)
    if state in TERMINAL_STATES:
        raise QueueManagerError("cannot register queue item directly into a terminal state")
    if state in {BLOCKED_STATE, ESCALATION_REQUIRED_STATE} and not reason:
        raise QueueManagerError(f"reason is required when registering state {state}")

    documents = _load_documents(root)
    repos = documents["repos"]["repos"]
    queue_items = documents["queue"]["queue_items"]

    repo_entry = _find_repo(repos, repo_id)
    _ensure_unique_queue_item(queue_items, queue_item_id)
    _ensure_repo_is_available(repo_entry)

    queue_item = {
        "queue_item_id": queue_item_id,
        "repo_id": repo_id,
        "state": state,
        "next_action": next_action,
    }
    queue_items.append(queue_item)
    documents["queue"]["queue_items"] = _sorted_entries(queue_items, "queue_item_id")

    repo_entry["current_queue_item"] = queue_item_id
    repo_entry["last_known_status"] = state

    if state == BLOCKED_STATE:
        _upsert_reason_record(
            documents["blockers"]["blockers"],
            id_key="blocker_id",
            item_id_prefix="blk",
            queue_item_id=queue_item_id,
            reason=reason,
        )
    elif state == ESCALATION_REQUIRED_STATE:
        _upsert_reason_record(
            documents["escalations"]["escalations"],
            id_key="escalation_id",
            item_id_prefix="esc",
            queue_item_id=queue_item_id,
            reason=reason,
        )

    _persist_documents(root, documents)
    return _build_result(
        action="REGISTERED",
        queue_item=queue_item,
        repo_id=repo_id,
        updated_files=_updated_files(),
    )


def update_queue_item_state(
    queue_item_id: str,
    state: str,
    next_action: str,
    *,
    root: Path = ROOT,
    reason: str | None = None,
) -> dict[str, Any]:
    """Update a queue item to a new closed-set state."""

    if not queue_item_id:
        raise QueueManagerError("queue_item_id must be non-empty")

    if not next_action:
        raise QueueManagerError("next_action must be non-empty")

    _require_known_state(state)
    if state in {BLOCKED_STATE, ESCALATION_REQUIRED_STATE} and not reason:
        raise QueueManagerError(f"reason is required when updating state to {state}")

    documents = _load_documents(root)
    queue_item = _find_queue_item(documents["queue"]["queue_items"], queue_item_id)
    previous_state = queue_item["state"]
    repo_entry = _find_repo(documents["repos"]["repos"], queue_item["repo_id"])

    queue_item["state"] = state
    queue_item["next_action"] = next_action
    repo_entry["last_known_status"] = state

    if state in ACTIVE_STATES:
        _ensure_current_queue_item_matches(repo_entry, queue_item_id)
        repo_entry["current_queue_item"] = queue_item_id
    else:
        if repo_entry.get("current_queue_item") == queue_item_id:
            repo_entry["current_queue_item"] = None

    _apply_reason_state_updates(
        documents=documents,
        queue_item_id=queue_item_id,
        state=state,
        reason=reason,
    )

    _persist_documents(root, documents)
    return {
        "status": "UPDATED",
        "queue_item_id": queue_item_id,
        "repo_id": queue_item["repo_id"],
        "previous_state": previous_state,
        "state": state,
        "next_action": next_action,
        "updated_files": _updated_files(),
    }


def _load_documents(root: Path) -> dict[str, dict[str, Any]]:
    required_paths = {
        "queue schema": root / QUEUE_ITEM_SCHEMA_PATH,
        "repo registry schema": root / REPO_REGISTRY_SCHEMA_PATH,
        "project queue": root / PROJECT_QUEUE_PATH,
        "blockers": root / BLOCKERS_PATH,
        "escalations": root / ESCALATIONS_PATH,
        "repo registry": root / REPOS_REGISTRY_PATH,
    }
    missing = [label for label, path in required_paths.items() if not path.exists()]
    if missing:
        raise QueueManagerError(
            "missing required files: " + ", ".join(sorted(missing))
        )

    queue_schema = load_json_file(root / QUEUE_ITEM_SCHEMA_PATH)
    repo_registry_schema = load_json_file(root / REPO_REGISTRY_SCHEMA_PATH)

    documents = {
        "queue": _load_and_validate_yaml(
            root / PROJECT_QUEUE_PATH,
            _build_collection_schema(queue_schema, "queue_items"),
            "queue/project_queue.yaml",
        ),
        "blockers": _load_and_validate_yaml(
            root / BLOCKERS_PATH,
            BLOCKERS_DOCUMENT_SCHEMA,
            "queue/blockers.yaml",
        ),
        "escalations": _load_and_validate_yaml(
            root / ESCALATIONS_PATH,
            ESCALATIONS_DOCUMENT_SCHEMA,
            "queue/escalations.yaml",
        ),
        "repos": _load_and_validate_yaml(
            root / REPOS_REGISTRY_PATH,
            repo_registry_schema,
            "registry/repos.yaml",
        ),
    }
    return documents


def _load_and_validate_yaml(
    path: Path,
    schema: dict[str, Any],
    display_path: str,
) -> dict[str, Any]:
    try:
        document = load_yaml_subset_file(path)
    except ValueError as exc:
        raise QueueManagerError(f"{display_path}: {exc}") from exc

    errors = validate_instance(document, schema, display_path)
    if errors:
        raise QueueManagerError("; ".join(sorted(errors)))

    return document


def _build_collection_schema(
    item_schema: dict[str, Any],
    collection_key: str,
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [collection_key],
        "properties": {
            collection_key: {
                "type": "array",
                "items": item_schema,
            }
        },
    }


def _find_repo(repos: list[dict[str, Any]], repo_id: str) -> dict[str, Any]:
    for entry in repos:
        if entry["repo_id"] == repo_id:
            return entry
    raise QueueManagerError(f"unknown repo_id '{repo_id}'")


def _find_queue_item(
    queue_items: list[dict[str, Any]],
    queue_item_id: str,
) -> dict[str, Any]:
    for entry in queue_items:
        if entry["queue_item_id"] == queue_item_id:
            return entry
    raise QueueManagerError(f"unknown queue_item_id '{queue_item_id}'")


def _ensure_unique_queue_item(
    queue_items: list[dict[str, Any]],
    queue_item_id: str,
) -> None:
    if any(entry["queue_item_id"] == queue_item_id for entry in queue_items):
        raise QueueManagerError(f"duplicate queue_item_id '{queue_item_id}'")


def _ensure_repo_is_available(repo_entry: dict[str, Any]) -> None:
    current_queue_item = repo_entry.get("current_queue_item")
    if current_queue_item is not None:
        raise QueueManagerError(
            f"repo_id '{repo_entry['repo_id']}' already has active queue item "
            f"'{current_queue_item}'"
        )


def _ensure_current_queue_item_matches(
    repo_entry: dict[str, Any],
    queue_item_id: str,
) -> None:
    current_queue_item = repo_entry.get("current_queue_item")
    if current_queue_item not in {None, queue_item_id}:
        raise QueueManagerError(
            f"repo_id '{repo_entry['repo_id']}' is currently assigned to "
            f"'{current_queue_item}', not '{queue_item_id}'"
        )


def _apply_reason_state_updates(
    *,
    documents: dict[str, dict[str, Any]],
    queue_item_id: str,
    state: str,
    reason: str | None,
) -> None:
    blockers = documents["blockers"]["blockers"]
    escalations = documents["escalations"]["escalations"]

    if state == BLOCKED_STATE:
        _upsert_reason_record(
            blockers,
            id_key="blocker_id",
            item_id_prefix="blk",
            queue_item_id=queue_item_id,
            reason=reason,
        )
        _close_reason_records(escalations, queue_item_id)
        return

    if state == ESCALATION_REQUIRED_STATE:
        _upsert_reason_record(
            escalations,
            id_key="escalation_id",
            item_id_prefix="esc",
            queue_item_id=queue_item_id,
            reason=reason,
        )
        _close_reason_records(blockers, queue_item_id)
        return

    _close_reason_records(blockers, queue_item_id)
    _close_reason_records(escalations, queue_item_id)


def _upsert_reason_record(
    records: list[dict[str, Any]],
    *,
    id_key: str,
    item_id_prefix: str,
    queue_item_id: str,
    reason: str | None,
) -> None:
    assert reason is not None

    for record in records:
        if record["queue_item_id"] == queue_item_id:
            record["reason"] = reason
            record["status"] = "OPEN"
            return

    records.append(
        {
            id_key: f"{item_id_prefix}-{queue_item_id}",
            "queue_item_id": queue_item_id,
            "reason": reason,
            "status": "OPEN",
        }
    )
    records.sort(key=lambda record: str(record[id_key]))


def _close_reason_records(
    records: list[dict[str, Any]],
    queue_item_id: str,
) -> None:
    for record in records:
        if record["queue_item_id"] == queue_item_id:
            record["status"] = "CLOSED"


def _persist_documents(root: Path, documents: dict[str, dict[str, Any]]) -> None:
    _write_yaml(root / PROJECT_QUEUE_PATH, documents["queue"])
    _write_yaml(root / BLOCKERS_PATH, documents["blockers"])
    _write_yaml(root / ESCALATIONS_PATH, documents["escalations"])
    _write_yaml(root / REPOS_REGISTRY_PATH, documents["repos"])


def _updated_files() -> list[str]:
    return [
        str(PROJECT_QUEUE_PATH),
        str(BLOCKERS_PATH),
        str(ESCALATIONS_PATH),
        str(REPOS_REGISTRY_PATH),
    ]


def _build_result(
    *,
    action: str,
    queue_item: dict[str, Any],
    repo_id: str,
    updated_files: list[str],
) -> dict[str, Any]:
    return {
        "status": action,
        "queue_item_id": queue_item["queue_item_id"],
        "repo_id": repo_id,
        "state": queue_item["state"],
        "next_action": queue_item["next_action"],
        "updated_files": updated_files,
    }


def _require_known_state(state: str) -> None:
    if state not in QUEUE_STATES:
        allowed_states = ", ".join(QUEUE_STATES)
        raise QueueManagerError(
            f"unknown queue state '{state}'; expected one of {allowed_states}"
        )


def _sorted_entries(
    entries: list[dict[str, Any]],
    id_key: str,
) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda entry: str(entry[id_key]))


def _write_yaml(path: Path, document: dict[str, Any]) -> None:
    path.write_text(_dump_yaml(document), encoding="utf-8")


def _dump_yaml(value: Any, *, indent: int = 0) -> str:
    if not isinstance(value, dict):
        raise QueueManagerError("queue document root must be an object")

    lines = _dump_mapping(value, indent)
    return "\n".join(lines) + "\n"


def _dump_mapping(mapping: dict[str, Any], indent: int) -> list[str]:
    lines: list[str] = []
    for key, value in mapping.items():
        prefix = " " * indent
        if isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
                continue
            lines.append(f"{prefix}{key}:")
            lines.extend(_dump_sequence(value, indent + 2))
            continue

        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.extend(_dump_mapping(value, indent + 2))
            continue

        lines.append(f"{prefix}{key}: {_dump_scalar(value)}")
    return lines


def _dump_sequence(values: list[Any], indent: int) -> list[str]:
    lines: list[str] = []
    prefix = " " * indent
    for value in values:
        if isinstance(value, dict):
            first = True
            for key, nested_value in value.items():
                entry_prefix = f"{prefix}- " if first else f"{prefix}  "
                if isinstance(nested_value, list):
                    if not nested_value:
                        lines.append(f"{entry_prefix}{key}: []")
                    else:
                        lines.append(f"{entry_prefix}{key}:")
                        lines.extend(_dump_sequence(nested_value, indent + 4))
                elif isinstance(nested_value, dict):
                    lines.append(f"{entry_prefix}{key}:")
                    lines.extend(_dump_mapping(nested_value, indent + 4))
                else:
                    lines.append(f"{entry_prefix}{key}: {_dump_scalar(nested_value)}")
                first = False
            if first:
                lines.append(f"{prefix}- {{}}")
            continue

        if isinstance(value, list):
            if value:
                raise QueueManagerError("nested sequences are unsupported")
            lines.append(f"{prefix}- []")
            continue

        lines.append(f"{prefix}- {_dump_scalar(value)}")
    return lines


def _dump_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return _dump_string(value)
    raise QueueManagerError(
        f"unsupported queue scalar type: {type(value).__name__}"
    )


def _dump_string(value: str) -> str:
    if value == "":
        return '""'

    safe_characters = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_/.:"
    )
    if set(value) <= safe_characters and not value.startswith(("-", "?", ":", "{", "[")):
        return value

    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    raise QueueManagerError(
        "unsupported string value for deterministic YAML emission"
    )
