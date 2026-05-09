from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.pge.bootstrap_plan import build_repo_bootstrap_plan_from_file  # noqa: E402
from ora.pge.scaffold_writer import (  # noqa: E402
    APPLIED_STATUS,
    DRY_RUN_STATUS,
    ScaffoldWriterError,
    execute_repo_bootstrap_plan,
)


FIXTURE_DIR = ROOT / "tests/fixtures/pge/requests"


def test_execute_repo_bootstrap_plan_supports_dry_run_without_writes(
    tmp_path: Path,
) -> None:
    plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")
    target_root = tmp_path / "dry-run-target"

    artifact = execute_repo_bootstrap_plan(plan, target_root=target_root, dry_run=True)

    assert artifact["dry_run"] is True
    assert artifact["operation_count"] == len(plan["planned_operations"])
    assert artifact["operations"][0]["status"] == DRY_RUN_STATUS
    assert artifact["operations"][0]["normalized_target_path"] == "governance"
    assert artifact["operations"][-1]["normalized_target_path"] == "ORA_SOURCE_CONTEXT_v1.0.0.md"
    readme_operation = next(
        operation
        for operation in artifact["operations"]
        if operation["normalized_target_path"] == "README.md"
    )
    assert readme_operation["content_sha256"] == hashlib.sha256(
        b"# ORA-Slice-3-Example\n\nGenerated from the ORA Slice 1 deterministic scaffold.\n"
    ).hexdigest()
    assert not target_root.exists()


def test_execute_repo_bootstrap_plan_writes_controlled_scaffold(
    tmp_path: Path,
) -> None:
    plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")
    target_root = tmp_path / "scaffolded-repo"

    artifact = execute_repo_bootstrap_plan(plan, target_root=target_root)

    assert artifact["dry_run"] is False
    assert artifact["operations"][0]["status"] == APPLIED_STATUS
    assert (target_root / "governance").is_dir()
    assert (target_root / "governance/constitution").is_dir()
    assert (target_root / "README.md").read_text(encoding="utf-8") == (
        "# ORA-Slice-3-Example\n\n"
        "Generated from the ORA Slice 1 deterministic scaffold.\n"
    )
    assert (target_root / "PROJECT_CONTEXT.md").read_text(encoding="utf-8") == (
        ROOT / "PROJECT_CONTEXT.md"
    ).read_text(encoding="utf-8")
    assert (target_root / "ORA_SOURCE_CONTEXT_v1.0.0.md").read_text(encoding="utf-8") == (
        ROOT / "ORA_SOURCE_CONTEXT_v1.0.0.md"
    ).read_text(encoding="utf-8")


def test_execute_repo_bootstrap_plan_rejects_path_traversal(
    tmp_path: Path,
) -> None:
    plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")
    mutated_plan = copy.deepcopy(plan)
    mutated_plan["planned_operations"][0]["target_path"] = "../escape"

    with pytest.raises(ScaffoldWriterError, match="path traversal is not allowed"):
        execute_repo_bootstrap_plan(
            mutated_plan,
            target_root=tmp_path / "rejected-target",
        )

    assert not (tmp_path / "rejected-target").exists()


def test_execute_repo_bootstrap_plan_rejects_duplicate_operations(
    tmp_path: Path,
) -> None:
    plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")
    mutated_plan = copy.deepcopy(plan)
    mutated_plan["planned_operations"][1]["operation_id"] = mutated_plan["planned_operations"][0][
        "operation_id"
    ]

    with pytest.raises(ScaffoldWriterError, match="duplicate operation_id"):
        execute_repo_bootstrap_plan(
            mutated_plan,
            target_root=tmp_path / "duplicate-target",
        )


def test_execute_repo_bootstrap_plan_rejects_unknown_operation_type(
    tmp_path: Path,
) -> None:
    plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")
    mutated_plan = copy.deepcopy(plan)
    mutated_plan["planned_operations"][0]["operation_type"] = "DELETE_FILE"

    with pytest.raises(ScaffoldWriterError, match="expected one of 'CREATE_DIRECTORY', 'WRITE_FILE'"):
        execute_repo_bootstrap_plan(
            mutated_plan,
            target_root=tmp_path / "unknown-operation-target",
        )


def test_execute_repo_bootstrap_plan_rejects_missing_template(
    tmp_path: Path,
) -> None:
    plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")
    execution_root = tmp_path / "execution-root"
    (execution_root / "schemas/pge").mkdir(parents=True)
    (execution_root / "governance/constitution").mkdir(parents=True)
    (execution_root / "governance/control_plane").mkdir(parents=True)
    (execution_root / "schemas/pge/repo_bootstrap_plan.schema.json").write_text(
        (ROOT / "schemas/pge/repo_bootstrap_plan.schema.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (execution_root / "governance/constitution/AI_CONSTITUTION.md").write_text(
        (ROOT / "governance/constitution/AI_CONSTITUTION.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (execution_root / "governance/control_plane/DECISION_GATE.md").write_text(
        (ROOT / "governance/control_plane/DECISION_GATE.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (execution_root / "PROJECT_CONTEXT.md").write_text(
        (ROOT / "PROJECT_CONTEXT.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (execution_root / "ORA_SOURCE_CONTEXT_v1.0.0.md").write_text(
        (ROOT / "ORA_SOURCE_CONTEXT_v1.0.0.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    with pytest.raises(ScaffoldWriterError, match="missing template"):
        execute_repo_bootstrap_plan(
            plan,
            target_root=tmp_path / "missing-template-target",
            root=execution_root,
        )


def test_execute_repo_bootstrap_plan_is_deterministic_across_repeated_execution(
    tmp_path: Path,
) -> None:
    plan = build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")
    target_root = tmp_path / "repeat-target"

    first_artifact = execute_repo_bootstrap_plan(plan, target_root=target_root)
    second_artifact = execute_repo_bootstrap_plan(plan, target_root=target_root)

    assert first_artifact == second_artifact
    assert (target_root / "README.md").read_text(encoding="utf-8") == (
        "# ORA-Slice-3-Example\n\n"
        "Generated from the ORA Slice 1 deterministic scaffold.\n"
    )
