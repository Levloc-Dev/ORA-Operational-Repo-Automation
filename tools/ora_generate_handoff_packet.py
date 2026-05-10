#!/usr/bin/env python3
"""Fail-closed CLI for deterministic ORA governed handoff packet generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.bridges._governed_handoff import (  # noqa: E402
    HandoffPacketError,
    render_handoff_packet_json,
)
from ora.bridges.chatgpt import build_chatgpt_handoff_packet  # noqa: E402
from ora.bridges.claude import build_claude_handoff_packet  # noqa: E402
from ora.bridges.codex import build_codex_handoff_packet  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic ORA governed handoff packet."
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--bridge-type", required=True)
    return parser


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    args = build_parser().parse_args(argv)
    bridge_type = args.bridge_type.upper()

    try:
        packet = _build_bridge_packet(
            project_id=args.project_id,
            bridge_type=bridge_type,
            root=root,
        )
    except HandoffPacketError as exc:
        print(
            json.dumps(
                {
                    "bridge_type": bridge_type,
                    "error": str(exc),
                    "generated": False,
                    "project_id": args.project_id,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    print(render_handoff_packet_json(packet), end="")
    return 0


def _build_bridge_packet(
    *,
    project_id: str,
    bridge_type: str,
    root: Path,
) -> dict[str, object]:
    if bridge_type == "CHATGPT":
        return build_chatgpt_handoff_packet(project_id, root=root)
    if bridge_type == "CLAUDE":
        return build_claude_handoff_packet(project_id, root=root)
    if bridge_type == "CODEX":
        return build_codex_handoff_packet(project_id, root=root)
    raise HandoffPacketError(f"unsupported bridge_type '{bridge_type}'")


if __name__ == "__main__":
    raise SystemExit(main())
