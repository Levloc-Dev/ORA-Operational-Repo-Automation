#!/usr/bin/env python3
"""Fail-closed CLI gate for ORA scaffold-writer execution."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.pge.scaffold_writer import ScaffoldWriterError, execute_repo_bootstrap_plan  # noqa: E402
from ora.validation.schema_subset import load_json_file, load_yaml_subset_file  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute a validated ORA bootstrap plan with an explicit local-write gate."
    )
    parser.add_argument("--plan", required=True, help="Path to bootstrap plan JSON or YAML.")
    parser.add_argument(
        "--target-root",
        required=True,
        help="Explicit local target root for the scaffold operation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stage and validate operations without writing. This is the default mode.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Apply staged operations to the target root.",
    )
    parser.add_argument(
        "--confirm-local-write",
        action="store_true",
        help="Required with --execute to authorize local writes.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        plan = load_plan_file(Path(args.plan))
        dry_run = resolve_dry_run(
            execute=args.execute,
            dry_run_flag=args.dry_run,
            confirm_local_write=args.confirm_local_write,
        )
        artifact = execute_repo_bootstrap_plan(
            plan,
            target_root=Path(args.target_root),
            dry_run=dry_run,
            root=ROOT,
        )
    except (PlanExecutionCliError, ScaffoldWriterError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(artifact, indent=2, sort_keys=False))
    return 0


class PlanExecutionCliError(ValueError):
    """Raised when CLI arguments or plan loading fail closed."""


def resolve_dry_run(*, execute: bool, dry_run_flag: bool, confirm_local_write: bool) -> bool:
    if execute and dry_run_flag:
        raise PlanExecutionCliError("refusing to accept both --dry-run and --execute")
    if execute and not confirm_local_write:
        raise PlanExecutionCliError(
            "refusing to execute without --confirm-local-write"
        )
    return not execute


def load_plan_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise PlanExecutionCliError(f"missing plan file: {path}")

    try:
        if path.suffix == ".json":
            document = load_json_file(path)
        elif path.suffix in {".yaml", ".yml"}:
            document = load_yaml_subset_file(path)
        else:
            raise PlanExecutionCliError(f"unsupported plan file type: {path}")
    except ValueError as exc:
        raise PlanExecutionCliError(f"{path}: {exc}") from exc

    if not isinstance(document, dict):
        raise PlanExecutionCliError(f"{path}: plan document must be an object")

    return document


if __name__ == "__main__":
    raise SystemExit(main())
