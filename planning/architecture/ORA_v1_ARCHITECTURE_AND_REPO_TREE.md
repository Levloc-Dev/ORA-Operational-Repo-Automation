# ORA v1 Architecture and Repository Tree Recommendation

## Status

Governed v1 architecture with early MVP slices implemented and reconciled.

## Source Context

This design is derived from `ORA_SOURCE_CONTEXT_v1.0.0.md`, which defines ORA as a governed operational automation layer for removing the human transport bottleneck from multi-project AI-assisted software development while preserving fail-closed governance and human constitutional authority.

## Core Recommendation

ORA v1 is being implemented as a narrow, deterministic operational automation platform, not as a broad autonomous agent.

The current implemented MVP surface in this repository includes:

1. project profiles
2. repo bootstrap automation through PGE
3. repo registry
4. direct file-writing workflows
5. validator orchestration
6. project queue tracking through initial governed admission only
7. execution handoff packets for ChatGPT, Codex, and Claude

The following areas remain intentionally unimplemented in the current repo state:
- validator execution
- GitHub repo creation or bridge execution
- Dev/Main sync execution
- dashboard implementation
- unrestricted runtime activation

ORA v1 should explicitly exclude unrestricted shell execution, autonomous deployment, autonomous merges, recursive self-modification, and unrestricted runtime authority.

---

# 1. Architectural Position

Recommended ecosystem layering:

```text
CSL
└── Constitutional authority and governance doctrine

ORP
└── Governance routing, policy interpretation, and authority checks

ORA
└── Operational automation, repo workflow execution, queue tracking, and handoff transport

PGE
└── ORA subsystem for project/repo birth automation

Target Repositories
└── CSL, ORP, TOS, WIO, PAL, CPT, standalone projects, research projects, commercial projects
```

ORA should not decide what is constitutionally allowed. ORA should execute only bounded operational actions that have passed profile, policy, capability, and validation checks.

---

# 2. ORA v1 Boundary

## 2.1 ORA may do

- create project scaffolds from declared profiles
- create repo-local file structures
- generate prompt packets
- write deterministic files from templates
- run declared validators
- prepare commits
- track project state
- track current slice status
- prepare GitHub Dev/Main sync operations
- emit escalation packets when authority is missing

## 2.2 ORA must not do in v1

- autonomously merge branches
- deploy to production
- execute arbitrary shell commands outside a declared allowlist
- self-modify its own governance rules
- bypass ORP or CSL governance
- infer missing approval from model judgment
- silently continue after validation failure

---

# 3. Recommended v1 Subsystems

## 3.1 Profile Registry

Purpose: declare allowed project types and their operational scaffolds.

Initial profiles:

```text
CSL_GOVERNED
STANDALONE_LIGHT
STANDALONE_COMMERCIAL
RESEARCH_LIBRARY
SANDBOX
```

Each profile should declare:

- required directories
- optional directories
- required governance artifacts
- required validators
- branch strategy
- repo sync mode
- initial files
- prohibited actions
- escalation triggers

## 3.2 PGE — Project Genesis Engine

Purpose: repo birth automation.

PGE should be the first real implementation target.

PGE v1 should support:

- local repo scaffold generation
- GitHub repo creation packet generation
- Levloc-Dev / Levloc-Main replication plan generation
- initial README generation
- profile-specific governance scaffold
- initial branch plan
- initial validator plan
- initial project queue registration

PGE v1 should not immediately attempt fully autonomous GitHub execution unless the CLI/API credentials and account boundaries are explicitly configured and validated.

## 3.3 Repo Registry

Purpose: maintain machine-readable repo metadata.

Recommended file:

```text
registry/repos.yaml
```

Each repo entry should include:

- repo_id
- repo_name
- project_profile
- local_path
- github_dev_remote
- github_main_remote
- default_branch
- active_branch
- governance_mode
- validator_set
- sync_mode
- current_queue_item
- last_known_status

## 3.4 Operational Runner

Purpose: execute declared operational tasks using deterministic scripts.

ORA v1 runner should use a strict allowlist.

Allowed initial operation types:

```text
WRITE_FILE
CREATE_DIRECTORY
APPLY_TEMPLATE
RUN_VALIDATOR
PREPARE_COMMIT
GENERATE_HANDOFF_PACKET
REGISTER_QUEUE_ITEM
UPDATE_QUEUE_ITEM
```

Excluded operation types:

```text
ARBITRARY_SHELL
DEPLOY
MERGE
DELETE_REMOTE
MODIFY_GOVERNANCE_AUTHORITY
```

## 3.5 Validator Orchestrator

Purpose: run repo-specific validators in the correct order and capture results.

Validator execution should be declared in profile YAML, not inferred by the model.

Each validator result should capture:

- command
- exit_code
- stdout_hash
- stderr_hash
- duration_ms
- working_directory
- timestamp
- result_status

## 3.6 Queue Manager

Purpose: track the operational state of concurrent projects.

Queue states should be closed-set:

```text
PROPOSED
READY_FOR_BOOTSTRAP
BOOTSTRAPPING
READY_FOR_SLICE
IN_SLICE
VALIDATING
BLOCKED
ESCALATION_REQUIRED
READY_FOR_COMMIT
READY_FOR_SYNC
COMPLETE
ARCHIVED
```

The queue should answer:

- what is currently active?
- what is blocked?
- what needs human decision?
- what can proceed deterministically?
- what has failed validation?
- what is the next recommended action?

## 3.7 Execution Bridges

Purpose: move work packets between systems without making ORA a freeform agent.

Initial bridge pattern:

```text
ORA generates packet → human or tool executes packet → result is pasted/imported → ORA records state → validators run → queue updates
```

Recommended bridge categories:

- ChatGPT context/source packets
- Codex launch prompts
- Claude review prompts
- GitHub operation packets
- local repo operation packets
- validator result import packets

Bridges should be packet-based before they are API-based.

---

# 4. Recommended Repository Tree

```text
ORA-Operational-Repo-Automation/
├── README.md
├── pyproject.toml
├── .gitignore
├── .githooks/
│   ├── pre-commit
│   └── post-commit
│
├── governance/
│   ├── constitution/
│   │   └── AI_CONSTITUTION.md
│   ├── control_plane/
│   │   └── DECISION_GATE.md
│   ├── workflows/
│   │   ├── governed_specs/
│   │   ├── validation_reports/
│   │   └── implementation_prompts/
│   └── policies/
│       ├── ORA_CAPABILITY_BOUNDARY.md
│       └── ORA_FAIL_CLOSED_POLICY.md
│
├── memory/
│   ├── evolution/
│   │   ├── decisions/
│   │   └── executions/
│   └── indexes/
│       └── decision_index.yaml
│
├── planning/
│   ├── seeds/
│   ├── prompts/
│   ├── implementation_prompts/
│   └── architecture/
│       └── ORA_v1_ARCHITECTURE_AND_REPO_TREE.md
│
├── docs/
│   ├── architecture/
│   │   ├── ORA_SYSTEM_OVERVIEW.md
│   │   ├── ORA_SUBSYSTEM_BOUNDARIES.md
│   │   └── snapshots/
│   ├── contracts/
│   └── operations/
│
├── schemas/
│   ├── profile/
│   │   └── project_profile.schema.json
│   ├── pge/
│   │   └── repo_bootstrap_plan.schema.json
│   ├── registry/
│   │   └── repo_registry.schema.json
│   ├── queue/
│   │   └── queue_item.schema.json
│   ├── operation/
│   │   └── operation_plan.schema.json
│   ├── validation/
│   │   └── validator_result.schema.json
│   └── bridge/
│       └── handoff_packet.schema.json
│
├── profiles/
│   ├── CSL_GOVERNED.yaml
│   ├── STANDALONE_LIGHT.yaml
│   ├── STANDALONE_COMMERCIAL.yaml
│   ├── RESEARCH_LIBRARY.yaml
│   └── SANDBOX.yaml
│
├── templates/
│   ├── common/
│   │   ├── README.template.md
│   │   └── gitignore.template
│   ├── csl_governed/
│   ├── standalone_light/
│   ├── standalone_commercial/
│   ├── research_library/
│   └── sandbox/
│
├── registry/
│   ├── repos.yaml
│   └── projects.yaml
│
├── queue/
│   ├── project_queue.yaml
│   ├── blockers.yaml
│   └── escalations.yaml
│
├── bridges/
│   ├── chatgpt/
│   │   └── packet_builder.py
│   ├── codex/
│   │   └── launch_prompt_builder.py
│   ├── claude/
│   │   └── review_packet_builder.py
│   ├── github/
│   │   └── github_packet_builder.py
│   └── local_repo/
│       └── local_operation_packet_builder.py
│
├── src/
│   └── ora/
│       ├── __init__.py
│       ├── profiles/
│       │   ├── loader.py
│       │   └── validator.py
│       ├── pge/
│       │   ├── bootstrap_plan.py
│       │   ├── scaffold_writer.py
│       │   └── template_renderer.py
│       ├── registry/
│       │   └── repo_registry.py
│       ├── queue/
│       │   └── queue_manager.py
│       ├── operations/
│       │   ├── operation_plan.py
│       │   ├── allowlist.py
│       │   └── runner.py
│       ├── validation/
│       │   ├── validator_orchestrator.py
│       │   └── result_capture.py
│       └── bridges/
│           ├── chatgpt.py
│           ├── codex.py
│           ├── claude.py
│           ├── github.py
│           └── local_repo.py
│
├── tools/
│   ├── ora_bootstrap_project.py
│   ├── ora_register_repo.py
│   ├── ora_run_validators.py
│   ├── ora_update_queue.py
│   ├── ora_generate_handoff_packet.py
│   ├── validate_profiles.py
│   ├── validate_registry.py
│   ├── validate_queue.py
│   └── validate_operation_plan.py
│
├── validators/
│   ├── validate_ora_contract_stack.py
│   └── validate_fail_closed_boundaries.py
│
├── tests/
│   ├── contract/
│   ├── unit/
│   └── fixtures/
│
└── dashboard/
    ├── README.md
    └── future_placeholder.md
```

---

# 5. MVP Implementation Order

## Slice 1 — Static architecture and governed scaffold

Create the repo tree, source context, README, architecture file, profile files, and basic schemas. No runtime execution.

## Slice 2 — Profile validation

Implement schema validation for project profiles.

## Slice 3 — PGE bootstrap plan generation

Generate a repo bootstrap plan from a selected profile and project metadata. No repo creation yet.

## Slice 4 — Local scaffold writer

Write directories and files into a local target path from a validated bootstrap plan.

## Slice 5 — Repo registry

Register scaffolded repos in `registry/repos.yaml`.

## Slice 6 — Queue manager

Implemented for deterministic initial governed admission only. The canonical queue item shape is:
- `project_id`
- `repo_id`
- `profile_id`
- `status: READY_FOR_FIRST_GOVERNED_SLICE`
- `current_slice: null`
- `blocker: null`
- `escalation_required: true`

## Slice 7 — Validator runner

Implemented as deterministic validator plan generation only. Validator selection is sourced from the declared profile YAML and must match `registry/repos.yaml.validator_set`. There is still no general validator execution engine in this repo.

## Slice 8 — Handoff packet builders

Implemented for governed ChatGPT, Codex, and Claude packet generation only. No bridge dispatch or execution is present.

## Slice 9 — Dev/Main sync packet generation

Generate sync packets and command plans. Do not execute destructive Git operations by default.

## Slice 10 — Dashboard placeholder

Add read-only queue/status dashboard only after the underlying YAML model is stable.

---

# 6. Over-Engineering Guardrails

ORA v1 should avoid:

- database-first design
- event bus architecture
- distributed workers
- agent swarms
- model-directed execution policies
- premature Rust service implementation
- dashboard-first implementation
- fully autonomous GitHub mutation
- self-modifying governance

Use filesystem + YAML first.

Use Python scripts first.

Add Rust only when concurrency, daemon reliability, or long-running orchestration becomes a real bottleneck.

Add SQLite only when YAML registry and queue files become insufficient.

---

# 7. Recommended Exact Placement

Place this file at:

```text
planning/architecture/ORA_v1_ARCHITECTURE_AND_REPO_TREE.md
```

Also copy or reference it from:

```text
docs/architecture/ORA_SYSTEM_OVERVIEW.md
```

The implementation prompt derived from this file should be placed at:

```text
planning/implementation_prompts/ORA_CODEX_CREATE_V1_REPO_SCAFFOLD_PROMPT.md
```

---

# 8. Final Recommendation

Build ORA v1 around PGE, profile validation, local deterministic scaffolding, repo registry, project queue tracking, and packet-based bridges.

Do not begin with a broad autonomous runtime.

The most valuable first milestone is a tool that can reliably create a new governed or standalone repo scaffold, register it, generate the correct handoff packets, and tell the operator exactly what is blocked, ready, or invalid.
