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
    update_queue_item_state,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Register and update deterministic ORA queue items."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    register_parser = subparsers.add_parser(
        "register",
        help="Register a new queue item for a known repo.",
    )
    register_parser.add_argument("--repo-id", required=True)
    register_parser.add_argument("--queue-item-id", required=True)
    register_parser.add_argument("--state", required=True)
    register_parser.add_argument("--next-action", required=True)
    register_parser.add_argument("--reason")

    update_parser = subparsers.add_parser(
        "update-state",
        help="Update a known queue item to a closed-set state.",
    )
    update_parser.add_argument("--queue-item-id", required=True)
    update_parser.add_argument("--state", required=True)
    update_parser.add_argument("--next-action", required=True)
    update_parser.add_argument("--reason")

    return parser


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.command == "register":
            result = register_queue_item(
                repo_id=args.repo_id,
                queue_item_id=args.queue_item_id,
                state=args.state,
                next_action=args.next_action,
                root=root,
                reason=args.reason,
            )
        else:
            result = update_queue_item_state(
                queue_item_id=args.queue_item_id,
                state=args.state,
                next_action=args.next_action,
                root=root,
                reason=args.reason,
            )
    except QueueManagerError as exc:
        result = {
            "status": "REJECTED",
            "error": str(exc),
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
