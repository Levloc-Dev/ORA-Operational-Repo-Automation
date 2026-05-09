"""Deterministic repo bootstrap plan generation for ORA PGE Slice 3."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ora.validation.schema_subset import (
    ValidationResult,
    load_json_file,
    load_yaml_subset_file,
    validate_instance,
    validate_schema_support,
)


ROOT = Path(__file__).resolve().parents[3]
PROJECT_REQUEST_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "project_id",
        "repo_name",
        "profile_id",
        "description",
        "target_owner",
        "local_path",
    ],
    "properties": {
        "project_id": {"type": "string"},
        "repo_name": {"type": "string"},
        "profile_id": {"type": "string"},
        "description": {"type": "string"},
        "target_owner": {"type": "string"},
        "local_path": {"type": "string"},
    },
}
PROFILE_SCHEMA_PATH = Path("schemas/profile/project_profile.schema.json")
PLAN_SCHEMA_PATH = Path("schemas/pge/repo_bootstrap_plan.schema.json")
PLAN_VERSION = "1.0.0"


class BootstrapPlanError(ValueError):
    """Raised when request, profile, or plan validation fails closed."""


def build_repo_bootstrap_plan_from_file(
    request_path: Path,
    *,
    root: Path = ROOT,
    plan_schema_path: Path | None = None,
) -> dict[str, Any]:
    """Load a project request file and return a validated bootstrap plan."""

    request = load_project_request_file(request_path)
    return build_repo_bootstrap_plan(
        request,
        root=root,
        request_source=str(request_path),
        plan_schema_path=plan_schema_path,
    )


def build_repo_bootstrap_plan(
    project_request: dict[str, Any],
    *,
    root: Path = ROOT,
    request_source: str = "<project_request>",
    plan_schema_path: Path | None = None,
) -> dict[str, Any]:
    """Build a deterministic bootstrap plan from request metadata and profile."""

    request_errors = validate_instance(
        project_request,
        PROJECT_REQUEST_SCHEMA,
        request_source,
    )
    if request_errors:
        raise BootstrapPlanError(_format_errors(request_errors))

    profile = load_project_profile(project_request["profile_id"], root=root)
    plan = _assemble_plan(project_request, profile)

    validation = validate_repo_bootstrap_plan(
        plan,
        root=root,
        schema_path=plan_schema_path,
    )
    if not validation.ok:
        raise BootstrapPlanError(_format_errors(validation.errors))

    return plan


def load_project_request_file(path: Path) -> dict[str, Any]:
    """Load a request file from JSON or the supported YAML subset."""

    if not path.exists():
        raise BootstrapPlanError(f"missing request file: {path}")

    try:
        if path.suffix == ".json":
            document = load_json_file(path)
        elif path.suffix in {".yaml", ".yml"}:
            document = load_yaml_subset_file(path)
        else:
            raise BootstrapPlanError(f"unsupported request file type: {path}")
    except ValueError as exc:
        raise BootstrapPlanError(f"{path}: {exc}") from exc

    if not isinstance(document, dict):
        raise BootstrapPlanError(f"{path}: request document must be an object")

    return document


def load_project_profile(profile_id: str, *, root: Path = ROOT) -> dict[str, Any]:
    """Load and validate a named project profile."""

    schema_path = root / PROFILE_SCHEMA_PATH
    profile_path = root / "profiles" / f"{profile_id}.yaml"

    if not profile_path.exists():
        raise BootstrapPlanError(f"unknown profile_id '{profile_id}'")
    if not schema_path.exists():
        raise BootstrapPlanError(f"missing file: {PROFILE_SCHEMA_PATH}")

    schema = load_json_file(schema_path)
    try:
        document = load_yaml_subset_file(profile_path)
    except ValueError as exc:
        raise BootstrapPlanError(f"profiles/{profile_path.name}: {exc}") from exc

    if not isinstance(document, dict):
        raise BootstrapPlanError(f"profiles/{profile_path.name}: profile must be an object")

    errors = validate_instance(document, schema, f"profiles/{profile_path.name}")
    if errors:
        raise BootstrapPlanError(_format_errors(errors))

    actual_profile_id = document.get("profile_id")
    if actual_profile_id != profile_id:
        raise BootstrapPlanError(
            f"profiles/{profile_path.name}: profile_id '{actual_profile_id}' does not match requested profile '{profile_id}'"
        )

    return document


def validate_repo_bootstrap_plan(
    plan: dict[str, Any],
    *,
    root: Path = ROOT,
    schema_path: Path | None = None,
) -> ValidationResult:
    """Validate a generated plan against the bootstrap plan schema."""

    resolved_schema_path = schema_path or (root / PLAN_SCHEMA_PATH)
    if not resolved_schema_path.exists():
        return ValidationResult((f"missing file: {resolved_schema_path}",))

    schema = load_json_file(resolved_schema_path)
    schema_label = _display_schema_path(resolved_schema_path, root)
    errors = validate_schema_support(schema, schema_label)
    errors.extend(validate_instance(plan, schema, "repo_bootstrap_plan"))
    return ValidationResult(tuple(errors))


def _assemble_plan(
    project_request: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    write_files = _stable_unique(
        [*profile["required_governance_artifacts"], *profile["initial_files"]]
    )
    create_directories = _stable_unique(
        [*profile["required_directories"], *_parent_directories(write_files)]
    )

    return {
        "plan_version": PLAN_VERSION,
        "project_name": project_request["repo_name"],
        "project_profile": profile["profile_id"],
        "create_directories": create_directories,
        "write_files": write_files,
        "validators": _stable_unique(profile["required_validators"]),
        # Slice 3 is a dry-run planner only; execution must remain escalated.
        "escalation_required": True,
    }


def _parent_directories(paths: list[str]) -> list[str]:
    parents: list[str] = []
    for path in paths:
        parent = Path(path).parent
        if str(parent) != ".":
            parents.append(parent.as_posix())
    return parents


def _stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _display_schema_path(schema_path: Path, root: Path) -> str:
    try:
        return schema_path.relative_to(root).as_posix()
    except ValueError:
        return str(schema_path)


def _format_errors(errors: tuple[str, ...] | list[str]) -> str:
    return "\n".join(errors)
