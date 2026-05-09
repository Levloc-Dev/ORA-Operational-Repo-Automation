#!/usr/bin/env python3
"""Dry-run ORA bootstrap-plan generator for PGE Slice 3."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.pge.bootstrap_plan import BootstrapPlanError, build_repo_bootstrap_plan_from_file  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print(
            "usage: python3 tools/ora_bootstrap_project.py <project-request.{json,yaml}>",
            file=sys.stderr,
        )
        return 1

    request_path = Path(args[0])
    try:
        plan = build_repo_bootstrap_plan_from_file(request_path, root=ROOT)
    except BootstrapPlanError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(plan, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
