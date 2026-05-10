from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validators.validate_fail_closed_boundaries import (  # noqa: E402
    REQUIRED_TEXT,
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

    result = validate_fail_closed_boundaries(root)

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

    result = validate_fail_closed_boundaries(root)

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

    result = validate_fail_closed_boundaries(root)

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

    result = validate_fail_closed_boundaries(root)

    assert not result.ok
    assert any("current_queue_item" in error for error in result.errors)
    assert any("last_known_status" in error for error in result.errors)


def make_validator_root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    for relative_path, marker in REQUIRED_TEXT.items():
        write_text(root / relative_path, f"{marker}\n")
    write_text(root / "src/ora/queue/__init__.py", "")
    write_text(root / "tools/__init__.py", "")
    return root


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
