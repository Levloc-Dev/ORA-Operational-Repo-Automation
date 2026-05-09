"""Fail-closed repo registry admission for scaffolded ORA repositories."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ora.pge.bootstrap_plan import (
    PROJECT_REQUEST_SCHEMA,
    BootstrapPlanError,
    load_project_profile,
    load_project_request_file,
)
from ora.validation.schema_subset import (
    load_json_file,
    load_yaml_subset_file,
    validate_instance,
)


ROOT = Path(__file__).resolve().parents[3]
REPO_REGISTRY_SCHEMA_PATH = Path("schemas/registry/repo_registry.schema.json")
PROJECT_REGISTRY_SCHEMA_PATH = Path("schemas/registry/project_registry.schema.json")
REPOS_REGISTRY_PATH = Path("registry/repos.yaml")
PROJECTS_REGISTRY_PATH = Path("registry/projects.yaml")
ALLOWED_OPERATION_STATUSES = frozenset({"APPLIED", "ALREADY_PRESENT"})
GOVERNED_DEV_MAIN_BRANCH_STRATEGY = "governed_dev_main"
DEFAULT_BRANCH = "main"
DEFAULT_ACTIVE_BRANCH = "main"
GOVERNED_ACTIVE_BRANCH = "dev"


class RepoRegistryAdmissionError(ValueError):
    """Raised when registry admission fails closed."""


def admit_repo_from_execution_artifact(
    request_path: Path,
    execution_result_path: Path,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Validate a scaffold execution artifact and admit the repo into ORA registries."""

    errors: list[str] = []

    request = _load_request(request_path, errors)
    artifact = _load_execution_artifact(execution_result_path, errors)
    registries = _load_registries(root, errors)

    profile: dict[str, Any] | None = None
    if request is not None:
        try:
            profile = load_project_profile(request["profile_id"], root=root)
        except BootstrapPlanError as exc:
            errors.append(str(exc))

    if request is not None and artifact is not None:
        errors.extend(_validate_artifact_against_request(request, artifact))

    repo_id: str | None = None
    project_id: str | None = None
    if request is not None:
        project_id = request["project_id"]
        repo_id = _derive_repo_id(request)

    if registries is not None and repo_id is not None and project_id is not None:
        repos_registry, projects_registry = registries
        errors.extend(
            _validate_duplicate_ids(
                repos_registry["repos"],
                projects_registry["projects"],
                repo_id,
                project_id,
            )
        )

    result: dict[str, Any] = {
        "status": "REJECTED",
        "admitted": False,
        "request_path": str(request_path),
        "execution_result_path": str(execution_result_path),
        "repo_id": repo_id,
        "project_id": project_id,
        "updated_files": [],
        "errors": sorted(errors),
    }

    if errors:
        return result

    assert request is not None
    assert artifact is not None
    assert profile is not None
    assert registries is not None
    assert repo_id is not None
    assert project_id is not None

    repos_registry, projects_registry = registries
    repo_entry = _build_repo_entry(request, artifact, profile, repo_id)
    project_entry = _build_project_entry(project_id)

    updated_repos = _sorted_collection([*repos_registry["repos"], repo_entry], "repo_id")
    updated_projects = _sorted_collection(
        [*projects_registry["projects"], project_entry],
        "project_id",
    )

    _write_registry_file(root / REPOS_REGISTRY_PATH, {"repos": updated_repos})
    _write_registry_file(root / PROJECTS_REGISTRY_PATH, {"projects": updated_projects})

    return {
        "status": "ADMITTED",
        "admitted": True,
        "request_path": str(request_path),
        "execution_result_path": str(execution_result_path),
        "repo_id": repo_id,
        "project_id": project_id,
        "updated_files": [
            str(REPOS_REGISTRY_PATH),
            str(PROJECTS_REGISTRY_PATH),
        ],
        "errors": [],
    }


def _load_request(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        request = load_project_request_file(path)
    except BootstrapPlanError as exc:
        errors.append(str(exc))
        return None

    validation_errors = validate_instance(request, PROJECT_REQUEST_SCHEMA, str(path))
    errors.extend(validation_errors)
    if validation_errors:
        return None
    return request


def _load_execution_artifact(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        document = _load_supported_document(path)
    except RepoRegistryAdmissionError as exc:
        errors.append(str(exc))
        return None

    if not isinstance(document, dict):
        errors.append(f"{path}: execution artifact must be an object")
        return None

    return document


def _load_registries(
    root: Path,
    errors: list[str],
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    repo_schema_path = root / REPO_REGISTRY_SCHEMA_PATH
    project_schema_path = root / PROJECT_REGISTRY_SCHEMA_PATH
    repos_path = root / REPOS_REGISTRY_PATH
    projects_path = root / PROJECTS_REGISTRY_PATH

    for path in (repo_schema_path, project_schema_path, repos_path, projects_path):
        if not path.exists():
            errors.append(f"missing file: {path.relative_to(root)}")

    if errors:
        return None

    repo_schema = load_json_file(repo_schema_path)
    project_schema = load_json_file(project_schema_path)

    try:
        repos_registry = load_yaml_subset_file(repos_path)
    except ValueError as exc:
        errors.append(f"{REPOS_REGISTRY_PATH}: {exc}")
        repos_registry = None

    try:
        projects_registry = load_yaml_subset_file(projects_path)
    except ValueError as exc:
        errors.append(f"{PROJECTS_REGISTRY_PATH}: {exc}")
        projects_registry = None

    if repos_registry is None or projects_registry is None:
        return None

    errors.extend(validate_instance(repos_registry, repo_schema, str(REPOS_REGISTRY_PATH)))
    errors.extend(
        validate_instance(projects_registry, project_schema, str(PROJECTS_REGISTRY_PATH))
    )
    if errors:
        return None

    return repos_registry, projects_registry


def _validate_artifact_against_request(
    request: dict[str, Any],
    artifact: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    dry_run = artifact.get("dry_run")
    if dry_run is not False:
        errors.append("execution artifact must declare dry_run: false")

    target_root = artifact.get("target_root")
    if not isinstance(target_root, str) or not target_root:
        errors.append("execution artifact must declare a non-empty target_root")
    elif target_root != request["local_path"]:
        errors.append(
            "execution artifact target_root does not match request local_path"
        )

    project_profile = artifact.get("project_profile")
    if project_profile != request["profile_id"]:
        errors.append(
            "execution artifact project_profile does not match request profile_id"
        )

    project_name = artifact.get("project_name")
    if project_name != request["repo_name"]:
        errors.append(
            "execution artifact project_name does not match request repo_name"
        )

    operations = artifact.get("operations")
    if not isinstance(operations, list):
        errors.append("execution artifact must declare operations as an array")
        return errors

    operation_count = artifact.get("operation_count")
    if not isinstance(operation_count, int):
        errors.append("execution artifact must declare operation_count as an integer")
    elif operation_count != len(operations):
        errors.append("execution artifact operation_count does not match operations length")

    for index, operation in enumerate(operations):
        if not isinstance(operation, dict):
            errors.append(
                f"execution artifact operations[{index}] must be an object"
            )
            continue

        status = operation.get("status")
        if status not in ALLOWED_OPERATION_STATUSES:
            errors.append(
                f"execution artifact operations[{index}] status must be one of "
                f"{', '.join(sorted(ALLOWED_OPERATION_STATUSES))}"
            )

    return errors


def _validate_duplicate_ids(
    repo_entries: list[dict[str, Any]],
    project_entries: list[dict[str, Any]],
    repo_id: str,
    project_id: str,
) -> list[str]:
    errors: list[str] = []

    if any(entry.get("repo_id") == repo_id for entry in repo_entries):
        errors.append(f"duplicate repo_id '{repo_id}'")
    if any(entry.get("project_id") == project_id for entry in project_entries):
        errors.append(f"duplicate project_id '{project_id}'")

    return errors


def _derive_repo_id(request: dict[str, Any]) -> str:
    return request["project_id"]


def _build_repo_entry(
    request: dict[str, Any],
    artifact: dict[str, Any],
    profile: dict[str, Any],
    repo_id: str,
) -> dict[str, Any]:
    branch_strategy = profile["branch_strategy"]
    return {
        "repo_id": repo_id,
        "repo_name": request["repo_name"],
        "project_profile": request["profile_id"],
        "local_path": artifact["target_root"],
        "github_dev_remote": None,
        "github_main_remote": None,
        "default_branch": DEFAULT_BRANCH,
        "active_branch": _resolve_active_branch(branch_strategy),
        "governance_mode": profile["profile_id"],
        "validator_set": list(profile["required_validators"]),
        "sync_mode": profile["repo_sync_mode"],
        "current_queue_item": None,
        "last_known_status": _resolve_last_known_status(artifact["operations"]),
    }


def _build_project_entry(project_id: str) -> dict[str, str]:
    return {"project_id": project_id}


def _resolve_active_branch(branch_strategy: str) -> str:
    if branch_strategy == GOVERNED_DEV_MAIN_BRANCH_STRATEGY:
        return GOVERNED_ACTIVE_BRANCH
    return DEFAULT_ACTIVE_BRANCH


def _resolve_last_known_status(operations: list[dict[str, Any]]) -> str:
    if operations and all(operation["status"] == "ALREADY_PRESENT" for operation in operations):
        return "ALREADY_PRESENT"
    return "APPLIED"


def _sorted_collection(
    entries: list[dict[str, Any]],
    id_key: str,
) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda entry: str(entry[id_key]))


def _load_supported_document(path: Path) -> Any:
    if not path.exists():
        raise RepoRegistryAdmissionError(f"missing file: {path}")

    try:
        if path.suffix == ".json":
            return load_json_file(path)
        if path.suffix in {".yaml", ".yml"}:
            return load_yaml_subset_file(path)
    except ValueError as exc:
        raise RepoRegistryAdmissionError(f"{path}: {exc}") from exc

    raise RepoRegistryAdmissionError(f"unsupported file type: {path}")


def _write_registry_file(path: Path, document: dict[str, Any]) -> None:
    path.write_text(_dump_yaml(document), encoding="utf-8")


def _dump_yaml(value: Any, *, indent: int = 0) -> str:
    if not isinstance(value, dict):
        raise RepoRegistryAdmissionError("registry document root must be an object")

    lines = _dump_mapping(value, indent)
    return "\n".join(lines) + "\n"


def _dump_mapping(mapping: dict[str, Any], indent: int) -> list[str]:
    lines: list[str] = []
    for key, value in mapping.items():
        prefix = " " * indent
        if isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
                continue
            lines.append(f"{prefix}{key}:")
            lines.extend(_dump_sequence(value, indent + 2))
            continue

        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.extend(_dump_mapping(value, indent + 2))
            continue

        lines.append(f"{prefix}{key}: {_dump_scalar(value)}")
    return lines


def _dump_sequence(values: list[Any], indent: int) -> list[str]:
    lines: list[str] = []
    prefix = " " * indent
    for value in values:
        if isinstance(value, dict):
            first = True
            for key, nested_value in value.items():
                entry_prefix = f"{prefix}- " if first else f"{prefix}  "
                if isinstance(nested_value, list):
                    if not nested_value:
                        lines.append(f"{entry_prefix}{key}: []")
                    else:
                        lines.append(f"{entry_prefix}{key}:")
                        lines.extend(_dump_sequence(nested_value, indent + 4))
                elif isinstance(nested_value, dict):
                    lines.append(f"{entry_prefix}{key}:")
                    lines.extend(_dump_mapping(nested_value, indent + 4))
                else:
                    lines.append(f"{entry_prefix}{key}: {_dump_scalar(nested_value)}")
                first = False
            if first:
                lines.append(f"{prefix}- {{}}")
            continue

        if isinstance(value, list):
            if value:
                raise RepoRegistryAdmissionError("nested sequences are unsupported")
            lines.append(f"{prefix}- []")
            continue

        lines.append(f"{prefix}- {_dump_scalar(value)}")
    return lines


def _dump_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return _dump_string(value)
    raise RepoRegistryAdmissionError(
        f"unsupported registry scalar type: {type(value).__name__}"
    )


def _dump_string(value: str) -> str:
    if value == "":
        return '""'

    safe_characters = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_/.:"
    )
    if set(value) <= safe_characters and not value.startswith(("-", "?", ":", "{", "[")):
        return value

    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    raise RepoRegistryAdmissionError(
        "unsupported string value for deterministic YAML emission"
    )
