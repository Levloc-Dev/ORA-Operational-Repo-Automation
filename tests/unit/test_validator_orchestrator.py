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

from ora.validation.validator_orchestrator import (  # noqa: E402
    ValidatorOrchestratorError,
    build_validator_plan,
    render_validator_plan_json,
)
from ora.validation.result_capture import build_result_artifact_path  # noqa: E402
from tools.ora_execute_validator import main as execute_main  # noqa: E402
from tools.ora_run_validators import main  # noqa: E402


def test_build_validator_plan_generates_valid_csl_governed_plan(
    tmp_path: Path,
) -> None:
    root = make_validator_root(tmp_path, profile_id="CSL_GOVERNED")

    plan = build_validator_plan("repo-1", root=root)

    assert plan == {
        "plan_version": "1.0.0",
        "project_id": "repo-1",
        "repo_id": "repo-1",
        "repo_path": "/tmp/repo-1",
        "profile_id": "CSL_GOVERNED",
        "execution_mode": "PLAN_ONLY",
        "validators": [
            "tools/validate_repo_layout.py",
            "tools/validate_profiles.py",
        ],
        "authority_boundary": {
            "execution_mode": "PLAN_ONLY",
            "allowed_state_reads": [
                "registry/projects.yaml",
                "registry/repos.yaml",
                "queue/project_queue.yaml",
            ],
            "validator_execution_allowed": False,
            "git_operations_allowed": False,
            "network_access_allowed": False,
            "queue_updates_allowed": False,
            "repo_writes_allowed": False,
            "subprocess_allowed": False,
        },
        "prohibited_actions": [
            "unrestricted_shell",
            "deploy",
            "autonomous_merge",
            "self_modify_governance",
        ],
    }


def test_build_validator_plan_generates_valid_standalone_light_plan(
    tmp_path: Path,
) -> None:
    root = make_validator_root(tmp_path, profile_id="STANDALONE_LIGHT")

    plan = build_validator_plan("repo-1", root=root)

    assert plan["profile_id"] == "STANDALONE_LIGHT"
    assert plan["repo_path"] == "/tmp/repo-1"
    assert plan["validators"] == ["tools/validate_repo_layout.py"]
    assert plan["prohibited_actions"] == [
        "unrestricted_shell",
        "deploy",
        "autonomous_merge",
    ]
    assert plan["execution_mode"] == "PLAN_ONLY"
    assert plan["authority_boundary"]["execution_mode"] == "PLAN_ONLY"


def test_build_validator_plan_rejects_unknown_project(tmp_path: Path) -> None:
    root = make_validator_root(tmp_path, projects_yaml="projects: []\n")

    with pytest.raises(ValidatorOrchestratorError, match="unknown project_id 'repo-1'"):
        build_validator_plan("repo-1", root=root)


def test_build_validator_plan_rejects_project_not_in_queue(tmp_path: Path) -> None:
    root = make_validator_root(tmp_path, queue_yaml="queue_items: []\n")

    with pytest.raises(
        ValidatorOrchestratorError,
        match="project_id 'repo-1' is not present in queue/project_queue.yaml",
    ):
        build_validator_plan("repo-1", root=root)


def test_ora_run_validators_output_is_byte_identical(tmp_path: Path, capsys) -> None:
    root = make_validator_root(tmp_path, profile_id="CSL_GOVERNED")

    first_exit_code = main(["--project-id", "repo-1"], root=root)
    first_output = capsys.readouterr()

    second_exit_code = main(["--project-id", "repo-1"], root=root)
    second_output = capsys.readouterr()

    assert first_exit_code == 0
    assert second_exit_code == 0
    assert first_output.err == ""
    assert second_output.err == ""
    assert first_output.out == second_output.out
    assert first_output.out == render_validator_plan_json(
        build_validator_plan("repo-1", root=root)
    )


def test_ora_run_validators_rejects_missing_repo_registry_entry(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_validator_root(tmp_path, repos_yaml="repos: []\n")

    exit_code = main(["--project-id", "repo-1"], root=root)
    output = capsys.readouterr()

    assert exit_code == 1
    assert output.err == ""
    assert json.loads(output.out) == {
        "error": "missing repo registry entry for repo_id 'repo-1'",
        "generated": False,
        "project_id": "repo-1",
    }


def test_ora_execute_validator_writes_result_artifact_for_allowed_validator(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_validator_root(tmp_path, profile_id="CSL_GOVERNED")

    exit_code = execute_main(
        [
            "--project-id",
            "repo-1",
            "--validator-id",
            "tools/validate_profiles.py",
        ],
        root=root,
    )
    output = capsys.readouterr()

    assert exit_code == 0
    document = json.loads(output.out)
    assert document["result_status"] == "PASS"
    assert document["validator_id"] == "tools/validate_profiles.py"
    assert document["failure_reason"] is None
    assert document["validator_output"] == {
        "errors": [],
        "ok": True,
        "summary": "profile validation passed",
        "validator_id": "tools/validate_profiles.py",
    }

    artifact_path = build_result_artifact_path(
        project_id="repo-1",
        validator_id="tools/validate_profiles.py",
        output_format="json",
        root=root,
    )
    assert artifact_path.exists()
    assert json.loads(artifact_path.read_text(encoding="utf-8")) == document


def test_ora_execute_validator_rejects_undeclared_validator_request(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_validator_root(tmp_path, profile_id="STANDALONE_LIGHT")

    exit_code = execute_main(
        [
            "--project-id",
            "repo-1",
            "--validator-id",
            "tools/validate_profiles.py",
        ],
        root=root,
    )
    output = capsys.readouterr()

    assert exit_code == 1
    assert json.loads(output.out) == {
        "error": "undeclared validator execution request 'tools/validate_profiles.py' for project_id 'repo-1'",
        "executed": False,
        "project_id": "repo-1",
        "validator_id": "tools/validate_profiles.py",
    }


def test_ora_execute_validator_rejects_unknown_validator_id(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_validator_root(tmp_path, profile_id="CSL_GOVERNED")

    exit_code = execute_main(
        [
            "--project-id",
            "repo-1",
            "--validator-id",
            "tools/unknown.py",
        ],
        root=root,
    )
    output = capsys.readouterr()

    assert exit_code == 1
    assert json.loads(output.out) == {
        "error": "unknown validator_id 'tools/unknown.py'",
        "executed": False,
        "project_id": "repo-1",
        "validator_id": "tools/unknown.py",
    }


def test_ora_execute_validator_fails_closed_on_malformed_validator_output(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_validator_root(tmp_path, profile_id="CSL_GOVERNED")
    write_text(
        root / "tools/validate_profiles.py",
        "#!/usr/bin/env python3\n"
        "print('not-json')\n",
    )

    exit_code = execute_main(
        [
            "--project-id",
            "repo-1",
            "--validator-id",
            "tools/validate_profiles.py",
        ],
        root=root,
    )
    output = capsys.readouterr()
    document = json.loads(output.out)

    assert exit_code == 1
    assert document["result_status"] == "ERROR"
    assert document["failure_reason"] == (
        "malformed result output for 'tools/validate_profiles.py': invalid JSON"
    )
    assert document["validator_output"] is None


def test_ora_execute_validator_fails_closed_on_missing_validator_command(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_validator_root(tmp_path, profile_id="CSL_GOVERNED")
    (root / "tools/validate_profiles.py").unlink()

    exit_code = execute_main(
        [
            "--project-id",
            "repo-1",
            "--validator-id",
            "tools/validate_profiles.py",
        ],
        root=root,
    )
    output = capsys.readouterr()

    assert exit_code == 1
    assert json.loads(output.out) == {
        "error": "missing validator command for 'tools/validate_profiles.py': tools/validate_profiles.py",
        "executed": False,
        "project_id": "repo-1",
        "validator_id": "tools/validate_profiles.py",
    }


def test_ora_execute_validator_fails_closed_on_non_zero_exit_code(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_validator_root(tmp_path, profile_id="CSL_GOVERNED")
    write_text(
        root / "tools/validate_profiles.py",
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('{\"validator_id\":\"tools/validate_profiles.py\",\"ok\":false,\"summary\":\"failed\",\"errors\":[\"boom\"]}')\n"
        "raise SystemExit(3)\n",
    )

    exit_code = execute_main(
        [
            "--project-id",
            "repo-1",
            "--validator-id",
            "tools/validate_profiles.py",
        ],
        root=root,
    )
    output = capsys.readouterr()
    document = json.loads(output.out)

    assert exit_code == 1
    assert document["result_status"] == "FAIL"
    assert document["exit_code"] == 3
    assert document["failure_reason"] == "validator exited with code 3"


def make_validator_root(
    tmp_path: Path,
    *,
    profile_id: str = "CSL_GOVERNED",
    projects_yaml: str | None = None,
    repos_yaml: str | None = None,
    queue_yaml: str | None = None,
) -> Path:
    root = tmp_path / "root"
    (root / "registry").mkdir(parents=True)
    (root / "queue").mkdir()
    (root / "profiles").mkdir()
    (root / "schemas/profile").mkdir(parents=True)
    (root / "schemas/validation").mkdir(parents=True)
    (root / "src/ora/validation").mkdir(parents=True, exist_ok=True)
    (root / "governance/workflows/validation_reports").mkdir(parents=True)
    (root / "tools").mkdir(exist_ok=True)

    write_text(
        root / "registry/projects.yaml",
        projects_yaml
        or (
            "projects:\n"
            "  - project_id: repo-1\n"
        ),
    )
    write_text(
        root / "registry/repos.yaml",
        repos_yaml
        or build_repos_yaml(profile_id),
    )
    for source_profile in [
        "CSL_GOVERNED",
        "STANDALONE_LIGHT",
        "STANDALONE_COMMERCIAL",
        "RESEARCH_LIBRARY",
        "SANDBOX",
    ]:
        write_text(
            root / "profiles" / f"{source_profile}.yaml",
            (ROOT / "profiles" / f"{source_profile}.yaml").read_text(
                encoding="utf-8"
            ),
        )
    write_text(
        root / "schemas/profile/project_profile.schema.json",
        (ROOT / "schemas/profile/project_profile.schema.json").read_text(
            encoding="utf-8"
        ),
    )
    write_text(
        root / "schemas/validation/validator_result.schema.json",
        (ROOT / "schemas/validation/validator_result.schema.json").read_text(
            encoding="utf-8"
        ),
    )
    write_text(
        root / "queue/project_queue.yaml",
        queue_yaml
        or build_queue_yaml(profile_id),
    )
    copy_validator_runtime(root)
    return root


def build_repos_yaml(profile_id: str) -> str:
    validators = validator_lines(profile_id)
    return (
        "repos:\n"
        "  - repo_id: repo-1\n"
        "    repo_name: repo-1\n"
        f"    project_profile: {profile_id}\n"
        "    local_path: /tmp/repo-1\n"
        "    github_dev_remote: null\n"
        "    github_main_remote: null\n"
        "    default_branch: main\n"
        "    active_branch: dev\n"
        f"    governance_mode: {profile_id}\n"
        "    validator_set:\n"
        f"{validators}"
        "    sync_mode: dev_main_packet_only\n"
        "    current_queue_item: null\n"
        "    last_known_status: APPLIED\n"
    )


def build_queue_yaml(profile_id: str) -> str:
    return (
        "queue_items:\n"
        "  - project_id: repo-1\n"
        "    repo_id: repo-1\n"
        f"    profile_id: {profile_id}\n"
        "    status: READY_FOR_FIRST_GOVERNED_SLICE\n"
        "    current_slice: null\n"
        "    blocker: null\n"
        "    escalation_required: true\n"
    )


def validator_lines(profile_id: str) -> str:
    validator_map = {
        "CSL_GOVERNED": [
            "tools/validate_repo_layout.py",
            "tools/validate_profiles.py",
        ],
        "STANDALONE_LIGHT": [
            "tools/validate_repo_layout.py",
        ],
    }
    validators = validator_map.get(profile_id, ["tools/validate_repo_layout.py"])
    return "".join(f"      - {validator}\n" for validator in validators)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_validator_runtime(root: Path) -> None:
    for relative_path in [
        "src/ora/__init__.py",
        "src/ora/validation/__init__.py",
        "src/ora/validation/schema_subset.py",
        "src/ora/validation/result_capture.py",
        "src/ora/validation/validator_orchestrator.py",
        "src/ora/pge/bootstrap_plan.py",
        "tools/validate_repo_layout.py",
        "tools/validate_profiles.py",
    ]:
        write_text(
            root / relative_path,
            (ROOT / relative_path).read_text(encoding="utf-8"),
        )
