#!/usr/bin/env python3
"""Static fail-closed boundary validator."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import NamedTuple


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_TEXT = {
    "README.md": "Excluded from repo birth:",
    "governance/policies/ORA_CAPABILITY_BOUNDARY.md": "Not allowed in Slice 1:",
    "governance/policies/ORA_FAIL_CLOSED_POLICY.md": "must stop without continuation",
    "src/ora/operations/runner.py": "not implemented in Slice 1",
}
FORBIDDEN_PATHS = ["runtime"]
QUEUE_ADMISSION_FILES = [
    "src/ora/queue/queue_manager.py",
    "tools/ora_update_queue.py",
]
FORBIDDEN_SUBSTRINGS = {
    "update_queue_item_state": "queue admission must not call state transition helpers",
    "update-state": "queue admission must not expose an update-state CLI command",
    "current_queue_item": "queue admission must not mutate registry queue tracking fields",
    "last_known_status": "queue admission must not mutate registry status fields",
}
FORBIDDEN_WRITE_PATHS = {
    "registry/repos.yaml": "queue admission must not write registry/repos.yaml",
    "queue/blockers.yaml": "queue admission must not write queue/blockers.yaml",
    "queue/escalations.yaml": "queue admission must not write queue/escalations.yaml",
}
WRITE_MODES = {"w", "a", "x", "w+", "a+", "x+", "r+", "+", "wb", "ab", "xb"}


class ValidationResult(NamedTuple):
    ok: bool
    errors: list[str]


class QueueAdmissionWriteVisitor(ast.NodeVisitor):
    """Collect static write-like operations against forbidden queue-adjacent files."""

    def __init__(self) -> None:
        self.path_bindings: dict[str, str] = {}
        self.errors: list[str] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        resolved = _resolve_path_expression(node.value, self.path_bindings)
        if resolved is not None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self.path_bindings[target.id] = resolved
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None and isinstance(node.target, ast.Name):
            resolved = _resolve_path_expression(node.value, self.path_bindings)
            if resolved is not None:
                self.path_bindings[node.target.id] = resolved
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        forbidden_write = self._resolve_forbidden_write(node)
        if forbidden_write is not None:
            self.errors.append(
                f"line {node.lineno}: queue admission must not write {forbidden_write}"
            )
        self.generic_visit(node)

    def _resolve_forbidden_write(self, node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Attribute) and node.func.attr == "write_text":
            path_text = _resolve_path_expression(node.func.value, self.path_bindings)
            return _match_forbidden_write_path(path_text)

        if isinstance(node.func, ast.Name) and node.func.id == "open" and node.args:
            mode = _resolve_open_mode(node)
            if mode is None or not _mode_writes(mode):
                return None
            path_text = _resolve_path_expression(node.args[0], self.path_bindings)
            return _match_forbidden_write_path(path_text)

        return None


def validate_fail_closed_boundaries(
    root: Path = ROOT,
    *,
    queue_admission_files: list[str] | None = None,
) -> ValidationResult:
    errors: list[str] = []

    for relative_path, marker in REQUIRED_TEXT.items():
        path = root / relative_path
        if not path.exists():
            errors.append(f"missing file: {relative_path}")
            continue
        if marker not in path.read_text(encoding="utf-8"):
            errors.append(f"{relative_path} missing marker {marker}")

    for relative_path in FORBIDDEN_PATHS:
        if (root / relative_path).exists():
            errors.append(f"forbidden path present: {relative_path}")

    for relative_path in queue_admission_files or QUEUE_ADMISSION_FILES:
        path = root / relative_path
        if not path.exists():
            errors.append(f"missing queue admission file: {relative_path}")
            continue
        errors.extend(_validate_queue_admission_file(path, relative_path))

    return ValidationResult(ok=not errors, errors=errors)


def _validate_queue_admission_file(path: Path, relative_path: str) -> list[str]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []

    for forbidden_text, message in FORBIDDEN_SUBSTRINGS.items():
        if forbidden_text in text:
            errors.append(f"{relative_path}: {message} ({forbidden_text})")

    try:
        tree = ast.parse(text, filename=relative_path)
    except SyntaxError as exc:
        return [f"{relative_path}: syntax error during static scan: {exc.msg}"]

    visitor = QueueAdmissionWriteVisitor()
    visitor.visit(tree)
    errors.extend(f"{relative_path}: {error}" for error in visitor.errors)
    return errors


def _resolve_path_expression(
    node: ast.AST,
    bindings: dict[str, str],
) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value

    if isinstance(node, ast.Name):
        return bindings.get(node.id)

    if isinstance(node, ast.Call):
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "Path"
            and len(node.args) == 1
        ):
            return _resolve_path_expression(node.args[0], bindings)

    return None


def _resolve_open_mode(node: ast.Call) -> str | None:
    if len(node.args) >= 2:
        mode = node.args[1]
        if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
            return mode.value

    for keyword in node.keywords:
        if keyword.arg == "mode":
            if isinstance(keyword.value, ast.Constant) and isinstance(
                keyword.value.value, str
            ):
                return keyword.value.value

    return "r"


def _mode_writes(mode: str) -> bool:
    return mode in WRITE_MODES or any(flag in mode for flag in ("w", "a", "x", "+"))


def _match_forbidden_write_path(path_text: str | None) -> str | None:
    if path_text is None:
        return None

    normalized = path_text.replace("\\", "/")
    for forbidden_path in FORBIDDEN_WRITE_PATHS:
        if normalized.endswith(forbidden_path):
            return forbidden_path
    return None


def main() -> int:
    result = validate_fail_closed_boundaries()
    if not result.ok:
        for error in result.errors:
            print(error, file=sys.stderr)
        return 1

    print("fail-closed boundary validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
