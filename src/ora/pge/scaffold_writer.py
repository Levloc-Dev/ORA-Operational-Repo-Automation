"""Deterministic fail-closed scaffold writer for ORA PGE Slice 4."""

from __future__ import annotations

import hashlib
import posixpath
from pathlib import Path, PurePosixPath
from typing import Any

from ora.pge.bootstrap_plan import (
    CANONICAL_SOURCE_CONTENT_STRATEGY,
    DIRECTORY_CONTENT_STRATEGY,
    DIRECTORY_OPERATION_TYPE,
    FILE_OPERATION_TYPE,
    README_TEMPLATE_PATH,
    ROOT,
    TEMPLATE_CONTENT_STRATEGY,
    validate_repo_bootstrap_plan,
)


EXECUTION_ARTIFACT_VERSION = "1.0.0"
DRY_RUN_STATUS = "DRY_RUN"
APPLIED_STATUS = "APPLIED"


class ScaffoldWriterError(ValueError):
    """Raised when scaffold execution violates fail-closed boundaries."""


def execute_repo_bootstrap_plan(
    plan: dict[str, Any],
    *,
    target_root: Path,
    dry_run: bool = False,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Execute a validated bootstrap plan against a single explicit target root."""

    validation = validate_repo_bootstrap_plan(plan, root=root)
    if not validation.ok:
        raise ScaffoldWriterError("; ".join(validation.errors))

    resolved_target_root = target_root.resolve()
    staged_operations = _stage_operations(
        plan=plan,
        target_root=resolved_target_root,
        root=root,
    )

    if not dry_run:
        _apply_operations(staged_operations)

    return _build_execution_artifact(
        plan=plan,
        target_root=resolved_target_root,
        dry_run=dry_run,
        staged_operations=staged_operations,
    )


def _stage_operations(
    *,
    plan: dict[str, Any],
    target_root: Path,
    root: Path,
) -> list[dict[str, Any]]:
    seen_operation_ids: set[str] = set()
    seen_target_paths: set[str] = set()
    staged_operations: list[dict[str, Any]] = []

    for operation in plan["planned_operations"]:
        operation_id = operation["operation_id"]
        if operation_id in seen_operation_ids:
            raise ScaffoldWriterError(f"duplicate operation_id '{operation_id}'")
        seen_operation_ids.add(operation_id)

        normalized_target_path = _normalize_relative_path(operation["target_path"])
        if normalized_target_path in seen_target_paths:
            raise ScaffoldWriterError(f"duplicate target_path '{normalized_target_path}'")
        seen_target_paths.add(normalized_target_path)

        absolute_target_path = _resolve_target_path(
            target_root=target_root,
            normalized_target_path=normalized_target_path,
        )
        staged_operation = _stage_operation(
            operation=operation,
            normalized_target_path=normalized_target_path,
            absolute_target_path=absolute_target_path,
            root=root,
            plan=plan,
        )
        staged_operations.append(staged_operation)

    return staged_operations


def _stage_operation(
    *,
    operation: dict[str, Any],
    normalized_target_path: str,
    absolute_target_path: Path,
    root: Path,
    plan: dict[str, Any],
) -> dict[str, Any]:
    operation_type = operation["operation_type"]
    if operation_type == DIRECTORY_OPERATION_TYPE:
        _validate_directory_operation(operation)
        return {
            "operation_id": operation["operation_id"],
            "operation_type": operation_type,
            "target_path": operation["target_path"],
            "normalized_target_path": normalized_target_path,
            "absolute_target_path": absolute_target_path,
            "source_template": None,
            "content_strategy": DIRECTORY_CONTENT_STRATEGY,
            "content_bytes": None,
        }

    if operation_type == FILE_OPERATION_TYPE:
        content_bytes = _load_file_content(
            operation=operation,
            normalized_target_path=normalized_target_path,
            root=root,
            plan=plan,
        )
        return {
            "operation_id": operation["operation_id"],
            "operation_type": operation_type,
            "target_path": operation["target_path"],
            "normalized_target_path": normalized_target_path,
            "absolute_target_path": absolute_target_path,
            "source_template": operation["source_template"],
            "content_strategy": operation["content_strategy"],
            "content_bytes": content_bytes,
        }

    raise ScaffoldWriterError(f"unknown operation_type '{operation_type}'")


def _validate_directory_operation(operation: dict[str, Any]) -> None:
    if operation["content_strategy"] != DIRECTORY_CONTENT_STRATEGY:
        raise ScaffoldWriterError(
            f"directory operation '{operation['operation_id']}' must use "
            f"'{DIRECTORY_CONTENT_STRATEGY}'"
        )
    if operation["source_template"] is not None:
        raise ScaffoldWriterError(
            f"directory operation '{operation['operation_id']}' must not declare source_template"
        )


def _load_file_content(
    *,
    operation: dict[str, Any],
    normalized_target_path: str,
    root: Path,
    plan: dict[str, Any],
) -> bytes:
    source_template = operation["source_template"]
    if not isinstance(source_template, str) or not source_template:
        raise ScaffoldWriterError(
            f"file operation '{operation['operation_id']}' must declare source_template"
        )

    content_strategy = operation["content_strategy"]
    if content_strategy == TEMPLATE_CONTENT_STRATEGY:
        return _render_readme_template(
            source_template=source_template,
            normalized_target_path=normalized_target_path,
            root=root,
            plan=plan,
        )

    if content_strategy == CANONICAL_SOURCE_CONTENT_STRATEGY:
        source_path = root / _normalize_relative_path(source_template)
        if not source_path.exists():
            raise ScaffoldWriterError(f"missing canonical source: {source_template}")
        if not source_path.is_file():
            raise ScaffoldWriterError(f"canonical source is not a file: {source_template}")
        return source_path.read_bytes()

    raise ScaffoldWriterError(
        f"file operation '{operation['operation_id']}' uses unsupported content_strategy "
        f"'{content_strategy}'"
    )


def _render_readme_template(
    *,
    source_template: str,
    normalized_target_path: str,
    root: Path,
    plan: dict[str, Any],
) -> bytes:
    if source_template != README_TEMPLATE_PATH:
        raise ScaffoldWriterError(
            f"unsupported template source '{source_template}' for deterministic README render"
        )
    if normalized_target_path != "README.md":
        raise ScaffoldWriterError(
            "template rendering is only permitted for target_path 'README.md'"
        )

    template_path = root / README_TEMPLATE_PATH
    if not template_path.exists():
        raise ScaffoldWriterError(f"missing template: {README_TEMPLATE_PATH}")
    if not template_path.is_file():
        raise ScaffoldWriterError(f"template is not a file: {README_TEMPLATE_PATH}")

    template_text = template_path.read_text(encoding="utf-8")
    marker = "{{ project_name }}"
    rendered = template_text.replace(marker, plan["project_name"])
    if "{{" in rendered or "}}" in rendered:
        raise ScaffoldWriterError(
            f"unsupported template marker detected in {README_TEMPLATE_PATH}"
        )
    return rendered.encode("utf-8")


def _apply_operations(staged_operations: list[dict[str, Any]]) -> None:
    for staged_operation in staged_operations:
        absolute_target_path = staged_operation["absolute_target_path"]
        if staged_operation["operation_type"] == DIRECTORY_OPERATION_TYPE:
            absolute_target_path.mkdir(parents=True, exist_ok=True)
            continue

        if absolute_target_path.exists():
            if absolute_target_path.is_dir():
                raise ScaffoldWriterError(
                    f"refusing to overwrite directory with file: {absolute_target_path}"
                )
            existing_content = absolute_target_path.read_bytes()
            if existing_content != staged_operation["content_bytes"]:
                raise ScaffoldWriterError(
                    f"refusing to overwrite existing file without explicit authorization: {absolute_target_path}"
                )
            continue

        absolute_target_path.parent.mkdir(parents=True, exist_ok=True)
        absolute_target_path.write_bytes(staged_operation["content_bytes"])


def _build_execution_artifact(
    *,
    plan: dict[str, Any],
    target_root: Path,
    dry_run: bool,
    staged_operations: list[dict[str, Any]],
) -> dict[str, Any]:
    status = DRY_RUN_STATUS if dry_run else APPLIED_STATUS
    return {
        "artifact_version": EXECUTION_ARTIFACT_VERSION,
        "plan_version": plan["plan_version"],
        "project_name": plan["project_name"],
        "project_profile": plan["project_profile"],
        "target_root": str(target_root),
        "dry_run": dry_run,
        "operation_count": len(staged_operations),
        "operations": [
            {
                "operation_id": staged_operation["operation_id"],
                "operation_type": staged_operation["operation_type"],
                "target_path": staged_operation["target_path"],
                "normalized_target_path": staged_operation["normalized_target_path"],
                "source_template": staged_operation["source_template"],
                "content_strategy": staged_operation["content_strategy"],
                "status": status,
                "bytes_written": _content_size(staged_operation["content_bytes"]),
                "content_sha256": _content_sha256(staged_operation["content_bytes"]),
            }
            for staged_operation in staged_operations
        ],
    }


def _content_size(content_bytes: bytes | None) -> int:
    if content_bytes is None:
        return 0
    return len(content_bytes)


def _content_sha256(content_bytes: bytes | None) -> str | None:
    if content_bytes is None:
        return None
    return hashlib.sha256(content_bytes).hexdigest()


def _resolve_target_path(*, target_root: Path, normalized_target_path: str) -> Path:
    absolute_target_path = (target_root / normalized_target_path).resolve()
    try:
        absolute_target_path.relative_to(target_root)
    except ValueError as exc:
        raise ScaffoldWriterError(
            f"target_path '{normalized_target_path}' escapes target root '{target_root}'"
        ) from exc
    return absolute_target_path


def _normalize_relative_path(raw_path: str) -> str:
    if not isinstance(raw_path, str) or not raw_path:
        raise ScaffoldWriterError("path must be a non-empty string")
    if "\\" in raw_path:
        raise ScaffoldWriterError(f"path uses unsupported separator '\\\\': {raw_path}")
    if PurePosixPath(raw_path).is_absolute():
        raise ScaffoldWriterError(f"absolute paths are not allowed: {raw_path}")

    normalized = posixpath.normpath(raw_path)
    if normalized in {".", ""}:
        raise ScaffoldWriterError(f"path must not resolve to the target root: {raw_path}")
    if normalized == ".." or normalized.startswith("../"):
        raise ScaffoldWriterError(f"path traversal is not allowed: {raw_path}")
    return normalized
