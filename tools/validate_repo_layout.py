#!/usr/bin/env python3
"""Fail-closed repository layout validator for the ORA Slice 1 scaffold."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PATHS = [
    "README.md",
    "PROJECT_CONTEXT.md",
    "ORA_SOURCE_CONTEXT_v1.0.0.md",
    "CHANGELOG.md",
    ".gitignore",
    "pyproject.toml",
    "LICENSE_PENDING.md",
    ".bootstrap/bootstrap_manifest.yaml",
    ".bootstrap/template_provenance.yaml",
    "governance/constitution",
    "governance/constitution/AI_CONSTITUTION.md",
    "governance/control_plane",
    "governance/control_plane/DECISION_GATE.md",
    "governance/policies/ORA_CAPABILITY_BOUNDARY.md",
    "governance/policies/ORA_FAIL_CLOSED_POLICY.md",
    "governance/workflows/governed_specs",
    "governance/workflows/validation_reports",
    "governance/reviews",
    "memory/evolution/decisions",
    "memory/evolution/executions",
    "memory/indexes/decision_index.yaml",
    "planning/seeds",
    "planning/prompts",
    "planning/implementation_prompts",
    "planning/implementation_prompts/ORA_CODEX_CREATE_V1_REPO_SCAFFOLD_PROMPT.md",
    "docs/architecture/snapshots",
    "docs/architecture/ORA_SYSTEM_OVERVIEW.md",
    "docs/architecture/ORA_SUBSYSTEM_BOUNDARIES.md",
    "docs/contracts",
    "docs/operations",
    "schemas/profile/project_profile.schema.json",
    "schemas/pge/repo_bootstrap_plan.schema.json",
    "schemas/registry/repo_registry.schema.json",
    "schemas/registry/project_registry.schema.json",
    "schemas/queue/queue_item.schema.json",
    "schemas/operation/operation_plan.schema.json",
    "schemas/validation/validator_result.schema.json",
    "schemas/bridge/handoff_packet.schema.json",
    "profiles/CSL_GOVERNED.yaml",
    "profiles/STANDALONE_LIGHT.yaml",
    "profiles/STANDALONE_COMMERCIAL.yaml",
    "profiles/RESEARCH_LIBRARY.yaml",
    "profiles/SANDBOX.yaml",
    "templates/common/README.template.md",
    "templates/common/gitignore.template",
    "registry/repos.yaml",
    "registry/projects.yaml",
    "queue/project_queue.yaml",
    "queue/blockers.yaml",
    "queue/escalations.yaml",
    "bridges/chatgpt/packet_builder.py",
    "bridges/codex/launch_prompt_builder.py",
    "bridges/claude/review_packet_builder.py",
    "bridges/github/github_packet_builder.py",
    "bridges/local_repo/local_operation_packet_builder.py",
    "src/ora/__init__.py",
    "src/ora/profiles/loader.py",
    "src/ora/profiles/validator.py",
    "src/ora/pge/bootstrap_plan.py",
    "src/ora/pge/scaffold_writer.py",
    "src/ora/pge/template_renderer.py",
    "src/ora/registry/repo_registry.py",
    "src/ora/queue/queue_manager.py",
    "src/ora/operations/operation_plan.py",
    "src/ora/operations/allowlist.py",
    "src/ora/operations/runner.py",
    "src/ora/validation/validator_orchestrator.py",
    "src/ora/validation/result_capture.py",
    "src/ora/bridges/chatgpt.py",
    "src/ora/bridges/codex.py",
    "src/ora/bridges/claude.py",
    "src/ora/bridges/github.py",
    "src/ora/bridges/local_repo.py",
    "schemas",
    "tools/ora_bootstrap_project.py",
    "tools/ora_register_repo.py",
    "tools/ora_run_validators.py",
    "tools/ora_update_queue.py",
    "tools/ora_generate_handoff_packet.py",
    "tools/validate_profiles.py",
    "tools/validate_registry.py",
    "tools/validate_queue.py",
    "tools/validate_operation_plan.py",
    "src",
    "tools/validate_memory.py",
    "tools/check_memory_integrity.py",
    "tools/validate_execution_records.py",
    "tools/check_working_tree_artifact_admission.py",
    "tools/ora_execute_bootstrap_plan.py",
    "validators/validate_ora_contract_stack.py",
    "validators/validate_fail_closed_boundaries.py",
    "tests/contract",
    "tests/fixtures",
    "tests/unit",
    "dashboard/README.md",
    "dashboard/future_placeholder.md",
    ".githooks/pre-commit",
    ".githooks/post-commit",
]

FORBIDDEN_PATHS = [
    "runtime",
]


def main() -> int:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    forbidden = [path for path in FORBIDDEN_PATHS if (ROOT / path).exists()]

    if missing or forbidden:
        if missing:
            print("missing required paths:", file=sys.stderr)
            for path in missing:
                print(f"  - {path}", file=sys.stderr)
        if forbidden:
            print("forbidden baseline paths present:", file=sys.stderr)
            for path in forbidden:
                print(f"  - {path}", file=sys.stderr)
        return 1

    print("repository layout validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
