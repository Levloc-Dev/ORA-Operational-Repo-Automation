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
)


FIXTURE_DIR = ROOT / "tests/fixtures/pge/requests"


def test_build_repo_bootstrap_plan_generates_valid_csl_governed_plan() -> None:
    plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")

    assert plan == {
        "plan_version": "1.0.0",
        "project_name": "ORA-Slice-3-Example",
        "project_profile": "CSL_GOVERNED",
        "create_directories": [
            "governance",
            "memory",
            "planning",
            "docs",
            "schemas",
            "governance/constitution",
            "governance/control_plane",
        ],
        "write_files": [
            "governance/constitution/AI_CONSTITUTION.md",
            "governance/control_plane/DECISION_GATE.md",
            "README.md",
            "PROJECT_CONTEXT.md",
            "ORA_SOURCE_CONTEXT_v1.0.0.md",
        ],
        "validators": [
            "tools/validate_repo_layout.py",
            "tools/validate_profiles.py",
        ],
        "escalation_required": True,
    }


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
                    "create_directories",
                    "write_files",
                    "validators",
                    "escalation_required",
                    "approval_ticket",
                ],
                "properties": {
                    "plan_version": {"type": "string"},
                    "project_name": {"type": "string"},
                    "project_profile": {"type": "string"},
                    "create_directories": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "write_files": {
                        "type": "array",
                        "items": {"type": "string"},
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
