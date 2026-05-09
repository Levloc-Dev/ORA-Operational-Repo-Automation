from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.registry.repo_registry import admit_repo_from_execution_artifact  # noqa: E402
from ora.validation.schema_subset import load_yaml_subset_file  # noqa: E402
from tools.ora_register_repo import main  # noqa: E402
from tools.validate_registry import validate_registry  # noqa: E402


def test_admit_repo_from_execution_artifact_updates_registries(
    tmp_path: Path,
) -> None:
    root = make_registry_root(tmp_path)
    target_root = tmp_path / "scaffolded-repo"
    request_path = write_request_file(tmp_path, local_path=target_root)
    artifact_path = write_execution_artifact_file(
        tmp_path,
        target_root=target_root,
    )

    result = admit_repo_from_execution_artifact(request_path, artifact_path, root=root)

    assert result == {
        "status": "ADMITTED",
        "admitted": True,
        "request_path": str(request_path),
        "execution_result_path": str(artifact_path),
        "repo_id": "ora-slice-5-example",
        "project_id": "ora-slice-5-example",
        "updated_files": ["registry/repos.yaml", "registry/projects.yaml"],
        "errors": [],
    }

    repo_document = load_yaml_as_jsonish(root / "registry/repos.yaml")
    assert repo_document == {
        "repos": [
            {
                "repo_id": "ora-slice-5-example",
                "repo_name": "ORA-Slice-5-Example",
                "project_profile": "CSL_GOVERNED",
                "local_path": str(target_root.resolve()),
                "github_dev_remote": None,
                "github_main_remote": None,
                "default_branch": "main",
                "active_branch": "dev",
                "governance_mode": "CSL_GOVERNED",
                "validator_set": [
                    "tools/validate_repo_layout.py",
                    "tools/validate_profiles.py",
                ],
                "sync_mode": "dev_main_packet_only",
                "current_queue_item": None,
                "last_known_status": "APPLIED",
            }
        ]
    }
    assert load_yaml_as_jsonish(root / "registry/projects.yaml") == {
        "projects": [{"project_id": "ora-slice-5-example"}]
    }
    assert validate_registry(root).ok


def test_admit_repo_from_execution_artifact_rejects_dry_run_artifact(
    tmp_path: Path,
) -> None:
    root = make_registry_root(tmp_path)
    target_root = tmp_path / "dry-run-target"
    request_path = write_request_file(tmp_path, local_path=target_root)
    artifact_path = write_execution_artifact_file(
        tmp_path,
        target_root=target_root,
        dry_run=True,
        statuses=["DRY_RUN", "DRY_RUN"],
    )

    result = admit_repo_from_execution_artifact(request_path, artifact_path, root=root)

    assert result["admitted"] is False
    assert result["status"] == "REJECTED"
    assert "execution artifact must declare dry_run: false" in result["errors"]
    assert load_yaml_as_jsonish(root / "registry/repos.yaml") == {"repos": []}
    assert load_yaml_as_jsonish(root / "registry/projects.yaml") == {"projects": []}


def test_admit_repo_from_execution_artifact_rejects_failed_operations(
    tmp_path: Path,
) -> None:
    root = make_registry_root(tmp_path)
    target_root = tmp_path / "failed-target"
    request_path = write_request_file(tmp_path, local_path=target_root)
    artifact_path = write_execution_artifact_file(
        tmp_path,
        target_root=target_root,
        statuses=["APPLIED", "FAILED"],
    )

    result = admit_repo_from_execution_artifact(request_path, artifact_path, root=root)

    assert result["admitted"] is False
    assert (
        "execution artifact operations[1] status must be one of ALREADY_PRESENT, APPLIED"
        in result["errors"]
    )


def test_admit_repo_from_execution_artifact_rejects_metadata_mismatch(
    tmp_path: Path,
) -> None:
    root = make_registry_root(tmp_path)
    request_path = write_request_file(tmp_path, local_path=tmp_path / "requested-target")
    artifact_path = write_execution_artifact_file(
        tmp_path,
        target_root=tmp_path / "actual-target",
        project_name="Wrong-Repo-Name",
    )

    result = admit_repo_from_execution_artifact(request_path, artifact_path, root=root)

    assert result["admitted"] is False
    assert "execution artifact target_root does not match request local_path" in result["errors"]
    assert (
        "execution artifact project_name does not match request repo_name"
        in result["errors"]
    )


def test_admit_repo_from_execution_artifact_rejects_duplicate_ids(
    tmp_path: Path,
) -> None:
    root = make_registry_root(
        tmp_path,
        repos_yaml=(
            "repos:\n"
            "  - repo_id: ora-slice-5-example\n"
            "    repo_name: Existing\n"
            "    project_profile: CSL_GOVERNED\n"
            "    local_path: /tmp/existing\n"
            "    github_dev_remote: null\n"
            "    github_main_remote: null\n"
            "    default_branch: main\n"
            "    active_branch: dev\n"
            "    governance_mode: CSL_GOVERNED\n"
            "    validator_set:\n"
            "      - tools/validate_repo_layout.py\n"
            "      - tools/validate_profiles.py\n"
            "    sync_mode: dev_main_packet_only\n"
            "    current_queue_item: null\n"
            "    last_known_status: APPLIED\n"
        ),
        projects_yaml="projects:\n  - project_id: ora-slice-5-example\n",
    )
    target_root = tmp_path / "duplicate-target"
    request_path = write_request_file(tmp_path, local_path=target_root)
    artifact_path = write_execution_artifact_file(
        tmp_path,
        target_root=target_root,
    )

    result = admit_repo_from_execution_artifact(request_path, artifact_path, root=root)

    assert result["admitted"] is False
    assert "duplicate repo_id 'ora-slice-5-example'" in result["errors"]
    assert "duplicate project_id 'ora-slice-5-example'" in result["errors"]


def test_admit_repo_from_execution_artifact_rejects_malformed_registry_files(
    tmp_path: Path,
) -> None:
    root = make_registry_root(
        tmp_path,
        repos_yaml="repos:\n\t- repo_id: invalid\n",
        projects_yaml="projects: []\n",
    )
    target_root = tmp_path / "malformed-registry-target"
    request_path = write_request_file(tmp_path, local_path=target_root)
    artifact_path = write_execution_artifact_file(
        tmp_path,
        target_root=target_root,
    )

    original_repos = (root / "registry/repos.yaml").read_text(encoding="utf-8")
    original_projects = (root / "registry/projects.yaml").read_text(encoding="utf-8")

    result = admit_repo_from_execution_artifact(request_path, artifact_path, root=root)

    assert result["admitted"] is False
    assert any(error.startswith("registry/repos.yaml:") for error in result["errors"])
    assert (root / "registry/repos.yaml").read_text(encoding="utf-8") == original_repos
    assert (root / "registry/projects.yaml").read_text(encoding="utf-8") == original_projects


def test_ora_register_repo_cli_emits_deterministic_json(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_registry_root(tmp_path)
    request_path = write_request_file(tmp_path, local_path=tmp_path / "cli-target")
    artifact_path = write_execution_artifact_file(
        tmp_path,
        target_root=tmp_path / "different-target",
    )

    first_exit_code = main(
        [
            "--request",
            str(request_path),
            "--execution-result",
            str(artifact_path),
        ],
        root=root,
    )
    first_output = capsys.readouterr()

    second_exit_code = main(
        [
            "--request",
            str(request_path),
            "--execution-result",
            str(artifact_path),
        ],
        root=root,
    )
    second_output = capsys.readouterr()

    assert first_exit_code == 1
    assert second_exit_code == 1
    assert first_output.err == ""
    assert second_output.err == ""
    assert first_output.out == second_output.out
    parsed = json.loads(first_output.out)
    assert parsed["status"] == "REJECTED"
    assert parsed["admitted"] is False


def make_registry_root(
    tmp_path: Path,
    *,
    repos_yaml: str = "repos: []\n",
    projects_yaml: str = "projects: []\n",
) -> Path:
    root = tmp_path / "root"
    (root / "schemas/registry").mkdir(parents=True)
    (root / "schemas/profile").mkdir(parents=True)
    (root / "profiles").mkdir()
    (root / "registry").mkdir()

    write_text(
        root / "schemas/registry/repo_registry.schema.json",
        (ROOT / "schemas/registry/repo_registry.schema.json").read_text(encoding="utf-8"),
    )
    write_text(
        root / "schemas/registry/project_registry.schema.json",
        (ROOT / "schemas/registry/project_registry.schema.json").read_text(encoding="utf-8"),
    )
    write_text(
        root / "schemas/profile/project_profile.schema.json",
        (ROOT / "schemas/profile/project_profile.schema.json").read_text(encoding="utf-8"),
    )
    write_text(
        root / "profiles/CSL_GOVERNED.yaml",
        (ROOT / "profiles/CSL_GOVERNED.yaml").read_text(encoding="utf-8"),
    )
    write_text(root / "registry/repos.yaml", repos_yaml)
    write_text(root / "registry/projects.yaml", projects_yaml)
    return root


def write_request_file(tmp_path: Path, *, local_path: Path) -> Path:
    request = {
        "project_id": "ora-slice-5-example",
        "repo_name": "ORA-Slice-5-Example",
        "profile_id": "CSL_GOVERNED",
        "description": "Example request for registry admission testing.",
        "target_owner": "Levloc-Dev",
        "local_path": str(local_path.resolve()),
    }
    path = tmp_path / "request.json"
    write_text(path, json.dumps(request, indent=2) + "\n")
    return path


def write_execution_artifact_file(
    tmp_path: Path,
    *,
    target_root: Path,
    dry_run: bool = False,
    project_name: str = "ORA-Slice-5-Example",
    project_profile: str = "CSL_GOVERNED",
    statuses: list[str] | None = None,
) -> Path:
    effective_statuses = list(statuses or ["APPLIED", "APPLIED"])
    artifact = {
        "artifact_version": "1.0.0",
        "plan_version": "1.0.0",
        "project_name": project_name,
        "project_profile": project_profile,
        "target_root": str(target_root.resolve()),
        "dry_run": dry_run,
        "operation_count": len(effective_statuses),
        "operations": [
            {
                "operation_id": f"op-{index}",
                "operation_type": "WRITE_FILE",
                "target_path": f"file-{index}.md",
                "normalized_target_path": f"file-{index}.md",
                "source_template": None,
                "content_strategy": "COPY_CANONICAL_SOURCE",
                "status": status,
                "bytes_written": 0,
                "content_sha256": None,
            }
            for index, status in enumerate(effective_statuses)
        ],
    }
    path = tmp_path / "artifact.json"
    write_text(path, json.dumps(artifact, indent=2) + "\n")
    return path


def load_yaml_as_jsonish(path: Path) -> dict[str, object]:
    return json.loads(json.dumps(load_yaml_subset_file(path)))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
