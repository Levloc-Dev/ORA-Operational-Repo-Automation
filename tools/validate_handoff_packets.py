#!/usr/bin/env python3
"""Deterministic schema-backed validation for ORA bridge handoff packets."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from ora.validation.schema_subset import (  # noqa: E402
    ValidationResult,
    load_json_file,
    load_yaml_subset_file,
    validate_instance,
    validate_schema_support,
)


def validate_handoff_packets(
    root: Path = ROOT,
    artifact_paths: list[Path] | None = None,
) -> ValidationResult:
    schema_path = root / "schemas/bridge/handoff_packet.schema.json"
    if not schema_path.exists():
        return ValidationResult(("missing file: schemas/bridge/handoff_packet.schema.json",))

    schema = load_json_file(schema_path)
    errors = validate_schema_support(schema, "schemas/bridge/handoff_packet.schema.json")

    for artifact_path in artifact_paths or []:
        if not artifact_path.exists():
            errors.append(f"missing handoff packet artifact: {artifact_path}")
            continue
        if artifact_path.suffix == ".json":
            document = load_json_file(artifact_path)
        elif artifact_path.suffix in {".yaml", ".yml"}:
            try:
                document = load_yaml_subset_file(artifact_path)
            except ValueError as exc:
                errors.append(f"{artifact_path}: {exc}")
                continue
        else:
            errors.append(f"unsupported handoff packet artifact type: {artifact_path}")
            continue

        errors.extend(validate_instance(document, schema, str(artifact_path)))

    return ValidationResult(tuple(errors))


def main(argv: list[str] | None = None) -> int:
    artifact_args = [Path(path) for path in (argv if argv is not None else sys.argv[1:])]
    result = validate_handoff_packets(artifact_paths=artifact_args)

    if not result.ok:
        for error in result.errors:
            print(error, file=sys.stderr)
        return 1

    if artifact_args:
        print("handoff packet validation passed")
    else:
        print("handoff packet schema validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
