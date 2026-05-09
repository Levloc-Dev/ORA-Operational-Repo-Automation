from __future__ import annotations

import copy
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.pge.bootstrap_plan import build_repo_bootstrap_plan_from_file  # noqa: E402
from tools.ora_execute_bootstrap_plan import main  # noqa: E402


FIXTURE_DIR = ROOT / "tests/fixtures/pge/requests"


def test_execute_bootstrap_plan_cli_defaults_to_dry_run(
    tmp_path: Path,
    capsys,
) -> None:
    plan_path = write_plan_file(tmp_path, build_valid_plan())
    target_root = tmp_path / "dry-run-target"

    exit_code = main(
        [
            "--plan",
            str(plan_path),
            "--target-root",
            str(target_root),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.err == ""
    assert not target_root.exists()

    artifact = json.loads(captured.out)
    assert artifact["dry_run"] is True
    assert artifact["target_root"] == str(target_root.resolve())
    assert artifact["operations"][0]["status"] == "DRY_RUN"


def test_execute_bootstrap_plan_cli_fails_without_confirmation(
    tmp_path: Path,
    capsys,
) -> None:
    plan_path = write_plan_file(tmp_path, build_valid_plan())
    target_root = tmp_path / "execute-without-confirmation"

    exit_code = main(
        [
            "--plan",
            str(plan_path),
            "--target-root",
            str(target_root),
            "--execute",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "refusing to execute without --confirm-local-write" in captured.err
    assert not target_root.exists()


def test_execute_bootstrap_plan_cli_writes_only_to_explicit_temp_target(
    tmp_path: Path,
    capsys,
) -> None:
    plan_path = write_plan_file(tmp_path, build_valid_plan())
    target_root = tmp_path / "scaffold-target"
    sibling_root = tmp_path / "untouched-sibling"

    exit_code = main(
        [
            "--plan",
            str(plan_path),
            "--target-root",
            str(target_root),
            "--execute",
            "--confirm-local-write",
        ]
    )

    captured = capsys.readouterr()
    artifact = json.loads(captured.out)

    assert exit_code == 0
    assert captured.err == ""
    assert artifact["dry_run"] is False
    assert artifact["operations"][0]["status"] == "APPLIED"
    assert (target_root / "governance").is_dir()
    assert (target_root / "README.md").is_file()
    assert not sibling_root.exists()


def test_execute_bootstrap_plan_cli_fails_closed_for_invalid_plan(
    tmp_path: Path,
    capsys,
) -> None:
    invalid_plan = copy.deepcopy(build_valid_plan())
    invalid_plan["planned_operations"][0]["operation_type"] = "DELETE_FILE"
    plan_path = write_plan_file(tmp_path, invalid_plan)
    target_root = tmp_path / "invalid-plan-target"

    exit_code = main(
        [
            "--plan",
            str(plan_path),
            "--target-root",
            str(target_root),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "expected one of 'CREATE_DIRECTORY', 'WRITE_FILE'" in captured.err
    assert not target_root.exists()


def test_execute_bootstrap_plan_cli_emits_deterministic_json(
    tmp_path: Path,
    capsys,
) -> None:
    plan_path = write_plan_file(tmp_path, build_valid_plan())
    target_root = tmp_path / "deterministic-dry-run-target"

    first_exit_code = main(
        [
            "--plan",
            str(plan_path),
            "--target-root",
            str(target_root),
        ]
    )
    first_output = capsys.readouterr()

    second_exit_code = main(
        [
            "--plan",
            str(plan_path),
            "--target-root",
            str(target_root),
        ]
    )
    second_output = capsys.readouterr()

    assert first_exit_code == 0
    assert second_exit_code == 0
    assert first_output.err == ""
    assert second_output.err == ""
    assert first_output.out == second_output.out


def build_valid_plan() -> dict[str, object]:
    return build_repo_bootstrap_plan_from_file(FIXTURE_DIR / "valid_csl_governed.yaml")


def write_plan_file(tmp_path: Path, plan: dict[str, object]) -> Path:
    plan_path = tmp_path / "repo_bootstrap_plan.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan_path
