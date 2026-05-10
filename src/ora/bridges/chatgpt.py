"""Deterministic governed handoff packet builder for ChatGPT."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ora.bridges._governed_handoff import ROOT, build_handoff_packet


def build_chatgpt_handoff_packet(
    project_id: str,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Build a deterministic handoff packet for the ChatGPT bridge."""

    return build_handoff_packet(project_id, "CHATGPT", root=root)
