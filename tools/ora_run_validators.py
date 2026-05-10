#!/usr/bin/env python3
"""Fail-closed CLI for deterministic ORA validator plan generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.validation.validator_orchestrator import (  # noqa: E402
    ValidatorOrchestratorError,
    build_validator_plan,
    render_validator_plan_json,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate deterministic ORA validator execution plans."
    )
    parser.add_argument("--project-id", required=True)
    return parser


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)

    try:
        plan = build_validator_plan(args.project_id, root=root)
    except ValidatorOrchestratorError as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "generated": False,
                    "project_id": getattr(args, "project_id", None),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    print(render_validator_plan_json(plan), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
