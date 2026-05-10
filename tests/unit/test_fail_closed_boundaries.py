from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validators.validate_fail_closed_boundaries import (  # noqa: E402
    BRIDGE_SCOPE_FILES,
    REQUIRED_TEXT,
    VALIDATOR_ORCHESTRATION_FILES,
    validate_fail_closed_boundaries,
)


def test_validate_fail_closed_boundaries_accepts_current_queue_admission_scope(
    tmp_path: Path,
) -> None:
    root = make_validator_root(tmp_path)
    write_text(
        root / "src/ora/queue/queue_manager.py",
        "from pathlib import Path\n"
        "PROJECT_QUEUE_PATH = Path('queue/project_queue.yaml')\n"
        "QUEUE_DOCUMENT = PROJECT_QUEUE_PATH\n"
        "\n"
        "def register_queue_item() -> None:\n"
        "    QUEUE_DOCUMENT.write_text('queue_items: []\\n', encoding='utf-8')\n",
    )
    write_text(
        root / "tools/ora_update_queue.py",
        "import argparse\n"
        "\n"
        "def build_parser() -> argparse.ArgumentParser:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    parser.add_subparsers(dest='command', required=True).add_parser('admit')\n"
        "    return parser\n",
    )

    result = validate_fail_closed_boundaries(
        root,
        bridge_scope_files=[],
        validator_orchestration_files=[],
    )

    assert result.ok
    assert result.errors == []


def test_validate_fail_closed_boundaries_rejects_forbidden_state_transition_symbols(
    tmp_path: Path,
) -> None:
    root = make_validator_root(tmp_path)
    write_text(
        root / "src/ora/queue/queue_manager.py",
        "def register_queue_item() -> None:\n"
        "    update_queue_item_state('repo-1')\n",
    )
    write_text(
        root / "tools/ora_update_queue.py",
        "import argparse\n"
        "\n"
        "def build_parser() -> argparse.ArgumentParser:\n"
        "    parser = argparse.ArgumentParser()\n"
        "    parser.add_subparsers(dest='command', required=True).add_parser('update-state')\n"
        "    return parser\n",
    )

    result = validate_fail_closed_boundaries(
        root,
        bridge_scope_files=[],
        validator_orchestration_files=[],
    )

    assert not result.ok
    assert "update_queue_item_state" in result.errors[0] or "update_queue_item_state" in result.errors[1]
    assert any("update-state" in error for error in result.errors)


def test_validate_fail_closed_boundaries_rejects_forbidden_registry_and_queue_writes(
    tmp_path: Path,
) -> None:
    root = make_validator_root(tmp_path)
    write_text(
        root / "src/ora/queue/queue_manager.py",
        "from pathlib import Path\n"
        "REPOS_PATH = Path('registry/repos.yaml')\n"
        "BLOCKERS_PATH = Path('queue/blockers.yaml')\n"
        "ESCALATIONS_PATH = Path('queue/escalations.yaml')\n"
        "\n"
        "def register_queue_item() -> None:\n"
        "    REPOS_PATH.write_text('repos: []\\n', encoding='utf-8')\n"
        "    open(BLOCKERS_PATH, 'w', encoding='utf-8').write('blockers: []\\n')\n"
        "    open(ESCALATIONS_PATH, mode='a', encoding='utf-8').write('escalations: []\\n')\n",
    )
    write_text(
        root / "tools/ora_update_queue.py",
        "def noop() -> None:\n"
        "    return None\n",
    )

    result = validate_fail_closed_boundaries(
        root,
        bridge_scope_files=[],
        validator_orchestration_files=[],
    )

    assert not result.ok
    assert any("registry/repos.yaml" in error for error in result.errors)
    assert any("queue/blockers.yaml" in error for error in result.errors)
    assert any("queue/escalations.yaml" in error for error in result.errors)


def test_validate_fail_closed_boundaries_rejects_registry_field_mutation_markers(
    tmp_path: Path,
) -> None:
    root = make_validator_root(tmp_path)
    write_text(
        root / "src/ora/queue/queue_manager.py",
        "def register_queue_item() -> dict[str, str | None]:\n"
        "    return {\n"
        "        'current_queue_item': 'repo-1',\n"
        "        'last_known_status': 'READY_FOR_FIRST_GOVERNED_SLICE',\n"
        "    }\n",
    )
    write_text(
        root / "tools/ora_update_queue.py",
        "def noop() -> None:\n"
        "    return None\n",
    )

    result = validate_fail_closed_boundaries(
        root,
        bridge_scope_files=[],
        validator_orchestration_files=[],
    )

    assert not result.ok
    assert any("current_queue_item" in error for error in result.errors)
    assert any("last_known_status" in error for error in result.errors)


def test_validate_fail_closed_boundaries_accepts_current_bridge_scope(
    tmp_path: Path,
) -> None:
    root = make_validator_root(tmp_path)
    write_safe_bridge_scope_files(root)

    result = validate_fail_closed_boundaries(
        root,
        queue_admission_files=[],
        validator_orchestration_files=[],
    )

    assert result.ok
    assert result.errors == []


def test_validate_fail_closed_boundaries_rejects_forbidden_bridge_imports_and_calls(
    tmp_path: Path,
) -> None:
    root = make_validator_root(tmp_path)
    write_safe_bridge_scope_files(root)
    write_text(
        root / "src/ora/bridges/_governed_handoff.py",
        "import os\n"
        "import requests\n"
        "from urllib import request\n"
        "import socket\n"
        "import subprocess\n"
        "\n"
        "def build_handoff_packet() -> None:\n"
        "    os.system('echo nope')\n"
        "    requests.get('https://example.invalid')\n"
        "    request.urlopen('https://example.invalid')\n"
        "    socket.socket()\n"
        "    subprocess.run(['echo', 'nope'])\n",
    )

    result = validate_fail_closed_boundaries(
        root,
        queue_admission_files=[],
        validator_orchestration_files=[],
    )

    assert not result.ok
    assert any("must not import requests" in error for error in result.errors)
    assert any("must not import urllib" in error for error in result.errors)
    assert any("must not import socket" in error for error in result.errors)
    assert any("must not import subprocess" in error for error in result.errors)
    assert any("must not call os.system" in error for error in result.errors)
    assert any("must not perform requests calls" in error for error in result.errors)
    assert any("must not perform urllib calls" in error for error in result.errors)
    assert any("must not perform socket calls" in error for error in result.errors)
    assert any("must not perform subprocess calls" in error for error in result.errors)


def test_validate_fail_closed_boundaries_rejects_forbidden_bridge_git_dispatch_and_writes(
    tmp_path: Path,
) -> None:
    root = make_validator_root(tmp_path)
    write_safe_bridge_scope_files(root)
    write_text(
        root / "tools/ora_generate_handoff_packet.py",
        "from pathlib import Path\n"
        "\n"
        "COMMAND = 'git push origin main'\n"
        "COMMIT = 'git commit -m guard'\n"
        "REPO = 'gh repo create'\n"
        "QUEUE_PATH = Path('queue/project_queue.yaml')\n"
        "PROJECTS_PATH = Path('registry/projects.yaml')\n"
        "README_PATH = Path('README.md')\n"
        "\n"
        "def dispatch_packet() -> None:\n"
        "    return None\n"
        "\n"
        "def send_packet() -> None:\n"
        "    QUEUE_PATH.write_text('queue_items: []\\n', encoding='utf-8')\n"
        "    PROJECTS_PATH.write_text('projects: []\\n', encoding='utf-8')\n"
        "    README_PATH.write_text('mutated\\n', encoding='utf-8')\n",
    )

    result = validate_fail_closed_boundaries(
        root,
        queue_admission_files=[],
        validator_orchestration_files=[],
    )

    assert not result.ok
    assert any("git push" in error for error in result.errors)
    assert any("git commit" in error for error in result.errors)
    assert any("gh repo" in error for error in result.errors)
    assert any("dispatch markers" in error for error in result.errors)
    assert any("send markers" in error for error in result.errors)
    assert any("must not write queue/project_queue.yaml" in error for error in result.errors)
    assert any("must not write registry/projects.yaml" in error for error in result.errors)
    assert any("must not perform file writes (README.md)" in error for error in result.errors)


def test_validate_fail_closed_boundaries_accepts_current_validator_orchestration_scope(
    tmp_path: Path,
) -> None:
    root = make_validator_root(tmp_path)
    write_safe_validator_orchestration_files(root)

    result = validate_fail_closed_boundaries(
        root,
        queue_admission_files=[],
        bridge_scope_files=[],
    )

    assert result.ok
    assert result.errors == []


def test_validate_fail_closed_boundaries_rejects_validator_execution_patterns(
    tmp_path: Path,
) -> None:
    root = make_validator_root(tmp_path)
    write_safe_validator_orchestration_files(root)
    write_text(
        root / "src/ora/validation/validator_orchestrator.py",
        "import os\n"
        "import socket\n"
        "import subprocess\n"
        "from requests import get\n"
        "from urllib import request\n"
        "from pathlib import Path\n"
        "\n"
        "QUEUE_PATH = Path('queue/project_queue.yaml')\n"
        "PROJECTS_PATH = Path('registry/projects.yaml')\n"
        "REPOS_PATH = Path('registry/repos.yaml')\n"
        "README_PATH = Path('README.md')\n"
        "GIT_PUSH = 'git push origin main'\n"
        "\n"
        "def build_validator_plan() -> None:\n"
        "    os.system('echo nope')\n"
        "    subprocess.run(['echo', 'nope'])\n"
        "    subprocess.Popen(['echo', 'nope'])\n"
        "    subprocess.check_call(['echo', 'nope'])\n"
        "    subprocess.check_output(['echo', 'nope'])\n"
        "    run(['echo', 'nope'])\n"
        "    exec('print(1)')\n"
        "    eval('1 + 1')\n"
        "    get('https://example.invalid')\n"
        "    request.urlopen('https://example.invalid')\n"
        "    socket.create_connection(('example.invalid', 443))\n"
        "    QUEUE_PATH.write_text('queue_items: []\\n', encoding='utf-8')\n"
        "    PROJECTS_PATH.write_text('projects: []\\n', encoding='utf-8')\n"
        "    REPOS_PATH.write_text('repos: []\\n', encoding='utf-8')\n"
        "    README_PATH.write_text('mutated\\n', encoding='utf-8')\n",
    )
    write_text(
        root / "tools/ora_run_validators.py",
        "import http.client\n"
        "from pathlib import Path\n"
        "\n"
        "QUEUE_PATH = Path('queue/project_queue.yaml')\n"
        "GIT_COMMIT = 'git commit -m guard'\n"
        "\n"
        "def main() -> int:\n"
        "    http.client.HTTPSConnection('example.invalid')\n"
        "    open(QUEUE_PATH, 'w', encoding='utf-8').write('queue_items: []\\n')\n"
        "    return 0\n",
    )

    result = validate_fail_closed_boundaries(
        root,
        queue_admission_files=[],
        bridge_scope_files=[],
    )

    assert not result.ok
    assert any("must not import subprocess" in error for error in result.errors)
    assert any("must not import network modules" in error for error in result.errors)
    assert any("must not call os.system" in error for error in result.errors)
    assert any("must not call Popen" in error for error in result.errors)
    assert any("must not call check_call" in error for error in result.errors)
    assert any("must not call check_output" in error for error in result.errors)
    assert any("must not call run" in error for error in result.errors)
    assert any("must not call exec" in error for error in result.errors)
    assert any("must not call eval" in error for error in result.errors)
    assert any("must not perform network calls" in error for error in result.errors)
    assert any("git command markers" in error for error in result.errors)
    assert any("must not write queue/project_queue.yaml" in error for error in result.errors)
    assert any("must not write registry/projects.yaml" in error for error in result.errors)
    assert any("must not write registry/repos.yaml" in error for error in result.errors)
    assert any("must not perform repo writes (README.md)" in error for error in result.errors)


def make_validator_root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    for relative_path, marker in REQUIRED_TEXT.items():
        write_text(root / relative_path, f"{marker}\n")
    write_text(root / "src/ora/queue/__init__.py", "")
    write_text(root / "src/ora/bridges/__init__.py", "")
    write_text(root / "tools/__init__.py", "")
    return root


def write_safe_bridge_scope_files(root: Path) -> None:
    bridge_text = (
        "from pathlib import Path\n"
        "\n"
        "ROOT = Path('.')\n"
        "\n"
        "def build_handoff_packet() -> dict[str, object]:\n"
        "    return {\n"
        "        'execution_mode': 'packet_only',\n"
        "        'prompt_dispatch_allowed': False,\n"
        "    }\n"
    )
    for relative_path in BRIDGE_SCOPE_FILES:
        write_text(root / relative_path, bridge_text)


def write_safe_validator_orchestration_files(root: Path) -> None:
    orchestration_text = (
        "from pathlib import Path\n"
        "\n"
        "ROOT = Path('.')\n"
        "\n"
        "def build_validator_plan() -> dict[str, object]:\n"
        "    return {\n"
        "        'execution_mode': 'PLAN_ONLY',\n"
        "        'validator_execution_allowed': False,\n"
        "    }\n"
    )
    for relative_path in VALIDATOR_ORCHESTRATION_FILES:
        write_text(root / relative_path, orchestration_text)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
