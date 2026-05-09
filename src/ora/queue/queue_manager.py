"""Deterministic queue admission gate for ORA."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ora.validation.schema_subset import load_yaml_subset_file, validate_instance


ROOT = Path(__file__).resolve().parents[3]
PROJECT_QUEUE_PATH = Path("queue/project_queue.yaml")
PROJECTS_REGISTRY_PATH = Path("registry/projects.yaml")
REPOS_REGISTRY_PATH = Path("registry/repos.yaml")
READY_STATUS = "READY_FOR_FIRST_GOVERNED_SLICE"

QUEUE_ITEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "project_id",
        "repo_id",
        "profile_id",
        "status",
        "current_slice",
        "blocker",
        "escalation_required",
    ],
    "properties": {
        "project_id": {"type": "string"},
        "repo_id": {"type": "string"},
        "profile_id": {"type": "string"},
        "status": {"type": "string", "enum": [READY_STATUS]},
        "current_slice": {"type": "null"},
        "blocker": {"type": "null"},
        "escalation_required": {"type": "string", "enum": ["true"]},
    },
}

QUEUE_DOCUMENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["queue_items"],
    "properties": {
        "queue_items": {
            "type": "array",
            "items": QUEUE_ITEM_SCHEMA,
        }
    },
}

PROJECTS_REGISTRY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["projects"],
    "properties": {
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["project_id"],
                "properties": {"project_id": {"type": "string"}},
            },
        }
    },
}

REPOS_REGISTRY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["repos"],
    "properties": {
        "repos": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["repo_id"],
                "properties": {"repo_id": {"type": "string"}},
            },
        }
    },
}


class QueueManagerError(ValueError):
    """Raised when queue admission cannot proceed safely."""


def register_queue_item(
    project_id: str,
    profile_id: str,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Admit a project to the governed queue if it passes verification."""

    if not project_id:
        raise QueueManagerError("project_id must be non-empty")
    if not profile_id:
        raise QueueManagerError("profile_id must be non-empty")

    repo_id = _derive_repo_id(project_id)
    queue_document = _load_and_validate_yaml(
        root / PROJECT_QUEUE_PATH,
        QUEUE_DOCUMENT_SCHEMA,
        str(PROJECT_QUEUE_PATH),
    )
    projects_document = _load_and_validate_yaml(
        root / PROJECTS_REGISTRY_PATH,
        PROJECTS_REGISTRY_SCHEMA,
        str(PROJECTS_REGISTRY_PATH),
    )
    repos_document = _load_and_validate_yaml(
        root / REPOS_REGISTRY_PATH,
        REPOS_REGISTRY_SCHEMA,
        str(REPOS_REGISTRY_PATH),
    )

    _require_known_project(projects_document["projects"], project_id)
    _require_known_repo(repos_document["repos"], repo_id)
    _reject_duplicate_project(queue_document["queue_items"], project_id)

    queue_item = _build_queue_item(
        project_id=project_id,
        repo_id=repo_id,
        profile_id=profile_id,
    )
    queue_document["queue_items"] = sorted(
        [*queue_document["queue_items"], queue_item],
        key=_queue_item_sort_key,
    )
    _write_yaml(root / PROJECT_QUEUE_PATH, queue_document)

    return {
        "admitted": True,
        "profile_id": profile_id,
        "project_id": project_id,
        "queue_item": queue_item,
        "repo_id": repo_id,
        "updated_files": [str(PROJECT_QUEUE_PATH)],
    }


def _derive_repo_id(project_id: str) -> str:
    return project_id


def _load_and_validate_yaml(
    path: Path,
    schema: dict[str, Any],
    display_path: str,
) -> dict[str, Any]:
    if not path.exists():
        raise QueueManagerError(f"missing required file: {display_path}")

    try:
        document = load_yaml_subset_file(path)
    except ValueError as exc:
        raise QueueManagerError(f"{display_path}: {exc}") from exc

    errors = validate_instance(document, schema, display_path)
    if errors:
        raise QueueManagerError("; ".join(sorted(errors)))

    if display_path == str(PROJECT_QUEUE_PATH):
        for index, queue_item in enumerate(document["queue_items"]):
            if queue_item["escalation_required"] != "true":
                raise QueueManagerError(
                    f"{display_path}.queue_items[{index}].escalation_required must be true"
                )

    return document


def _require_known_project(projects: list[dict[str, Any]], project_id: str) -> None:
    if any(entry.get("project_id") == project_id for entry in projects):
        return
    raise QueueManagerError(f"unknown project_id '{project_id}'")


def _require_known_repo(repos: list[dict[str, Any]], repo_id: str) -> None:
    if any(entry.get("repo_id") == repo_id for entry in repos):
        return
    raise QueueManagerError(f"unknown repo_id '{repo_id}'")


def _reject_duplicate_project(
    queue_items: list[dict[str, Any]],
    project_id: str,
) -> None:
    if any(entry.get("project_id") == project_id for entry in queue_items):
        raise QueueManagerError(f"duplicate project_id '{project_id}'")


def _build_queue_item(
    *,
    project_id: str,
    repo_id: str,
    profile_id: str,
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "repo_id": repo_id,
        "profile_id": profile_id,
        "status": READY_STATUS,
        "current_slice": None,
        "blocker": None,
        "escalation_required": True,
    }


def _queue_item_sort_key(queue_item: dict[str, Any]) -> str:
    return str(queue_item["project_id"])


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
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
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
