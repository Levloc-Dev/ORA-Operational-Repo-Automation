#!/usr/bin/env python3
"""Fail-closed CLI for deterministic ORA queue updates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.queue.queue_manager import (  # noqa: E402
    QueueManagerError,
    register_queue_item,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Admit deterministic ORA queue items."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    admit_parser = subparsers.add_parser(
        "admit",
        help="Admit a known project to the queue.",
    )
    admit_parser.add_argument("--project-id", required=True)
    admit_parser.add_argument("--profile-id", required=True)

    return parser


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)

    try:
        result = register_queue_item(
            project_id=args.project_id,
            profile_id=args.profile_id,
            root=root,
        )
    except QueueManagerError as exc:
        result = {
            "admitted": False,
            "error": str(exc),
            "profile_id": getattr(args, "profile_id", None),
            "project_id": getattr(args, "project_id", None),
            "repo_id": getattr(args, "project_id", None),
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
