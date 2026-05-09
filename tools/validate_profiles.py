#!/usr/bin/env python3
"""Fail-closed static validation for Slice 1 profile stubs."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / "profiles"
SCHEMA_PATH = ROOT / "schemas/profile/project_profile.schema.json"
PROFILE_FILES = [
    "CSL_GOVERNED.yaml",
    "STANDALONE_LIGHT.yaml",
    "STANDALONE_COMMERCIAL.yaml",
    "RESEARCH_LIBRARY.yaml",
    "SANDBOX.yaml",
]
REQUIRED_KEYS = [
    "profile_id:",
    "required_directories:",
    "optional_directories:",
    "required_governance_artifacts:",
    "required_validators:",
    "branch_strategy:",
    "repo_sync_mode:",
    "initial_files:",
    "prohibited_actions:",
    "escalation_triggers:",
]


def main() -> int:
    errors: list[str] = []
    if not SCHEMA_PATH.exists():
        errors.append("missing schema: schemas/profile/project_profile.schema.json")

    for name in PROFILE_FILES:
        path = PROFILE_DIR / name
        if not path.exists():
            errors.append(f"missing profile: profiles/{name}")
            continue
        text = path.read_text(encoding="utf-8")
        for key in REQUIRED_KEYS:
            if key not in text:
                errors.append(f"profiles/{name} missing key {key.rstrip(':')}")
        if "unrestricted_shell" not in text:
            errors.append(f"profiles/{name} missing fail-closed prohibited action")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("profile validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
