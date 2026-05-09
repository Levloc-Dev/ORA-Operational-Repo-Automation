from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.pge.bootstrap_plan import (  # noqa: E402
    BootstrapPlanError,
    build_repo_bootstrap_plan_from_file,
    validate_repo_bootstrap_plan,
)


FIXTURE_DIR = ROOT / "tests/fixtures/pge/requests"


def test_build_repo_bootstrap_plan_generates_valid_csl_governed_plan() -> None:
    plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")

    assert plan == {
        "plan_version": "1.0.0",
        "project_name": "ORA-Slice-3-Example",
        "project_profile": "CSL_GOVERNED",
        "planned_operations": [
            {
                "operation_id": "CREATE_DIRECTORY:governance",
                "operation_type": "CREATE_DIRECTORY",
                "target_path": "governance",
                "source_template": None,
                "content_strategy": "DECLARE_DIRECTORY",
                "authority_required": "LOCAL_REPO_WRITE_ESCALATION",
                "validation_required": True,
            },
            {
                "operation_id": "CREATE_DIRECTORY:memory",
                "operation_type": "CREATE_DIRECTORY",
                "target_path": "memory",
                "source_template": None,
                "content_strategy": "DECLARE_DIRECTORY",
                "authority_required": "LOCAL_REPO_WRITE_ESCALATION",
                "validation_required": True,
            },
            {
                "operation_id": "CREATE_DIRECTORY:planning",
                "operation_type": "CREATE_DIRECTORY",
                "target_path": "planning",
                "source_template": None,
                "content_strategy": "DECLARE_DIRECTORY",
                "authority_required": "LOCAL_REPO_WRITE_ESCALATION",
                "validation_required": True,
            },
            {
                "operation_id": "CREATE_DIRECTORY:docs",
                "operation_type": "CREATE_DIRECTORY",
                "target_path": "docs",
                "source_template": None,
                "content_strategy": "DECLARE_DIRECTORY",
                "authority_required": "LOCAL_REPO_WRITE_ESCALATION",
                "validation_required": True,
            },
            {
                "operation_id": "CREATE_DIRECTORY:schemas",
                "operation_type": "CREATE_DIRECTORY",
                "target_path": "schemas",
                "source_template": None,
                "content_strategy": "DECLARE_DIRECTORY",
                "authority_required": "LOCAL_REPO_WRITE_ESCALATION",
                "validation_required": True,
            },
            {
                "operation_id": "CREATE_DIRECTORY:governance/constitution",
                "operation_type": "CREATE_DIRECTORY",
                "target_path": "governance/constitution",
                "source_template": None,
                "content_strategy": "DECLARE_DIRECTORY",
                "authority_required": "LOCAL_REPO_WRITE_ESCALATION",
                "validation_required": True,
            },
            {
                "operation_id": "CREATE_DIRECTORY:governance/control_plane",
                "operation_type": "CREATE_DIRECTORY",
                "target_path": "governance/control_plane",
                "source_template": None,
                "content_strategy": "DECLARE_DIRECTORY",
                "authority_required": "LOCAL_REPO_WRITE_ESCALATION",
                "validation_required": True,
            },
            {
                "operation_id": "WRITE_FILE:governance/constitution/AI_CONSTITUTION.md",
                "operation_type": "WRITE_FILE",
                "target_path": "governance/constitution/AI_CONSTITUTION.md",
                "source_template": "governance/constitution/AI_CONSTITUTION.md",
                "content_strategy": "COPY_CANONICAL_SOURCE",
                "authority_required": "LOCAL_REPO_WRITE_ESCALATION",
                "validation_required": True,
            },
            {
                "operation_id": "WRITE_FILE:governance/control_plane/DECISION_GATE.md",
                "operation_type": "WRITE_FILE",
                "target_path": "governance/control_plane/DECISION_GATE.md",
                "source_template": "governance/control_plane/DECISION_GATE.md",
                "content_strategy": "COPY_CANONICAL_SOURCE",
                "authority_required": "LOCAL_REPO_WRITE_ESCALATION",
                "validation_required": True,
            },
            {
                "operation_id": "WRITE_FILE:README.md",
                "operation_type": "WRITE_FILE",
                "target_path": "README.md",
                "source_template": "templates/common/README.template.md",
                "content_strategy": "RENDER_TEMPLATE",
                "authority_required": "LOCAL_REPO_WRITE_ESCALATION",
                "validation_required": True,
            },
            {
                "operation_id": "WRITE_FILE:PROJECT_CONTEXT.md",
                "operation_type": "WRITE_FILE",
                "target_path": "PROJECT_CONTEXT.md",
                "source_template": "PROJECT_CONTEXT.md",
                "content_strategy": "COPY_CANONICAL_SOURCE",
                "authority_required": "LOCAL_REPO_WRITE_ESCALATION",
                "validation_required": True,
            },
            {
                "operation_id": "WRITE_FILE:ORA_SOURCE_CONTEXT_v1.0.0.md",
                "operation_type": "WRITE_FILE",
                "target_path": "ORA_SOURCE_CONTEXT_v1.0.0.md",
                "source_template": "ORA_SOURCE_CONTEXT_v1.0.0.md",
                "content_strategy": "COPY_CANONICAL_SOURCE",
                "authority_required": "LOCAL_REPO_WRITE_ESCALATION",
                "validation_required": True,
            },
        ],
        "validators": [
            "tools/validate_repo_layout.py",
            "tools/validate_profiles.py",
        ],
        "escalation_required": True,
    }


def test_build_repo_bootstrap_plan_is_byte_identical_across_repeated_runs() -> None:
    first_plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")
    second_plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")

    first_json = json.dumps(first_plan, indent=2, sort_keys=False)
    second_json = json.dumps(second_plan, indent=2, sort_keys=False)

    assert first_json == second_json


def test_build_repo_bootstrap_plan_fails_closed_for_unknown_profile() -> None:
    with pytest.raises(BootstrapPlanError, match="unknown profile_id 'UNKNOWN_PROFILE'"):
        build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "invalid_unknown_profile.yaml")


def test_build_repo_bootstrap_plan_fails_closed_for_missing_required_request_field() -> None:
    with pytest.raises(BootstrapPlanError, match="missing required key 'local_path'"):
        build_repo_bootstrap_plan_from_file(
            FIXTURE_DIR / "invalid_missing_local_path.yaml"
        )


def test_build_repo_bootstrap_plan_fails_closed_for_generated_plan_schema_failure(
    tmp_path: Path,
) -> None:
    schema_path = tmp_path / "repo_bootstrap_plan.schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "ora://schemas/pge/repo_bootstrap_plan.schema.json",
                "title": "ORA Repo Bootstrap Plan",
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "plan_version",
                    "project_name",
                    "project_profile",
                    "planned_operations",
                    "validators",
                    "escalation_required",
                    "approval_ticket",
                ],
                "properties": {
                    "plan_version": {"type": "string"},
                    "project_name": {"type": "string"},
                    "project_profile": {"type": "string"},
                    "planned_operations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "operation_id",
                                "operation_type",
                                "target_path",
                                "source_template",
                                "content_strategy",
                                "authority_required",
                                "validation_required",
                            ],
                            "properties": {
                                "operation_id": {"type": "string"},
                                "operation_type": {"type": "string"},
                                "target_path": {"type": "string"},
                                "source_template": {
                                    "type": ["string", "null"],
                                },
                                "content_strategy": {"type": "string"},
                                "authority_required": {"type": "string"},
                                "validation_required": {"type": "boolean"},
                            },
                        },
                    },
                    "validators": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "escalation_required": {"type": "boolean"},
                    "approval_ticket": {"type": "string"},
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    with pytest.raises(BootstrapPlanError, match="missing required key 'approval_ticket'"):
        build_repo_bootstrap_plan_from_file(
            FIXTURE_DIR / "valid_csl_governed.yaml",
            plan_schema_path=schema_path,
        )


def test_repo_bootstrap_plan_schema_rejects_unknown_operation_type() -> None:
    plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")
    plan["planned_operations"][0]["operation_type"] = "DELETE_FILE"

    validation = validate_repo_bootstrap_plan(plan, root=ROOT)

    assert not validation.ok
    assert (
        "repo_bootstrap_plan.planned_operations[0].operation_type: expected one of "
        "'CREATE_DIRECTORY', 'WRITE_FILE'"
    ) in validation.errors


def test_repo_bootstrap_plan_schema_rejects_unknown_authority_required() -> None:
    plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")
    plan["planned_operations"][0]["authority_required"] = "UNRESTRICTED_SHELL"

    validation = validate_repo_bootstrap_plan(plan, root=ROOT)

    assert not validation.ok
    assert (
        "repo_bootstrap_plan.planned_operations[0].authority_required: expected one of "
        "'LOCAL_REPO_WRITE_ESCALATION'"
    ) in validation.errors


def test_repo_bootstrap_plan_schema_rejects_missing_operation_id() -> None:
    plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")
    del plan["planned_operations"][0]["operation_id"]

    validation = validate_repo_bootstrap_plan(plan, root=ROOT)

    assert not validation.ok
    assert (
        "repo_bootstrap_plan.planned_operations[0]: missing required key 'operation_id'"
    ) in validation.errors


def test_generated_csl_governed_plan_validates_against_hardened_schema() -> None:
    plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")

    validation = validate_repo_bootstrap_plan(plan, root=ROOT)

    assert validation.ok
