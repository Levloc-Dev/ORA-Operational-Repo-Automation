#!/usr/bin/env python3
"""Fail-closed CLI for ORA registry admission."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.registry.repo_registry import admit_repo_from_execution_artifact  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Admit a scaffolded repository into the ORA registries."
    )
    parser.add_argument(
        "--request",
        required=True,
        help="Path to the bootstrap request JSON or YAML file.",
    )
    parser.add_argument(
        "--execution-result",
        required=True,
        help="Path to the scaffold execution artifact JSON or YAML file.",
    )
    return parser


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)
    result = admit_repo_from_execution_artifact(
        Path(args.request),
        Path(args.execution_result),
        root=root,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["admitted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
