#!/usr/bin/env python3
"""Explicit single-validator execution entrypoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.validation.result_capture import (  # noqa: E402
    ValidatorExecutionError,
    execute_validator_command,
    render_output,
    resolve_validator_command,
)
from ora.validation.validator_orchestrator import (  # noqa: E402
    ValidatorOrchestratorError,
    build_validator_plan,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one explicitly declared ORA validator and capture its result."
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--validator-id", required=True)
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="json",
    )
    return parser


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)

    try:
        plan = build_validator_plan(args.project_id, root=root)
        resolve_validator_command(args.validator_id, root=root)
        if args.validator_id not in plan["validators"]:
            raise ValidatorExecutionError(
                f"undeclared validator execution request '{args.validator_id}' for project_id '{args.project_id}'"
            )
        artifact = execute_validator_command(
            project_id=args.project_id,
            repo_id=plan["repo_id"],
            profile_id=plan["profile_id"],
            validator_id=args.validator_id,
            artifact_format=args.format,
            root=root,
        )
    except (ValidatorExecutionError, ValidatorOrchestratorError) as exc:
        print(
            json.dumps(
                {
                    "executed": False,
                    "project_id": getattr(args, "project_id", None),
                    "validator_id": getattr(args, "validator_id", None),
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    print(render_output(artifact, args.format), end="")
    return 0 if artifact["result_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
