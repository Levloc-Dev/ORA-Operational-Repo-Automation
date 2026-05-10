"""Deterministic validator output rendering and result capture."""

from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from ora.validation.schema_subset import load_json_file, validate_instance


ROOT = Path(__file__).resolve().parents[3]
RESULT_SCHEMA_PATH = Path("schemas/validation/validator_result.schema.json")
RESULT_ARTIFACTS_DIR = Path("governance/workflows/validation_reports")
RESULT_ARTIFACT_VERSION = "1.0.0"
VALIDATOR_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["validator_id", "ok", "summary", "errors"],
    "properties": {
        "validator_id": {"type": "string"},
        "ok": {"type": "boolean"},
        "summary": {"type": "string"},
        "errors": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}
ALLOWED_VALIDATOR_COMMANDS = {
    "tools/validate_repo_layout.py": ("tools/validate_repo_layout.py",),
    "tools/validate_profiles.py": ("tools/validate_profiles.py",),
}
SUPPORTED_OUTPUT_FORMATS = {"json", "yaml"}


class ValidatorExecutionError(ValueError):
    """Raised when validator execution cannot proceed safely."""


def build_validator_output(
    validator_id: str,
    *,
    ok: bool,
    summary: str,
    errors: list[str],
) -> dict[str, Any]:
    """Build a deterministic validator self-report document."""

    document = {
        "validator_id": validator_id,
        "ok": ok,
        "summary": summary,
        "errors": sorted(errors),
    }
    validation_errors = validate_instance(
        document,
        VALIDATOR_OUTPUT_SCHEMA,
        "validator_output",
    )
    if validation_errors:
        raise ValidatorExecutionError("; ".join(sorted(validation_errors)))
    return document


def render_output(document: dict[str, Any], output_format: str) -> str:
    """Render deterministic JSON or YAML."""

    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ValidatorExecutionError(f"unsupported output format '{output_format}'")

    if output_format == "json":
        return json.dumps(document, indent=2, sort_keys=True) + "\n"
    return _render_yaml(document) + "\n"


def execute_validator_command(
    *,
    project_id: str,
    repo_id: str,
    profile_id: str,
    validator_id: str,
    root: Path = ROOT,
    artifact_format: str = "json",
) -> dict[str, Any]:
    """Execute one allowlisted validator and capture a deterministic result artifact."""

    command = resolve_validator_command(validator_id, root=root)
    started_at = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    stdout_text = completed.stdout
    stderr_text = completed.stderr
    failure_reason: str | None = None
    validator_output: dict[str, Any] | None = None

    if completed.returncode != 0:
        failure_reason = f"validator exited with code {completed.returncode}"
        result_status = "FAIL"
    else:
        try:
            validator_output = parse_validator_output(stdout_text, validator_id)
        except ValidatorExecutionError as exc:
            failure_reason = str(exc)
            result_status = "ERROR"
        else:
            result_status = "PASS" if validator_output["ok"] else "FAIL"
            if not validator_output["ok"]:
                failure_reason = "validator reported failures"

    artifact = {
        "artifact_version": RESULT_ARTIFACT_VERSION,
        "project_id": project_id,
        "repo_id": repo_id,
        "profile_id": profile_id,
        "validator_id": validator_id,
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "stdout_hash": _hash_text(stdout_text),
        "stderr_hash": _hash_text(stderr_text),
        "duration_ms": duration_ms,
        "working_directory": str(root),
        "timestamp": None,
        "result_status": result_status,
        "failure_reason": failure_reason,
        "validator_output": validator_output,
    }
    validate_result_artifact(artifact, root=root)
    write_result_artifact(
        artifact,
        project_id=project_id,
        validator_id=validator_id,
        output_format=artifact_format,
        root=root,
    )
    return artifact


def resolve_validator_command(validator_id: str, *, root: Path = ROOT) -> tuple[str, ...]:
    """Resolve a validator id to its fixed, shell-free command tuple."""

    command_suffix = ALLOWED_VALIDATOR_COMMANDS.get(validator_id)
    if command_suffix is None:
        raise ValidatorExecutionError(f"unknown validator_id '{validator_id}'")

    validator_path = root / command_suffix[0]
    if not validator_path.exists():
        raise ValidatorExecutionError(
            f"missing validator command for '{validator_id}': {command_suffix[0]}"
        )

    return (
        sys.executable,
        str(validator_path),
        "--format",
        "json",
    )


def parse_validator_output(stdout_text: str, validator_id: str) -> dict[str, Any]:
    """Parse and validate structured validator stdout."""

    try:
        document = json.loads(stdout_text)
    except json.JSONDecodeError as exc:
        raise ValidatorExecutionError(
            f"malformed result output for '{validator_id}': invalid JSON"
        ) from exc

    validation_errors = validate_instance(
        document,
        VALIDATOR_OUTPUT_SCHEMA,
        "validator_output",
    )
    if validation_errors:
        raise ValidatorExecutionError(
            f"malformed result output for '{validator_id}': "
            + "; ".join(sorted(validation_errors))
        )

    if document["validator_id"] != validator_id:
        raise ValidatorExecutionError(
            f"malformed result output for '{validator_id}': validator_id mismatch"
        )

    return document


def validate_result_artifact(
    document: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    """Validate the result artifact against the declared schema."""

    schema_path = root / RESULT_SCHEMA_PATH
    if not schema_path.exists():
        raise ValidatorExecutionError(f"missing file: {RESULT_SCHEMA_PATH}")

    schema = load_json_file(schema_path)
    errors = validate_instance(
        document,
        schema,
        "validator_result",
    )
    if errors:
        raise ValidatorExecutionError("; ".join(sorted(errors)))


def write_result_artifact(
    document: dict[str, Any],
    *,
    project_id: str,
    validator_id: str,
    output_format: str,
    root: Path = ROOT,
) -> Path:
    """Write the declared validator result artifact."""

    artifact_path = build_result_artifact_path(
        project_id=project_id,
        validator_id=validator_id,
        output_format=output_format,
        root=root,
    )
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(render_output(document, output_format), encoding="utf-8")
    return artifact_path


def build_result_artifact_path(
    *,
    project_id: str,
    validator_id: str,
    output_format: str,
    root: Path = ROOT,
) -> Path:
    """Return the deterministic artifact path for a project-validator pair."""

    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ValidatorExecutionError(f"unsupported output format '{output_format}'")

    suffix = ".json" if output_format == "json" else ".yaml"
    slug = _slugify(validator_id)
    return root / RESULT_ARTIFACTS_DIR / f"{project_id}--{slug}{suffix}"


def _hash_text(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def _slugify(value: str) -> str:
    result = []
    for character in value:
        if character.isalnum():
            result.append(character)
        else:
            result.append("_")
    return "".join(result)


def _render_yaml(value: Any, *, indent: int = 0) -> str:
    if isinstance(value, dict):
        lines: list[str] = []
        for key in sorted(value):
            rendered = _render_yaml(value[key], indent=indent + 2)
            if _is_scalar(value[key]):
                lines.append(f"{' ' * indent}{key}: {rendered.strip()}")
            else:
                lines.append(f"{' ' * indent}{key}:")
                lines.append(rendered.rstrip("\n"))
        return "\n".join(lines)

    if isinstance(value, list):
        if not value:
            return f"{' ' * indent}[]"

        lines = []
        for entry in value:
            if _is_scalar(entry):
                lines.append(f"{' ' * indent}- {_render_yaml(entry).strip()}")
            else:
                lines.append(f"{' ' * indent}-")
                lines.append(_render_yaml(entry, indent=indent + 2).rstrip("\n"))
        return "\n".join(lines)

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return json.dumps(str(value))


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, bool, int, float))
