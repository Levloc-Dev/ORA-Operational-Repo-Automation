"""Deterministic governed handoff packet generation for external bridges."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ora.validation.schema_subset import load_yaml_subset_file, validate_instance


ROOT = Path(__file__).resolve().parents[3]
PROJECTS_REGISTRY_PATH = Path("registry/projects.yaml")
REPOS_REGISTRY_PATH = Path("registry/repos.yaml")
PROJECT_QUEUE_PATH = Path("queue/project_queue.yaml")
PACKET_VERSION = "1.0.0"
EXECUTION_MODE = "packet_only"
SUPPORTED_BRIDGE_TYPES = ("CHATGPT", "CLAUDE", "CODEX")
ALLOWED_STATE_READS = [
    str(PROJECTS_REGISTRY_PATH),
    str(REPOS_REGISTRY_PATH),
    str(PROJECT_QUEUE_PATH),
]
VALIDATION_COMMANDS = [
    "python3 tools/validate_profiles.py",
    "python3 tools/validate_registry.py",
    "python3 tools/validate_queue.py",
    "python3 tools/validate_operation_plan.py",
    "python3 tools/validate_handoff_packets.py",
    "python3 validators/validate_ora_contract_stack.py",
    "python3 validators/validate_fail_closed_boundaries.py",
    "pytest -q",
]
PROHIBITED_ACTIONS = [
    "execution",
    "subprocess",
    "github",
    "git_operations",
    "network",
    "repo_writes",
    "queue_updates",
    "prompt_dispatch",
]
REQUESTED_ACTION_BY_BRIDGE = {
    "CHATGPT": "PREPARE_GOVERNED_CHATGPT_HANDOFF",
    "CLAUDE": "PREPARE_GOVERNED_CLAUDE_HANDOFF",
    "CODEX": "PREPARE_GOVERNED_CODEX_HANDOFF",
}

PROJECTS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["projects"],
    "properties": {
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["project_id"],
                "properties": {
                    "project_id": {"type": "string"},
                },
            },
        },
    },
}
REPOS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["repos"],
    "properties": {
        "repos": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "repo_id",
                    "repo_name",
                    "project_profile",
                    "local_path",
                    "github_dev_remote",
                    "github_main_remote",
                    "default_branch",
                    "active_branch",
                    "governance_mode",
                    "validator_set",
                    "sync_mode",
                    "current_queue_item",
                    "last_known_status",
                ],
                "properties": {
                    "repo_id": {"type": "string"},
                    "repo_name": {"type": "string"},
                    "project_profile": {"type": "string"},
                    "local_path": {"type": "string"},
                    "github_dev_remote": {"type": ["string", "null"]},
                    "github_main_remote": {"type": ["string", "null"]},
                    "default_branch": {"type": "string"},
                    "active_branch": {"type": "string"},
                    "governance_mode": {"type": "string"},
                    "validator_set": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "sync_mode": {"type": "string"},
                    "current_queue_item": {"type": ["string", "null"]},
                    "last_known_status": {"type": "string"},
                },
            },
        },
    },
}
QUEUE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["queue_items"],
    "properties": {
        "queue_items": {
            "type": "array",
            "items": {
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
                    "status": {"type": "string"},
                    "current_slice": {"type": "null"},
                    "blocker": {"type": "null"},
                    "escalation_required": {"type": "string", "enum": ["true"]},
                },
            },
        },
    },
}


class HandoffPacketError(ValueError):
    """Raised when governed handoff packet generation cannot proceed safely."""


def build_handoff_packet(
    project_id: str,
    bridge_type: str,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Build a deterministic governed handoff packet for an external bridge."""

    if not project_id:
        raise HandoffPacketError("project_id must be non-empty")

    normalized_bridge_type = bridge_type.upper()
    if normalized_bridge_type not in REQUESTED_ACTION_BY_BRIDGE:
        raise HandoffPacketError(f"unsupported bridge_type '{bridge_type}'")

    projects_document = _load_and_validate_yaml(
        root / PROJECTS_REGISTRY_PATH,
        PROJECTS_SCHEMA,
        str(PROJECTS_REGISTRY_PATH),
    )
    repos_document = _load_and_validate_yaml(
        root / REPOS_REGISTRY_PATH,
        REPOS_SCHEMA,
        str(REPOS_REGISTRY_PATH),
    )
    queue_document = _load_and_validate_yaml(
        root / PROJECT_QUEUE_PATH,
        QUEUE_SCHEMA,
        str(PROJECT_QUEUE_PATH),
    )

    _require_known_project(projects_document["projects"], project_id)
    queue_item = _require_queued_project(queue_document["queue_items"], project_id)
    repo_entry = _require_known_repo(repos_document["repos"], queue_item["repo_id"])
    _validate_joined_state(project_id, queue_item, repo_entry)

    return {
        "packet_version": PACKET_VERSION,
        "bridge_type": normalized_bridge_type,
        "project_id": project_id,
        "repo_id": queue_item["repo_id"],
        "profile_id": queue_item["profile_id"],
        "current_queue_status": queue_item["status"],
        "requested_action": REQUESTED_ACTION_BY_BRIDGE[normalized_bridge_type],
        "authority_boundary": {
            "execution_mode": EXECUTION_MODE,
            "allowed_state_reads": list(ALLOWED_STATE_READS),
            "human_review_required": True,
            "git_operations_allowed": False,
            "network_access_allowed": False,
            "prompt_dispatch_allowed": False,
            "queue_updates_allowed": False,
            "repo_writes_allowed": False,
            "subprocess_allowed": False,
        },
        "validation_commands": list(VALIDATION_COMMANDS),
        "prohibited_actions": list(PROHIBITED_ACTIONS),
        "execution_mode": EXECUTION_MODE,
    }


def render_handoff_packet_json(packet: dict[str, Any]) -> str:
    """Render a canonical, byte-stable JSON packet."""

    return json.dumps(packet, indent=2, sort_keys=True) + "\n"


def _load_and_validate_yaml(
    path: Path,
    schema: dict[str, Any],
    display_path: str,
) -> dict[str, Any]:
    if not path.exists():
        raise HandoffPacketError(f"missing required file: {display_path}")

    try:
        document = load_yaml_subset_file(path)
    except ValueError as exc:
        raise HandoffPacketError(f"{display_path}: {exc}") from exc

    errors = validate_instance(document, schema, display_path)
    if errors:
        raise HandoffPacketError("; ".join(sorted(errors)))

    return document


def _require_known_project(projects: list[dict[str, Any]], project_id: str) -> None:
    if any(entry["project_id"] == project_id for entry in projects):
        return
    raise HandoffPacketError(f"unknown project_id '{project_id}'")


def _require_queued_project(
    queue_items: list[dict[str, Any]],
    project_id: str,
) -> dict[str, Any]:
    for queue_item in queue_items:
        if queue_item["project_id"] == project_id:
            return queue_item
    raise HandoffPacketError(f"project_id '{project_id}' is not present in queue/project_queue.yaml")


def _require_known_repo(
    repos: list[dict[str, Any]],
    repo_id: str,
) -> dict[str, Any]:
    for repo_entry in repos:
        if repo_entry["repo_id"] == repo_id:
            return repo_entry
    raise HandoffPacketError(f"unknown repo_id '{repo_id}'")


def _validate_joined_state(
    project_id: str,
    queue_item: dict[str, Any],
    repo_entry: dict[str, Any],
) -> None:
    if repo_entry["project_profile"] != queue_item["profile_id"]:
        raise HandoffPacketError(
            f"repo_id '{repo_entry['repo_id']}' profile mismatch for project_id '{project_id}'"
        )

