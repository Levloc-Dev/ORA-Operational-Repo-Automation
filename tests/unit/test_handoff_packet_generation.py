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

from ora.bridges._governed_handoff import (  # noqa: E402
    HandoffPacketError,
    render_handoff_packet_json,
)
from ora.bridges.chatgpt import build_chatgpt_handoff_packet  # noqa: E402
from ora.bridges.claude import build_claude_handoff_packet  # noqa: E402
from ora.bridges.codex import build_codex_handoff_packet  # noqa: E402
from tools.ora_generate_handoff_packet import main  # noqa: E402
from tools.validate_handoff_packets import validate_handoff_packets  # noqa: E402


def test_build_codex_handoff_packet_is_schema_valid(tmp_path: Path) -> None:
    root = make_handoff_root(tmp_path)

    packet = build_codex_handoff_packet("repo-1", root=root)
    artifact_path = root / "codex_packet.json"
    artifact_path.write_text(render_handoff_packet_json(packet), encoding="utf-8")

    validation_result = validate_handoff_packets(root, [artifact_path])

    assert packet["bridge_type"] == "CODEX"
    assert packet["requested_action"] == "PREPARE_GOVERNED_CODEX_HANDOFF"
    assert packet["repo_id"] == "repo-1"
    assert packet["profile_id"] == "CSL_GOVERNED"
    assert validation_result.ok


def test_build_claude_handoff_packet_is_schema_valid(tmp_path: Path) -> None:
    root = make_handoff_root(tmp_path)

    packet = build_claude_handoff_packet("repo-1", root=root)
    artifact_path = root / "claude_packet.json"
    artifact_path.write_text(render_handoff_packet_json(packet), encoding="utf-8")

    validation_result = validate_handoff_packets(root, [artifact_path])

    assert packet["bridge_type"] == "CLAUDE"
    assert packet["requested_action"] == "PREPARE_GOVERNED_CLAUDE_HANDOFF"
    assert validation_result.ok


def test_build_chatgpt_handoff_packet_is_schema_valid(tmp_path: Path) -> None:
    root = make_handoff_root(tmp_path)

    packet = build_chatgpt_handoff_packet("repo-1", root=root)
    artifact_path = root / "chatgpt_packet.json"
    artifact_path.write_text(render_handoff_packet_json(packet), encoding="utf-8")

    validation_result = validate_handoff_packets(root, [artifact_path])

    assert packet["bridge_type"] == "CHATGPT"
    assert packet["requested_action"] == "PREPARE_GOVERNED_CHATGPT_HANDOFF"
    assert validation_result.ok


def test_build_handoff_packet_rejects_unknown_project(tmp_path: Path) -> None:
    root = make_handoff_root(tmp_path, projects_yaml="projects: []\n")

    with pytest.raises(HandoffPacketError, match="unknown project_id 'repo-1'"):
        build_codex_handoff_packet("repo-1", root=root)


def test_build_handoff_packet_rejects_project_not_in_queue(tmp_path: Path) -> None:
    root = make_handoff_root(tmp_path, queue_yaml="queue_items: []\n")

    with pytest.raises(
        HandoffPacketError,
        match="project_id 'repo-1' is not present in queue/project_queue.yaml",
    ):
        build_codex_handoff_packet("repo-1", root=root)


def test_ora_generate_handoff_packet_rejects_unsupported_bridge(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_handoff_root(tmp_path)

    exit_code = main(
        [
            "--project-id",
            "repo-1",
            "--bridge-type",
            "GEMINI",
        ],
        root=root,
    )
    output = capsys.readouterr()

    assert exit_code == 1
    assert output.err == ""
    assert json.loads(output.out) == {
        "bridge_type": "GEMINI",
        "error": "unsupported bridge_type 'GEMINI'",
        "generated": False,
        "project_id": "repo-1",
    }


def test_ora_generate_handoff_packet_output_is_byte_identical(
    tmp_path: Path,
    capsys,
) -> None:
    root = make_handoff_root(tmp_path)

    first_exit_code = main(
        [
            "--project-id",
            "repo-1",
            "--bridge-type",
            "CODEX",
        ],
        root=root,
    )
    first_output = capsys.readouterr()

    second_exit_code = main(
        [
            "--project-id",
            "repo-1",
            "--bridge-type",
            "CODEX",
        ],
        root=root,
    )
    second_output = capsys.readouterr()

    assert first_exit_code == 0
    assert second_exit_code == 0
    assert first_output.err == ""
    assert second_output.err == ""
    assert first_output.out == second_output.out


def make_handoff_root(
    tmp_path: Path,
    *,
    projects_yaml: str | None = None,
    repos_yaml: str | None = None,
    queue_yaml: str | None = None,
) -> Path:
    root = tmp_path / "root"
    (root / "registry").mkdir(parents=True)
    (root / "queue").mkdir()
    (root / "schemas/bridge").mkdir(parents=True)

    _write_text(
        root / "schemas/bridge/handoff_packet.schema.json",
        (ROOT / "schemas/bridge/handoff_packet.schema.json").read_text(encoding="utf-8"),
    )
    _write_text(
        root / "registry/projects.yaml",
        projects_yaml
        or (
            "projects:\n"
            "  - project_id: repo-1\n"
        ),
    )
    _write_text(
        root / "registry/repos.yaml",
        repos_yaml
        or (
            "repos:\n"
            "  - repo_id: repo-1\n"
            "    repo_name: repo-1\n"
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
    _write_text(
        root / "queue/project_queue.yaml",
        queue_yaml
        or (
            "queue_items:\n"
            "  - project_id: repo-1\n"
            "    repo_id: repo-1\n"
            "    profile_id: CSL_GOVERNED\n"
            "    status: READY_FOR_FIRST_GOVERNED_SLICE\n"
            "    current_slice: null\n"
            "    blocker: null\n"
            "    escalation_required: true\n"
        ),
    )
    return root


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
