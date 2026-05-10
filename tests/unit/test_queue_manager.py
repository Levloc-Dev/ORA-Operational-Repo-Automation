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

from ora.queue.queue_manager import (  # noqa: E402
    QueueManagerError,
    register_queue_item,
)
from ora.validation.schema_subset import load_yaml_subset_file  # noqa: E402
from tools.ora_update_queue import main  # noqa: E402
from tools.validate_queue import validate_queue  # noqa: E402
from tools.validate_registry import validate_registry  # noqa: E402


def test_register_queue_item_admits_known_project_and_repo(
    tmp_path: Path,
) -> None:
    root = make_queue_root(tmp_path)
    original_repos = (root / "registry/repos.yaml").read_text(encoding="utf-8")
    original_projects = (root / "registry/projects.yaml").read_text(encoding="utf-8")

    result = register_queue_item(
        project_id="repo-1",
        profile_id="CSL_GOVERNED",
        root=root,
    )

    assert result == {
        "admitted": True,
        "profile_id": "CSL_GOVERNED",
        "project_id": "repo-1",
        "queue_item": {
            "project_id": "repo-1",
            "repo_id": "repo-1",
            "profile_id": "CSL_GOVERNED",
            "status": "READY_FOR_FIRST_GOVERNED_SLICE",
            "current_slice": None,
            "blocker": None,
            "escalation_required": "true",
        },
        "repo_id": "repo-1",
        "updated_files": ["queue/project_queue.yaml"],
    }
    assert load_yaml_as_jsonish(root / "queue/project_queue.yaml") == {
        "queue_items": [result["queue_item"]]
    }
    assert "escalation_required: true\n" in (
        root / "queue/project_queue.yaml"
    ).read_text(encoding="utf-8")
    assert (root / "registry/repos.yaml").read_text(encoding="utf-8") == original_repos
    assert (root / "registry/projects.yaml").read_text(encoding="utf-8") == original_projects
    assert validate_queue(root).ok
    assert validate_registry(root).ok


def test_register_queue_item_rejects_duplicate_project_id_in_queue(
    tmp_path: Path,
) -> None:
    root = make_queue_root(tmp_path)
    register_queue_item(
        project_id="repo-1",
        profile_id="CSL_GOVERNED",
        root=root,
    )

    with pytest.raises(QueueManagerError, match="duplicate project_id 'repo-1'"):
        register_queue_item(
            project_id="repo-1",
            profile_id="CSL_GOVERNED",
            root=root,
        )


def test_register_queue_item_rejects_unknown_project(tmp_path: Path) -> None:
    root = make_queue_root(tmp_path, projects_yaml="projects: []\n")

    with pytest.raises(QueueManagerError, match="unknown project_id 'repo-1'"):
        register_queue_item(
            project_id="repo-1",
            profile_id="CSL_GOVERNED",
            root=root,
        )


def test_register_queue_item_rejects_unknown_repo(tmp_path: Path) -> None:
    root = make_queue_root(tmp_path, repos_yaml="repos: []\n")

    with pytest.raises(QueueManagerError, match="unknown repo_id 'repo-1'"):
        register_queue_item(
            project_id="repo-1",
            profile_id="CSL_GOVERNED",
            root=root,
        )


def test_register_queue_item_rejects_malformed_queue_file(tmp_path: Path) -> None:
    root = make_queue_root(tmp_path)
    write_text(root / "queue/project_queue.yaml", "queue_items:\n\t- invalid\n")

    with pytest.raises(QueueManagerError, match="queue/project_queue.yaml:"):
        register_queue_item(
            project_id="repo-1",
            profile_id="CSL_GOVERNED",
            root=root,
        )


def test_ora_update_queue_cli_is_deterministic_on_rejection(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_queue_root(tmp_path, projects_yaml="projects: []\n")

    first_exit_code = main(
        [
            "admit",
            "--project-id",
            "repo-1",
            "--profile-id",
            "CSL_GOVERNED",
        ],
        root=root,
    )
    first_output = capsys.readouterr()

    second_exit_code = main(
        [
            "admit",
            "--project-id",
            "repo-1",
            "--profile-id",
            "CSL_GOVERNED",
        ],
        root=root,
    )
    second_output = capsys.readouterr()

    assert first_exit_code == 1
    assert second_exit_code == 1
    assert first_output.err == ""
    assert second_output.err == ""
    assert first_output.out == second_output.out
    assert json.loads(first_output.out) == {
        "admitted": False,
        "error": "unknown project_id 'repo-1'",
        "profile_id": "CSL_GOVERNED",
        "project_id": "repo-1",
        "repo_id": "repo-1",
    }


def make_queue_root(
    tmp_path: Path,
    *,
    repos_yaml: str | None = None,
    projects_yaml: str | None = None,
) -> Path:
    root = tmp_path / "root"
    (root / "queue").mkdir(parents=True)
    (root / "registry").mkdir()
    (root / "schemas/queue").mkdir(parents=True)
    (root / "schemas/registry").mkdir(parents=True)

    write_text(
        root / "schemas/queue/queue_item.schema.json",
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "ora://schemas/queue/queue_item.schema.json",
                "title": "ORA Queue Item",
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
            indent=2,
        )
        + "\n",
    )
    write_text(
        root / "schemas/registry/repo_registry.schema.json",
        (ROOT / "schemas/registry/repo_registry.schema.json").read_text(
            encoding="utf-8"
        ),
    )
    write_text(
        root / "schemas/registry/project_registry.schema.json",
        (ROOT / "schemas/registry/project_registry.schema.json").read_text(
            encoding="utf-8"
        ),
    )
    write_text(root / "queue/project_queue.yaml", "queue_items: []\n")
    write_text(root / "queue/blockers.yaml", "blockers: []\n")
    write_text(root / "queue/escalations.yaml", "escalations: []\n")
    write_text(
        root / "registry/repos.yaml",
        repos_yaml
        or (
            "repos:\n"
            "  - repo_id: repo-1\n"
            "    repo_name: Repo-One\n"
            "    project_profile: CSL_GOVERNED\n"
            "    local_path: /tmp/repo-1\n"
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
    )
    write_text(
        root / "registry/projects.yaml",
        projects_yaml or "projects:\n  - project_id: repo-1\n",
    )
    return root


def load_yaml_as_jsonish(path: Path) -> dict[str, object]:
    return json.loads(json.dumps(load_yaml_subset_file(path)))


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
