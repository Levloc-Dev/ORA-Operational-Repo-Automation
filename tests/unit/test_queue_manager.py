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

from ora.queue.queue_manager import (  # noqa: E402
    QueueManagerError,
    register_queue_item,
    update_queue_item_state,
)
from ora.validation.schema_subset import load_yaml_subset_file  # noqa: E402
from tools.ora_update_queue import main  # noqa: E402
from tools.validate_queue import validate_queue  # noqa: E402
from tools.validate_registry import validate_registry  # noqa: E402


def test_register_queue_item_updates_queue_and_registry(tmp_path: Path) -> None:
    root = make_queue_root(tmp_path)

    result = register_queue_item(
        repo_id="repo-1",
        queue_item_id="q-1",
        state="READY_FOR_SLICE",
        next_action="implement-slice-6",
        root=root,
    )

    assert result == {
        "status": "REGISTERED",
        "queue_item_id": "q-1",
        "repo_id": "repo-1",
        "state": "READY_FOR_SLICE",
        "next_action": "implement-slice-6",
        "updated_files": [
            "queue/project_queue.yaml",
            "queue/blockers.yaml",
            "queue/escalations.yaml",
            "registry/repos.yaml",
        ],
    }
    assert load_yaml_as_jsonish(root / "queue/project_queue.yaml") == {
        "queue_items": [
            {
                "queue_item_id": "q-1",
                "repo_id": "repo-1",
                "state": "READY_FOR_SLICE",
                "next_action": "implement-slice-6",
            }
        ]
    }
    assert load_yaml_as_jsonish(root / "registry/repos.yaml")["repos"][0][
        "current_queue_item"
    ] == "q-1"
    assert load_yaml_as_jsonish(root / "registry/repos.yaml")["repos"][0][
        "last_known_status"
    ] == "READY_FOR_SLICE"
    assert validate_queue(root).ok
    assert validate_registry(root).ok


def test_update_queue_item_state_opens_and_closes_blockers_and_escalations(
    tmp_path: Path,
) -> None:
    root = make_queue_root(tmp_path)
    register_queue_item(
        repo_id="repo-1",
        queue_item_id="q-1",
        state="READY_FOR_SLICE",
        next_action="implement-slice-6",
        root=root,
    )

    blocked = update_queue_item_state(
        "q-1",
        "BLOCKED",
        "await-human-input",
        root=root,
        reason="missing requirement clarification",
    )
    escalated = update_queue_item_state(
        "q-1",
        "ESCALATION_REQUIRED",
        "request-approval",
        root=root,
        reason="needs operator decision",
    )
    complete = update_queue_item_state(
        "q-1",
        "COMPLETE",
        "archive-when-needed",
        root=root,
    )

    assert blocked["previous_state"] == "READY_FOR_SLICE"
    assert escalated["previous_state"] == "BLOCKED"
    assert complete["previous_state"] == "ESCALATION_REQUIRED"

    blockers = load_yaml_as_jsonish(root / "queue/blockers.yaml")
    escalations = load_yaml_as_jsonish(root / "queue/escalations.yaml")
    repos = load_yaml_as_jsonish(root / "registry/repos.yaml")

    assert blockers == {
        "blockers": [
            {
                "blocker_id": "blk-q-1",
                "queue_item_id": "q-1",
                "reason": "missing requirement clarification",
                "status": "CLOSED",
            }
        ]
    }
    assert escalations == {
        "escalations": [
            {
                "escalation_id": "esc-q-1",
                "queue_item_id": "q-1",
                "reason": "needs operator decision",
                "status": "CLOSED",
            }
        ]
    }
    assert repos["repos"][0]["current_queue_item"] is None
    assert repos["repos"][0]["last_known_status"] == "COMPLETE"
    assert validate_queue(root).ok
    assert validate_registry(root).ok


def test_register_queue_item_rejects_duplicate_active_repo(tmp_path: Path) -> None:
    root = make_queue_root(tmp_path)
    register_queue_item(
        repo_id="repo-1",
        queue_item_id="q-1",
        state="READY_FOR_SLICE",
        next_action="implement-first-slice",
        root=root,
    )

    try:
        register_queue_item(
            repo_id="repo-1",
            queue_item_id="q-2",
            state="READY_FOR_COMMIT",
            next_action="commit-first-slice",
            root=root,
        )
    except QueueManagerError as exc:
        assert str(exc) == "repo_id 'repo-1' already has active queue item 'q-1'"
    else:
        raise AssertionError("expected duplicate active repo registration to fail")


def test_update_queue_item_state_requires_reason_for_blocked_states(
    tmp_path: Path,
) -> None:
    root = make_queue_root(tmp_path)
    register_queue_item(
        repo_id="repo-1",
        queue_item_id="q-1",
        state="READY_FOR_SLICE",
        next_action="implement-slice-6",
        root=root,
    )

    try:
        update_queue_item_state(
            "q-1",
            "BLOCKED",
            "await-human-input",
            root=root,
        )
    except QueueManagerError as exc:
        assert str(exc) == "reason is required when updating state to BLOCKED"
    else:
        raise AssertionError("expected blocked transition without reason to fail")


def test_ora_update_queue_cli_is_deterministic_on_rejection(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_queue_root(tmp_path)

    first_exit_code = main(
        [
            "update-state",
            "--queue-item-id",
            "missing-q",
            "--state",
            "READY_FOR_SYNC",
            "--next-action",
            "sync-dev-main",
        ],
        root=root,
    )
    first_output = capsys.readouterr()

    second_exit_code = main(
        [
            "update-state",
            "--queue-item-id",
            "missing-q",
            "--state",
            "READY_FOR_SYNC",
            "--next-action",
            "sync-dev-main",
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
        "error": "unknown queue_item_id 'missing-q'",
        "status": "REJECTED",
    }


def make_queue_root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    (root / "queue").mkdir(parents=True)
    (root / "registry").mkdir()
    (root / "schemas/queue").mkdir(parents=True)
    (root / "schemas/registry").mkdir(parents=True)

    write_text(
        root / "schemas/queue/queue_item.schema.json",
        (ROOT / "schemas/queue/queue_item.schema.json").read_text(encoding="utf-8"),
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
        (
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
    write_text(root / "registry/projects.yaml", "projects:\n  - project_id: repo-1\n")
    return root


def load_yaml_as_jsonish(path: Path) -> dict[str, object]:
    return json.loads(json.dumps(load_yaml_subset_file(path)))


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
