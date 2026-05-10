from __future__ import annotations

import json
import sys
from textwrap import dedent
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.validation.schema_subset import parse_yaml_subset
from tools.validate_handoff_packets import validate_handoff_packets
from tools.validate_operation_plan import validate_operation_plan_schema
from tools.validate_profiles import validate_profiles
from tools.validate_queue import validate_queue
from tools.validate_registry import validate_registry


def test_yaml_subset_parser_supports_scalars_and_sequence_mappings() -> None:
    document = parse_yaml_subset(
        dedent(
            """
            blockers:
              - blocker_id: blk-1
                queue_item_id: q-1
                reason: missing schema
                status: open
            """
        ).strip(),
        source_name="inline.yaml",
    )

    assert document == {
        "blockers": [
            {
                "blocker_id": "blk-1",
                "queue_item_id": "q-1",
                "reason": "missing schema",
                "status": "open",
            }
        ]
    }


def test_validate_profiles_accepts_existing_profile_shape(tmp_path: Path) -> None:
    root = tmp_path
    _write_json(
        root / "schemas/profile/project_profile.schema.json",
        {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "profile_id",
                "required_directories",
                "optional_directories",
                "required_governance_artifacts",
                "required_validators",
                "branch_strategy",
                "repo_sync_mode",
                "initial_files",
                "prohibited_actions",
                "escalation_triggers",
            ],
            "properties": {
                "profile_id": {"type": "string"},
                "required_directories": {"type": "array", "items": {"type": "string"}},
                "optional_directories": {"type": "array", "items": {"type": "string"}},
                "required_governance_artifacts": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "required_validators": {"type": "array", "items": {"type": "string"}},
                "branch_strategy": {"type": "string"},
                "repo_sync_mode": {"type": "string"},
                "initial_files": {"type": "array", "items": {"type": "string"}},
                "prohibited_actions": {"type": "array", "items": {"type": "string"}},
                "escalation_triggers": {"type": "array", "items": {"type": "string"}},
            },
        },
    )
    profiles_dir = root / "profiles"
    valid_profile = dedent(
        """
        profile_id: SAMPLE
        required_directories:
          - docs
        optional_directories:
          - tests
        required_governance_artifacts:
          - governance/policies/ORA_FAIL_CLOSED_POLICY.md
        required_validators:
          - tools/validate_repo_layout.py
        branch_strategy: simple
        repo_sync_mode: local_only
        initial_files:
          - README.md
        prohibited_actions:
          - unrestricted_shell
          - deploy
          - autonomous_merge
        escalation_triggers:
          - validation_failure
        """
    ).strip()
    for name in [
        "CSL_GOVERNED.yaml",
        "STANDALONE_LIGHT.yaml",
        "STANDALONE_COMMERCIAL.yaml",
        "RESEARCH_LIBRARY.yaml",
        "SANDBOX.yaml",
    ]:
        _write_text(profiles_dir / name, valid_profile)

    result = validate_profiles(root)

    assert result.ok


def test_validate_profiles_rejects_missing_fail_closed_action(tmp_path: Path) -> None:
    root = tmp_path
    _write_json(
        root / "schemas/profile/project_profile.schema.json",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["profile_id", "prohibited_actions"],
            "properties": {
                "profile_id": {"type": "string"},
                "prohibited_actions": {"type": "array", "items": {"type": "string"}},
            },
        },
    )
    profiles_dir = root / "profiles"
    invalid_profile = dedent(
        """
        profile_id: SAMPLE
        prohibited_actions:
          - unrestricted_shell
          - deploy
        """
    ).strip()
    for name in [
        "CSL_GOVERNED.yaml",
        "STANDALONE_LIGHT.yaml",
        "STANDALONE_COMMERCIAL.yaml",
        "RESEARCH_LIBRARY.yaml",
        "SANDBOX.yaml",
    ]:
        _write_text(profiles_dir / name, invalid_profile)

    result = validate_profiles(root)

    assert not result.ok
    assert any("autonomous_merge" in error for error in result.errors)


def test_validate_registry_accepts_valid_project_registry(tmp_path: Path) -> None:
    root = tmp_path
    _write_json(
        root / "schemas/registry/repo_registry.schema.json",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["repos"],
            "properties": {
                "repos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["repo_id", "repo_name"],
                        "properties": {
                            "repo_id": {"type": "string"},
                            "repo_name": {"type": "string"},
                        },
                    },
                }
            },
        },
    )
    _write_json(
        root / "schemas/registry/project_registry.schema.json",
        {
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
        },
    )
    _write_text(root / "registry/repos.yaml", "repos: []\n")
    _write_text(root / "registry/projects.yaml", "projects:\n  - project_id: sample-project\n")

    result = validate_registry(root)

    assert result.ok


def test_validate_registry_rejects_project_registry_missing_required_field(
    tmp_path: Path,
) -> None:
    root = tmp_path
    _write_json(
        root / "schemas/registry/repo_registry.schema.json",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["repos"],
            "properties": {"repos": {"type": "array", "items": {"type": "object"}}},
        },
    )
    _write_json(
        root / "schemas/registry/project_registry.schema.json",
        {
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
        },
    )
    _write_text(root / "registry/repos.yaml", "repos: []\n")
    _write_text(root / "registry/projects.yaml", "projects:\n  - invalid_key: sample\n")

    result = validate_registry(root)

    assert not result.ok
    assert "registry/projects.yaml.projects[0]: missing required key 'project_id'" in result.errors
    assert "registry/projects.yaml.projects[0]: unexpected key 'invalid_key'" in result.errors


def test_validate_registry_rejects_project_registry_unknown_field(tmp_path: Path) -> None:
    root = tmp_path
    _write_json(
        root / "schemas/registry/repo_registry.schema.json",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["repos"],
            "properties": {"repos": {"type": "array", "items": {"type": "object"}}},
        },
    )
    _write_json(
        root / "schemas/registry/project_registry.schema.json",
        {
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
        },
    )
    _write_text(root / "registry/repos.yaml", "repos: []\n")
    _write_text(
        root / "registry/projects.yaml",
        "projects:\n  - project_id: sample\n    owner: levloc\n",
    )

    result = validate_registry(root)

    assert not result.ok
    assert "registry/projects.yaml.projects[0]: unexpected key 'owner'" in result.errors


def test_validate_registry_fails_closed_on_malformed_project_registry(
    tmp_path: Path,
) -> None:
    root = tmp_path
    _write_json(
        root / "schemas/registry/repo_registry.schema.json",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["repos"],
            "properties": {"repos": {"type": "array", "items": {"type": "object"}}},
        },
    )
    _write_json(
        root / "schemas/registry/project_registry.schema.json",
        {
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
        },
    )
    _write_text(root / "registry/repos.yaml", "repos: []\n")
    _write_text(root / "registry/projects.yaml", "projects:\n\t- project_id: sample\n")

    result = validate_registry(root)

    assert not result.ok
    assert "registry/projects.yaml:" in result.errors[0]


def test_validate_queue_accepts_empty_collections(tmp_path: Path) -> None:
    root = tmp_path
    _write_json(
        root / "schemas/queue/queue_item.schema.json",
        {
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
                "status": {
                    "type": "string",
                    "enum": ["READY_FOR_FIRST_GOVERNED_SLICE"],
                },
                "current_slice": {"type": "null"},
                "blocker": {"type": "null"},
                "escalation_required": {"type": "string", "enum": ["true"]},
            },
        },
    )
    _write_text(root / "queue/project_queue.yaml", "queue_items: []\n")
    _write_text(root / "queue/blockers.yaml", "blockers: []\n")
    _write_text(root / "queue/escalations.yaml", "escalations: []\n")

    result = validate_queue(root)

    assert result.ok


def test_validate_queue_rejects_invalid_blocker_shape(tmp_path: Path) -> None:
    root = tmp_path
    _write_json(
        root / "schemas/queue/queue_item.schema.json",
        {
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
                "status": {
                    "type": "string",
                    "enum": ["READY_FOR_FIRST_GOVERNED_SLICE"],
                },
                "current_slice": {"type": "null"},
                "blocker": {"type": "null"},
                "escalation_required": {"type": "string", "enum": ["true"]},
            },
        },
    )
    _write_text(
        root / "queue/project_queue.yaml",
        dedent(
            """
            queue_items:
              - project_id: repo-1
                repo_id: repo-1
                profile_id: CSL_GOVERNED
                status: READY_FOR_FIRST_GOVERNED_SLICE
                current_slice: null
                blocker: null
                escalation_required: true
            """
        ).strip()
        + "\n",
    )
    _write_text(
        root / "queue/blockers.yaml",
        dedent(
            """
            blockers:
              - blocker_id: blk-1
                queue_item_id: q-1
                reason: waiting
            """
        ).strip()
        + "\n",
    )
    _write_text(root / "queue/escalations.yaml", "escalations: []\n")

    result = validate_queue(root)

    assert not result.ok
    assert "queue/blockers.yaml.blockers[0]: missing required key 'status'" in result.errors


def test_validate_operation_plan_schema_validates_artifacts(tmp_path: Path) -> None:
    root = tmp_path
    _write_json(
        root / "schemas/operation/operation_plan.schema.json",
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["operation_types", "prohibited_operation_types"],
            "properties": {
                "operation_types": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["WRITE_FILE"]},
                },
                "prohibited_operation_types": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["ARBITRARY_SHELL"]},
                },
            },
        },
    )
    valid_path = root / "valid_operation_plan.json"
    invalid_path = root / "invalid_operation_plan.json"
    _write_json(
        valid_path,
        {
            "operation_types": ["WRITE_FILE"],
            "prohibited_operation_types": ["ARBITRARY_SHELL"],
        },
    )
    _write_json(
        invalid_path,
        {
            "operation_types": ["DEPLOY"],
            "prohibited_operation_types": ["ARBITRARY_SHELL"],
        },
    )

    valid_result = validate_operation_plan_schema(root, [valid_path])
    invalid_result = validate_operation_plan_schema(root, [invalid_path])

    assert valid_result.ok
    assert not invalid_result.ok
    assert (
        f"{invalid_path}: expected one of 'WRITE_FILE'" in invalid_result.errors
        or f"{invalid_path}.operation_types[0]: expected one of 'WRITE_FILE'"
        in invalid_result.errors
    )


def test_validate_handoff_packets_validates_artifacts(tmp_path: Path) -> None:
    root = tmp_path
    _write_json(
        root / "schemas/bridge/handoff_packet.schema.json",
        {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "packet_version",
                "bridge_type",
                "project_id",
                "repo_id",
                "profile_id",
                "current_queue_status",
                "requested_action",
                "authority_boundary",
                "validation_commands",
                "prohibited_actions",
                "execution_mode",
            ],
            "properties": {
                "packet_version": {"type": "string"},
                "bridge_type": {
                    "type": "string",
                    "enum": ["CHATGPT", "CLAUDE", "CODEX"],
                },
                "project_id": {"type": "string"},
                "repo_id": {"type": "string"},
                "profile_id": {"type": "string"},
                "current_queue_status": {"type": "string"},
                "requested_action": {"type": "string"},
                "authority_boundary": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "execution_mode",
                        "allowed_state_reads",
                        "human_review_required",
                        "git_operations_allowed",
                        "network_access_allowed",
                        "prompt_dispatch_allowed",
                        "queue_updates_allowed",
                        "repo_writes_allowed",
                        "subprocess_allowed",
                    ],
                    "properties": {
                        "execution_mode": {
                            "type": "string",
                            "enum": ["packet_only"],
                        },
                        "allowed_state_reads": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "human_review_required": {"type": "boolean"},
                        "git_operations_allowed": {"type": "boolean"},
                        "network_access_allowed": {"type": "boolean"},
                        "prompt_dispatch_allowed": {"type": "boolean"},
                        "queue_updates_allowed": {"type": "boolean"},
                        "repo_writes_allowed": {"type": "boolean"},
                        "subprocess_allowed": {"type": "boolean"},
                    },
                },
                "validation_commands": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "prohibited_actions": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "execution_mode": {
                    "type": "string",
                    "enum": ["packet_only"],
                },
            },
        },
    )
    valid_path = root / "valid_handoff_packet.json"
    invalid_path = root / "invalid_handoff_packet.json"
    _write_json(
        valid_path,
        {
            "packet_version": "1.0.0",
            "bridge_type": "CODEX",
            "project_id": "repo-1",
            "repo_id": "repo-1",
            "profile_id": "CSL_GOVERNED",
            "current_queue_status": "READY_FOR_FIRST_GOVERNED_SLICE",
            "requested_action": "PREPARE_GOVERNED_CODEX_HANDOFF",
            "authority_boundary": {
                "execution_mode": "packet_only",
                "allowed_state_reads": [
                    "registry/projects.yaml",
                    "registry/repos.yaml",
                    "queue/project_queue.yaml",
                ],
                "human_review_required": True,
                "git_operations_allowed": False,
                "network_access_allowed": False,
                "prompt_dispatch_allowed": False,
                "queue_updates_allowed": False,
                "repo_writes_allowed": False,
                "subprocess_allowed": False,
            },
            "validation_commands": ["pytest -q"],
            "prohibited_actions": ["execution"],
            "packet_version": "1.0.0",
            "execution_mode": "packet_only",
        },
    )
    _write_json(
        invalid_path,
        {
            "packet_version": "1.0.0",
            "bridge_type": "CODEX",
            "project_id": "repo-1",
            "repo_id": "repo-1",
            "profile_id": "CSL_GOVERNED",
            "current_queue_status": "READY_FOR_FIRST_GOVERNED_SLICE",
            "requested_action": "PREPARE_GOVERNED_CODEX_HANDOFF",
            "authority_boundary": {
                "execution_mode": "execute_now",
                "allowed_state_reads": [
                    "registry/projects.yaml",
                    "registry/repos.yaml",
                    "queue/project_queue.yaml",
                ],
                "human_review_required": True,
                "git_operations_allowed": False,
                "network_access_allowed": False,
                "prompt_dispatch_allowed": False,
                "queue_updates_allowed": False,
                "repo_writes_allowed": False,
                "subprocess_allowed": False,
            },
            "validation_commands": ["pytest -q"],
            "prohibited_actions": ["execution"],
            "packet_version": "1.0.0",
            "execution_mode": "execute_now",
        },
    )

    valid_result = validate_handoff_packets(root, [valid_path])
    invalid_result = validate_handoff_packets(root, [invalid_path])

    assert valid_result.ok
    assert not invalid_result.ok
    assert (
        f"{invalid_path}.authority_boundary.execution_mode: expected one of 'packet_only'"
        in invalid_result.errors
        or f"{invalid_path}.execution_mode: expected one of 'packet_only'"
        in invalid_result.errors
    )


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
