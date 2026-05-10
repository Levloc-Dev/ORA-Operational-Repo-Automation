"""Deterministic validator plan generation for queued ORA projects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ora.pge.bootstrap_plan import BootstrapPlanError, load_project_profile
from ora.validation.schema_subset import load_yaml_subset_file, validate_instance


ROOT = Path(__file__).resolve().parents[3]
PLAN_VERSION = "1.0.0"
EXECUTION_MODE = "PLAN_ONLY"
PROJECTS_REGISTRY_PATH = Path("registry/projects.yaml")
REPOS_REGISTRY_PATH = Path("registry/repos.yaml")
PROJECT_QUEUE_PATH = Path("queue/project_queue.yaml")
ALLOWED_STATE_READS = (
    "registry/projects.yaml",
    "registry/repos.yaml",
    "queue/project_queue.yaml",
)

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
        }
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
        }
    },
}

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
        "status": {"type": "string"},
        "current_slice": {"type": "null"},
        "blocker": {"type": "null"},
        "escalation_required": {"type": "string", "enum": ["true"]},
    },
}

QUEUE_SCHEMA = {
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

class ValidatorOrchestratorError(ValueError):
    """Raised when validator planning cannot proceed safely."""


def build_validator_plan(project_id: str, *, root: Path = ROOT) -> dict[str, Any]:
    """Build a deterministic validator execution plan without running validators."""

    if not project_id:
        raise ValidatorOrchestratorError("project_id must be non-empty")

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
    repo_entry = _require_repo_entry(repos_document["repos"], queue_item["repo_id"])
    validators, prohibited_actions = _resolve_profile_rules(queue_item["profile_id"])
    _validate_joined_state(queue_item, repo_entry, validators)

    return {
        "plan_version": PLAN_VERSION,
        "project_id": project_id,
        "repo_id": queue_item["repo_id"],
        "repo_path": repo_entry["local_path"],
        "profile_id": queue_item["profile_id"],
        "execution_mode": EXECUTION_MODE,
        "validators": validators,
        "authority_boundary": {
            "execution_mode": EXECUTION_MODE,
            "allowed_state_reads": list(ALLOWED_STATE_READS),
            "validator_execution_allowed": False,
            "git_operations_allowed": False,
            "network_access_allowed": False,
            "queue_updates_allowed": False,
            "repo_writes_allowed": False,
            "subprocess_allowed": False,
        },
        "prohibited_actions": prohibited_actions,
    }


def render_validator_plan_json(plan: dict[str, Any]) -> str:
    """Render a canonical, byte-stable validator plan JSON document."""

    return json.dumps(plan, indent=2, sort_keys=True) + "\n"


def _load_and_validate_yaml(
    path: Path,
    schema: dict[str, Any],
    display_path: str,
) -> dict[str, Any]:
    if not path.exists():
        raise ValidatorOrchestratorError(f"missing required file: {display_path}")

    try:
        document = load_yaml_subset_file(path)
    except ValueError as exc:
        raise ValidatorOrchestratorError(f"{display_path}: {exc}") from exc

    errors = validate_instance(document, schema, display_path)
    if errors:
        raise ValidatorOrchestratorError("; ".join(sorted(errors)))

    return document


def _require_known_project(projects: list[dict[str, Any]], project_id: str) -> None:
    if any(project["project_id"] == project_id for project in projects):
        return
    raise ValidatorOrchestratorError(f"unknown project_id '{project_id}'")


def _require_queued_project(
    queue_items: list[dict[str, Any]],
    project_id: str,
) -> dict[str, Any]:
    for queue_item in queue_items:
        if queue_item["project_id"] == project_id:
            return queue_item
    raise ValidatorOrchestratorError(
        f"project_id '{project_id}' is not present in queue/project_queue.yaml"
    )


def _require_repo_entry(
    repo_entries: list[dict[str, Any]],
    repo_id: str,
) -> dict[str, Any]:
    for repo_entry in repo_entries:
        if repo_entry["repo_id"] == repo_id:
            return repo_entry
    raise ValidatorOrchestratorError(
        f"missing repo registry entry for repo_id '{repo_id}'"
    )


def _resolve_profile_rules(profile_id: str) -> tuple[list[str], list[str]]:
    try:
        profile = load_project_profile(profile_id, root=ROOT)
    except BootstrapPlanError as exc:
        raise ValidatorOrchestratorError(str(exc)) from exc

    return list(profile["required_validators"]), list(profile["prohibited_actions"])


def _validate_joined_state(
    queue_item: dict[str, Any],
    repo_entry: dict[str, Any],
    expected_validators: list[str],
) -> None:
    if repo_entry["project_profile"] != queue_item["profile_id"]:
        raise ValidatorOrchestratorError(
            "queue profile_id does not match registry/repos.yaml project_profile"
        )

    if repo_entry["validator_set"] != expected_validators:
        raise ValidatorOrchestratorError(
            "registry/repos.yaml validator_set does not match deterministic profile validator selection"
        )
