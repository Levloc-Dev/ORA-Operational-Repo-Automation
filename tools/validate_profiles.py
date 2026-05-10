#!/usr/bin/env python3
"""Deterministic schema-backed validation for ORA project profiles."""

from __future__ import annotations

import argparse
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
from ora.validation.result_capture import build_validator_output, render_output  # noqa: E402


PROFILE_DIR = ROOT / "profiles"
SCHEMA_PATH = ROOT / "schemas/profile/project_profile.schema.json"
PROFILE_FILES = [
    "CSL_GOVERNED.yaml",
    "STANDALONE_LIGHT.yaml",
    "STANDALONE_COMMERCIAL.yaml",
    "RESEARCH_LIBRARY.yaml",
    "SANDBOX.yaml",
]
REQUIRED_PROHIBITED_ACTIONS = {
    "unrestricted_shell",
    "deploy",
    "autonomous_merge",
}


def validate_profiles(root: Path = ROOT) -> ValidationResult:
    errors: list[str] = []
    schema_path = root / "schemas/profile/project_profile.schema.json"
    profile_dir = root / "profiles"

    if not schema_path.exists():
        errors.append("missing schema: schemas/profile/project_profile.schema.json")
        return ValidationResult(tuple(errors))

    schema = load_json_file(schema_path)

    for name in PROFILE_FILES:
        path = profile_dir / name
        if not path.exists():
            errors.append(f"missing profile: profiles/{name}")
            continue
        try:
            document = load_yaml_subset_file(path)
        except ValueError as exc:
            errors.append(f"profiles/{name}: {exc}")
            continue

        errors.extend(validate_instance(document, schema, f"profiles/{name}"))

        if isinstance(document, dict):
            prohibited_actions = document.get("prohibited_actions")
            if isinstance(prohibited_actions, list):
                missing_actions = sorted(
                    action
                    for action in REQUIRED_PROHIBITED_ACTIONS
                    if action not in prohibited_actions
                )
                for action in missing_actions:
                    errors.append(
                        f"profiles/{name}: prohibited_actions missing fail-closed entry '{action}'"
                    )
            else:
                errors.append(
                    f"profiles/{name}: prohibited_actions must be a list for fail-closed checks"
                )

    return ValidationResult(tuple(errors))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deterministic schema-backed validation for ORA project profiles."
    )
    parser.add_argument(
        "--format",
        choices=["json", "yaml", "text"],
        default="text",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = validate_profiles()

    if args.format == "text":
        if not result.ok:
            for error in result.errors:
                print(error, file=sys.stderr)
            return 1

        print("profile validation passed")
        return 0

    document = build_validator_output(
        "tools/validate_profiles.py",
        ok=result.ok,
        summary=(
            "profile validation passed"
            if result.ok
            else f"profile validation failed with {len(result.errors)} issue(s)"
        ),
        errors=list(result.errors),
    )
    print(render_output(document, args.format), end="")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
