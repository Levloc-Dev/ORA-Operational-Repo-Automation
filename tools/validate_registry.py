#!/usr/bin/env python3
"""Deterministic schema-backed validation for ORA registries."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.validation.schema_subset import (  # noqa: E402
    ValidationResult,
    load_json_file,
    load_yaml_subset_file,
    validate_instance,
)


REPO_SCHEMA_PATH = "schemas/registry/repo_registry.schema.json"
REPOS_PATH = "registry/repos.yaml"
PROJECTS_PATH = "registry/projects.yaml"
PROJECT_REGISTRY_SCHEMA_PATH = "schemas/registry/project_registry.schema.json"


def validate_registry(root: Path = ROOT) -> ValidationResult:
    errors: list[str] = []
    repo_schema_path = root / REPO_SCHEMA_PATH
    repos_path = root / REPOS_PATH
    projects_path = root / PROJECTS_PATH
    project_schema_path = root / PROJECT_REGISTRY_SCHEMA_PATH

    if not repo_schema_path.exists():
        errors.append(f"missing file: {REPO_SCHEMA_PATH}")
    if not repos_path.exists():
        errors.append(f"missing file: {REPOS_PATH}")
    if not projects_path.exists():
        errors.append(f"missing file: {PROJECTS_PATH}")

    if repo_schema_path.exists() and repos_path.exists():
        schema = load_json_file(repo_schema_path)
        try:
            document = load_yaml_subset_file(repos_path)
        except ValueError as exc:
            errors.append(f"{REPOS_PATH}: {exc}")
        else:
            errors.extend(validate_instance(document, schema, REPOS_PATH))

    if projects_path.exists():
        if not project_schema_path.exists():
            errors.append(
                "TODO: add schemas/registry/project_registry.schema.json to validate "
                "registry/projects.yaml deterministically"
            )
        else:
            project_schema = load_json_file(project_schema_path)
            try:
                project_document = load_yaml_subset_file(projects_path)
            except ValueError as exc:
                errors.append(f"{PROJECTS_PATH}: {exc}")
            else:
                errors.extend(
                    validate_instance(project_document, project_schema, PROJECTS_PATH)
                )

    return ValidationResult(tuple(errors))


def main() -> int:
    result = validate_registry()

    if not result.ok:
        for error in result.errors:
            print(error, file=sys.stderr)
        return 1

    print("registry validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
