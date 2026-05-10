#!/usr/bin/env python3
"""Static fail-closed boundary validator."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from typing import NamedTuple


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_TEXT = {
    "README.md": "Current fail-closed boundary:",
    "governance/policies/ORA_CAPABILITY_BOUNDARY.md": "Not allowed in Slice 1:",
    "governance/policies/ORA_FAIL_CLOSED_POLICY.md": "must stop without continuation",
    "src/ora/operations/runner.py": "not implemented in Slice 1",
}
FORBIDDEN_PATHS = ["runtime"]
QUEUE_ADMISSION_FILES = [
    "src/ora/queue/queue_manager.py",
    "tools/ora_update_queue.py",
]
BRIDGE_SCOPE_FILES = [
    "src/ora/bridges/_governed_handoff.py",
    "src/ora/bridges/chatgpt.py",
    "src/ora/bridges/codex.py",
    "src/ora/bridges/claude.py",
    "tools/ora_generate_handoff_packet.py",
]
VALIDATOR_ORCHESTRATION_FILES = [
    "src/ora/validation/validator_orchestrator.py",
    "tools/ora_run_validators.py",
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
FORBIDDEN_BRIDGE_COMMAND_MARKERS = {
    "git push": "bridge scope must not perform git push operations",
    "git commit": "bridge scope must not perform git commit operations",
    "gh repo": "bridge scope must not perform GitHub repository operations",
}
FORBIDDEN_BRIDGE_IDENTIFIER_FRAGMENTS = {
    "dispatch": "bridge scope must not include dispatch markers",
    "send": "bridge scope must not include send markers",
}
ALLOWED_BRIDGE_IDENTIFIER_EXACT = {
    "prompt_dispatch_allowed",
}
ALLOWED_BRIDGE_TEXT_EXACT = {
    "prompt_dispatch",
    "prompt_dispatch_allowed",
}
FORBIDDEN_BRIDGE_IMPORTS = {
    "requests": "bridge scope must not import requests",
    "socket": "bridge scope must not import socket",
    "subprocess": "bridge scope must not import subprocess",
    "urllib": "bridge scope must not import urllib",
}
FORBIDDEN_BRIDGE_CALL_PREFIXES = {
    "os.system": "bridge scope must not call os.system",
    "requests": "bridge scope must not perform requests calls",
    "socket": "bridge scope must not perform socket calls",
    "subprocess": "bridge scope must not perform subprocess calls",
    "urllib": "bridge scope must not perform urllib calls",
}
FORBIDDEN_VALIDATOR_COMMAND_MARKERS = {
    "git ": "validator orchestration scope must not include git command markers",
    "git\n": "validator orchestration scope must not include git command markers",
}
FORBIDDEN_VALIDATOR_IMPORTS = {
    "aiohttp": "validator orchestration scope must not import network modules",
    "http": "validator orchestration scope must not import network modules",
    "httpx": "validator orchestration scope must not import network modules",
    "requests": "validator orchestration scope must not import network modules",
    "socket": "validator orchestration scope must not import network modules",
    "subprocess": "validator orchestration scope must not import subprocess",
    "urllib": "validator orchestration scope must not import network modules",
}
FORBIDDEN_VALIDATOR_CALL_PREFIXES = {
    "eval": "validator orchestration scope must not call eval",
    "exec": "validator orchestration scope must not call exec",
    "http.client": "validator orchestration scope must not perform network calls",
    "httpx": "validator orchestration scope must not perform network calls",
    "os.system": "validator orchestration scope must not call os.system",
    "requests": "validator orchestration scope must not perform network calls",
    "socket": "validator orchestration scope must not perform network calls",
    "subprocess": "validator orchestration scope must not perform subprocess calls",
    "urllib": "validator orchestration scope must not perform network calls",
}
FORBIDDEN_VALIDATOR_CALL_NAMES = {
    "Popen": "validator orchestration scope must not call Popen",
    "check_call": "validator orchestration scope must not call check_call",
    "check_output": "validator orchestration scope must not call check_output",
    "run": "validator orchestration scope must not call run",
}


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


class BridgeScopeVisitor(ast.NodeVisitor):
    """Collect static bridge-scope violations for packet-generation files."""

    def __init__(self) -> None:
        self.path_bindings: dict[str, str] = {}
        self.import_aliases: dict[str, str] = {}
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

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            canonical = alias.name
            bound_name = alias.asname or canonical.split(".", 1)[0]
            self.import_aliases[bound_name] = canonical
            self._record_forbidden_import(canonical, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module is None:
            self.generic_visit(node)
            return

        self._record_forbidden_import(node.module, node.lineno)
        for alias in node.names:
            bound_name = alias.asname or alias.name
            self.import_aliases[bound_name] = f"{node.module}.{alias.name}"
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._record_identifier_marker(node.name, node.lineno)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._record_identifier_marker(node.name, node.lineno)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        self._record_identifier_marker(node.id, node.lineno)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        self._record_identifier_marker(node.attr, node.lineno)
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            self._record_command_markers(node.value, node.lineno)
            self._record_text_dispatch_markers(node.value, node.lineno)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        forbidden_write_error = self._resolve_forbidden_write(node)
        if forbidden_write_error is not None:
            self.errors.append(f"line {node.lineno}: {forbidden_write_error}")

        forbidden_call_error = self._resolve_forbidden_call(node)
        if forbidden_call_error is not None:
            self.errors.append(f"line {node.lineno}: {forbidden_call_error}")

        self.generic_visit(node)

    def _record_forbidden_import(self, module_name: str, lineno: int) -> None:
        for forbidden_module, message in FORBIDDEN_BRIDGE_IMPORTS.items():
            if module_name == forbidden_module or module_name.startswith(
                f"{forbidden_module}."
            ):
                self.errors.append(f"line {lineno}: {message}")

    def _record_identifier_marker(self, name: str, lineno: int) -> None:
        normalized_name = name.lower()
        if normalized_name in ALLOWED_BRIDGE_IDENTIFIER_EXACT:
            return
        for fragment, message in FORBIDDEN_BRIDGE_IDENTIFIER_FRAGMENTS.items():
            if fragment in normalized_name:
                self.errors.append(f"line {lineno}: {message} ({name})")

    def _record_command_markers(self, value: str, lineno: int) -> None:
        normalized_value = value.lower()
        for marker, message in FORBIDDEN_BRIDGE_COMMAND_MARKERS.items():
            if marker in normalized_value:
                self.errors.append(f"line {lineno}: {message} ({marker})")

    def _record_text_dispatch_markers(self, value: str, lineno: int) -> None:
        normalized_value = value.lower()
        if normalized_value in ALLOWED_BRIDGE_TEXT_EXACT:
            return
        if "dispatch" in normalized_value:
            self.errors.append(
                f"line {lineno}: bridge scope must not include dispatch markers ({value})"
            )
        if "send" in normalized_value:
            self.errors.append(
                f"line {lineno}: bridge scope must not include send markers ({value})"
            )

    def _resolve_forbidden_write(self, node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            "write",
            "write_bytes",
            "write_text",
        }:
            path_text = _resolve_path_expression(node.func.value, self.path_bindings)
            return _format_bridge_write_error(path_text)

        if isinstance(node.func, ast.Name) and node.func.id == "open" and node.args:
            mode = _resolve_open_mode(node)
            if mode is None or not _mode_writes(mode):
                return None
            path_text = _resolve_path_expression(node.args[0], self.path_bindings)
            return _format_bridge_write_error(path_text)

        return None

    def _resolve_forbidden_call(self, node: ast.Call) -> str | None:
        qualified_name = _resolve_qualified_name(node.func, self.import_aliases)
        if qualified_name is None:
            return None

        for prefix, message in FORBIDDEN_BRIDGE_CALL_PREFIXES.items():
            if qualified_name == prefix or qualified_name.startswith(f"{prefix}."):
                return message
        return None


class ValidatorOrchestrationVisitor(ast.NodeVisitor):
    """Collect static validator-orchestration scope violations."""

    def __init__(self) -> None:
        self.path_bindings: dict[str, str] = {}
        self.import_aliases: dict[str, str] = {}
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

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            canonical = alias.name
            bound_name = alias.asname or canonical.split(".", 1)[0]
            self.import_aliases[bound_name] = canonical
            self._record_forbidden_import(canonical, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module is None:
            self.generic_visit(node)
            return

        self._record_forbidden_import(node.module, node.lineno)
        for alias in node.names:
            bound_name = alias.asname or alias.name
            self.import_aliases[bound_name] = f"{node.module}.{alias.name}"
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            self._record_command_markers(node.value, node.lineno)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        forbidden_write_error = self._resolve_forbidden_write(node)
        if forbidden_write_error is not None:
            self.errors.append(f"line {node.lineno}: {forbidden_write_error}")

        forbidden_call_error = self._resolve_forbidden_call(node)
        if forbidden_call_error is not None:
            self.errors.append(f"line {node.lineno}: {forbidden_call_error}")

        self.generic_visit(node)

    def _record_forbidden_import(self, module_name: str, lineno: int) -> None:
        for forbidden_module, message in FORBIDDEN_VALIDATOR_IMPORTS.items():
            if module_name == forbidden_module or module_name.startswith(
                f"{forbidden_module}."
            ):
                self.errors.append(f"line {lineno}: {message}")

    def _record_command_markers(self, value: str, lineno: int) -> None:
        normalized_value = value.lower()
        for marker, message in FORBIDDEN_VALIDATOR_COMMAND_MARKERS.items():
            if marker in normalized_value:
                self.errors.append(f"line {lineno}: {message} ({marker.strip()})")

    def _resolve_forbidden_write(self, node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Attribute) and node.func.attr in {
            "write",
            "write_bytes",
            "write_text",
        }:
            path_text = _resolve_path_expression(node.func.value, self.path_bindings)
            return _format_validator_write_error(path_text)

        if isinstance(node.func, ast.Name) and node.func.id == "open" and node.args:
            mode = _resolve_open_mode(node)
            if mode is None or not _mode_writes(mode):
                return None
            path_text = _resolve_path_expression(node.args[0], self.path_bindings)
            return _format_validator_write_error(path_text)

        return None

    def _resolve_forbidden_call(self, node: ast.Call) -> str | None:
        qualified_name = _resolve_qualified_name(node.func, self.import_aliases)
        if qualified_name is None:
            return None

        terminal_name = qualified_name.rsplit(".", 1)[-1]
        if terminal_name in FORBIDDEN_VALIDATOR_CALL_NAMES:
            return FORBIDDEN_VALIDATOR_CALL_NAMES[terminal_name]

        for prefix, message in FORBIDDEN_VALIDATOR_CALL_PREFIXES.items():
            if qualified_name == prefix or qualified_name.startswith(f"{prefix}."):
                return message
        return None


def validate_fail_closed_boundaries(
    root: Path = ROOT,
    *,
    queue_admission_files: list[str] | None = None,
    bridge_scope_files: list[str] | None = None,
    validator_orchestration_files: list[str] | None = None,
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

    resolved_queue_admission_files = (
        QUEUE_ADMISSION_FILES
        if queue_admission_files is None
        else queue_admission_files
    )
    for relative_path in resolved_queue_admission_files:
        path = root / relative_path
        if not path.exists():
            errors.append(f"missing queue admission file: {relative_path}")
            continue
        errors.extend(_validate_queue_admission_file(path, relative_path))

    resolved_bridge_scope_files = (
        BRIDGE_SCOPE_FILES if bridge_scope_files is None else bridge_scope_files
    )
    for relative_path in resolved_bridge_scope_files:
        path = root / relative_path
        if not path.exists():
            errors.append(f"missing bridge scope file: {relative_path}")
            continue
        errors.extend(_validate_bridge_scope_file(path, relative_path))

    resolved_validator_orchestration_files = (
        VALIDATOR_ORCHESTRATION_FILES
        if validator_orchestration_files is None
        else validator_orchestration_files
    )
    for relative_path in resolved_validator_orchestration_files:
        path = root / relative_path
        if not path.exists():
            errors.append(f"missing validator orchestration file: {relative_path}")
            continue
        errors.extend(_validate_validator_orchestration_file(path, relative_path))

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


def _validate_bridge_scope_file(path: Path, relative_path: str) -> list[str]:
    text = path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(text, filename=relative_path)
    except SyntaxError as exc:
        return [f"{relative_path}: syntax error during static scan: {exc.msg}"]

    visitor = BridgeScopeVisitor()
    visitor.visit(tree)
    return [f"{relative_path}: {error}" for error in visitor.errors]


def _validate_validator_orchestration_file(path: Path, relative_path: str) -> list[str]:
    text = path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(text, filename=relative_path)
    except SyntaxError as exc:
        return [f"{relative_path}: syntax error during static scan: {exc.msg}"]

    visitor = ValidatorOrchestrationVisitor()
    visitor.visit(tree)
    return [f"{relative_path}: {error}" for error in visitor.errors]


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

    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _resolve_path_expression(node.left, bindings)
        right = _resolve_path_expression(node.right, bindings)
        if left is not None and right is not None:
            return str(Path(left) / right)

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


def _resolve_qualified_name(
    node: ast.AST,
    import_aliases: dict[str, str],
) -> str | None:
    if isinstance(node, ast.Name):
        return import_aliases.get(node.id, node.id)

    if isinstance(node, ast.Attribute):
        base = _resolve_qualified_name(node.value, import_aliases)
        if base is None:
            return None
        return f"{base}.{node.attr}"

    return None


def _format_bridge_write_error(path_text: str | None) -> str:
    if path_text is None:
        return "bridge scope must not perform file writes"

    normalized = path_text.replace("\\", "/")
    if normalized.endswith("queue/project_queue.yaml"):
        return "bridge scope must not write queue/project_queue.yaml"
    if normalized.endswith("registry/projects.yaml"):
        return "bridge scope must not write registry/projects.yaml"
    if normalized.endswith("registry/repos.yaml"):
        return "bridge scope must not write registry/repos.yaml"
    return f"bridge scope must not perform file writes ({path_text})"


def _format_validator_write_error(path_text: str | None) -> str:
    if path_text is None:
        return "validator orchestration scope must not perform file writes"

    normalized = path_text.replace("\\", "/")
    if normalized.endswith("queue/project_queue.yaml"):
        return "validator orchestration scope must not write queue/project_queue.yaml"
    if normalized.endswith("registry/projects.yaml"):
        return "validator orchestration scope must not write registry/projects.yaml"
    if normalized.endswith("registry/repos.yaml"):
        return "validator orchestration scope must not write registry/repos.yaml"
    return f"validator orchestration scope must not perform repo writes ({path_text})"


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
