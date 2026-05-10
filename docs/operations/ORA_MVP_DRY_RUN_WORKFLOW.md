# ORA MVP Dry-Run Workflow

## Purpose

This runbook documents the current safe end-to-end ORA MVP flow using only the commands and artifacts that already exist in this repository.

The workflow ends at:
- governed handoff packet generation
- validator orchestration plan generation

Default workflow execution still does not include validator execution, GitHub operations, queue state progression, or bridge dispatch. Validator execution is available only through the explicit single-validator entrypoint documented below.

## Current MVP Boundary

Current ORA MVP capabilities are limited to:
- project request intake from a local JSON or YAML file
- deterministic bootstrap plan generation
- scaffold writer dry-run artifact generation
- scaffold writer execution only with explicit local-write confirmation
- registry admission from a successful execution artifact
- queue admission for a known project and repo
- governed handoff packet generation
- validator execution plan generation by default
- explicit allowlisted single-validator execution with deterministic result artifact capture

Current ORA MVP does not provide:
- GitHub repository creation or GitHub bridge execution
- general validator execution orchestration
- queue state engine progression beyond initial admission
- bridge prompt dispatch
- unrestricted shell execution
- network execution
- deployment
- autonomous merge or push behavior
- self-modifying governance

`src/ora/operations/operation_plan.py` is still reserved for a later slice, so there is no general runtime operation planner in this MVP.

## Required Inputs

You need:
- a project request file
- a target local path that you are willing to write to only after explicit confirmation
- a clean understanding that registry and queue admission update tracked state in this repository

Example request file:
- `tests/fixtures/pge/requests/valid_csl_governed.yaml`

Example request shape:

```yaml
project_id: ora-slice-3-example
repo_name: ORA-Slice-3-Example
profile_id: CSL_GOVERNED
description: Example governed repo bootstrap request for dry-run planning.
target_owner: Levloc-Dev
local_path: /tmp/ora-slice-3-example
```

## Workflow

### 1. Create project request

Create a local request file in JSON or YAML. Example:

```bash
cat > /tmp/ora-mvp-request.yaml <<'EOF'
project_id: ora-mvp-example
repo_name: ORA-MVP-Example
profile_id: CSL_GOVERNED
description: Example ORA MVP dry-run request.
target_owner: Levloc-Dev
local_path: /tmp/ora-mvp-example
EOF
```

Purpose:
- defines the repo identity
- selects the project profile
- declares the local scaffold target

Required artifact:
- `/tmp/ora-mvp-request.yaml`

Fail-closed checkpoint:
- the request must satisfy the project request schema expected by `tools/ora_bootstrap_project.py`
- unknown `profile_id` stops the flow
- missing required keys such as `local_path` stop the flow

### 2. Generate bootstrap plan

Command:

```bash
python3 tools/ora_bootstrap_project.py /tmp/ora-mvp-request.yaml > /tmp/ora-mvp-bootstrap-plan.json
```

Purpose:
- converts the request into a deterministic bootstrap plan
- selects the allowed scaffold operations and validators for the chosen profile

Required artifact:
- `/tmp/ora-mvp-bootstrap-plan.json`

Expected artifact purpose:
- source of truth for scaffold writer dry-run and execution
- explicit list of planned operations, validators, and escalation requirement

Fail-closed checkpoint:
- command must exit successfully
- generated plan must contain only allowed operation types and `LOCAL_REPO_WRITE_ESCALATION`
- any request or schema failure stops the flow

### 3. Execute scaffold writer dry-run

Command:

```bash
python3 tools/ora_execute_bootstrap_plan.py --plan /tmp/ora-mvp-bootstrap-plan.json --target-root /tmp/ora-mvp-example > /tmp/ora-mvp-execution-dry-run.json
```

Purpose:
- validates the plan and stages the scaffold operation without writing files
- proves the target root and operation list are acceptable before any local write

Required artifact:
- `/tmp/ora-mvp-execution-dry-run.json`

Expected artifact purpose:
- dry-run execution record for human review
- confirms `dry_run: true` and per-operation `status: DRY_RUN`

Fail-closed checkpoint:
- target directory must remain unwritten in dry-run mode
- invalid plan content stops the flow
- dry-run output is review material only and cannot be used for registry admission

### 4. Execute scaffold writer with explicit local-write confirmation

Command:

```bash
python3 tools/ora_execute_bootstrap_plan.py --plan /tmp/ora-mvp-bootstrap-plan.json --target-root /tmp/ora-mvp-example --execute --confirm-local-write > /tmp/ora-mvp-execution-applied.json
```

Purpose:
- applies the approved scaffold plan to the explicit local target root

Required artifact:
- `/tmp/ora-mvp-execution-applied.json`

Expected artifact purpose:
- execution artifact for downstream registry admission
- records `dry_run: false`, `target_root`, `operation_count`, and per-operation applied status

Fail-closed checkpoint:
- `--execute` without `--confirm-local-write` is rejected
- writes are limited to the explicit `--target-root`
- invalid plan content stops the flow
- only a successful applied artifact can continue to registry admission

### 5. Register repo from execution artifact

Command:

```bash
python3 tools/ora_register_repo.py --request /tmp/ora-mvp-request.yaml --execution-result /tmp/ora-mvp-execution-applied.json > /tmp/ora-mvp-registry-admission.json
```

Purpose:
- admits the scaffolded repository into `registry/repos.yaml`
- admits the project into `registry/projects.yaml`

Required artifacts:
- `/tmp/ora-mvp-request.yaml`
- `/tmp/ora-mvp-execution-applied.json`
- `/tmp/ora-mvp-registry-admission.json`

Expected artifact purpose:
- admission result proving whether registry writes were accepted

Expected state updates on success:
- `registry/repos.yaml`
- `registry/projects.yaml`

Fail-closed checkpoint:
- dry-run artifacts are rejected because admission requires `dry_run: false`
- `execution_result.target_root` must equal `request.local_path`
- `execution_result.project_profile` must equal `request.profile_id`
- `execution_result.project_name` must equal `request.repo_name`
- every execution operation status must be `APPLIED` or `ALREADY_PRESENT`
- duplicate `repo_id` or `project_id` stops the flow
- malformed registry files stop the flow without partial writes

### 6. Admit project to queue

Command:

```bash
python3 tools/ora_update_queue.py admit --project-id ora-mvp-example --profile-id CSL_GOVERNED > /tmp/ora-mvp-queue-admission.json
```

Purpose:
- creates the initial deterministic queue entry for the admitted project

Required artifact:
- `/tmp/ora-mvp-queue-admission.json`

Expected artifact purpose:
- admission result for the initial queue item

Expected state update on success:
- `queue/project_queue.yaml`

Expected queue item:
- `status: READY_FOR_FIRST_GOVERNED_SLICE`
- `current_slice: null`
- `blocker: null`
- `escalation_required: true`

Fail-closed checkpoint:
- project must already exist in `registry/projects.yaml`
- repo must already exist in `registry/repos.yaml`
- duplicate queue admission for the same `project_id` is rejected
- malformed queue state stops the flow

### 7. Generate handoff packet

Command:

```bash
python3 tools/ora_generate_handoff_packet.py --project-id ora-mvp-example --bridge-type CODEX > /tmp/ora-mvp-codex-handoff.json
```

Purpose:
- generates a deterministic governed handoff packet for a supported bridge
- prepares a reviewable artifact without dispatching anything

Required artifact:
- `/tmp/ora-mvp-codex-handoff.json`

Expected artifact purpose:
- review packet for a governed external handoff
- carries validation command list and authority boundary

Supported bridge values:
- `CHATGPT`
- `CLAUDE`
- `CODEX`

Fail-closed checkpoint:
- project must already exist in `registry/projects.yaml`
- project must already exist in `queue/project_queue.yaml`
- repo must already exist in `registry/repos.yaml`
- queue and repo profile data must match
- unsupported bridge types are rejected
- packet generation does not dispatch prompts and does not update queue state

### 8. Generate validator orchestration plan

Command:

```bash
python3 tools/ora_run_validators.py --project-id ora-mvp-example > /tmp/ora-mvp-validator-plan.json
```

Purpose:
- generates a deterministic validator execution plan without running validators

Required artifact:
- `/tmp/ora-mvp-validator-plan.json`

Expected artifact purpose:
- reviewable plan-only validator artifact
- lists validators chosen from the admitted profile
- proves that the default orchestration path remains plan-only in this MVP

Fail-closed checkpoint:
- project must already exist in `registry/projects.yaml`
- project must already exist in `queue/project_queue.yaml`
- repo must already exist in `registry/repos.yaml`
- queue `profile_id` must match repo `project_profile`
- repo `validator_set` must match the deterministic profile validator selection
- the returned plan must keep `execution_mode: PLAN_ONLY`

### 8.1 Explicit single-validator execution

Command:

```bash
python3 tools/ora_execute_validator.py --project-id ora-mvp-example --validator-id tools/validate_repo_layout.py > /tmp/ora-mvp-validator-result.json
```

Purpose:
- runs one explicitly declared validator from the admitted allowlist
- writes a deterministic result artifact to `governance/workflows/validation_reports/`

Fail-closed checkpoint:
- unknown validator ids are rejected
- undeclared validator execution requests are rejected
- missing validator commands are rejected
- non-zero validator exit codes return failure artifacts and stop continuation
- malformed validator result output returns error artifacts and stop continuation

## Artifact Summary

Artifacts produced by the documented flow:
- project request file: input request that defines project identity, profile, and local path
- bootstrap plan JSON: deterministic scaffold plan derived from the request
- dry-run execution artifact JSON: no-write proof artifact for human review
- applied execution artifact JSON: successful local-write record used for registry admission
- registry admission result JSON: result of repo and project registry update attempt
- queue admission result JSON: result of initial queue item creation
- handoff packet JSON: governed bridge handoff artifact for review only
- validator plan JSON: plan-only validator orchestration artifact
- validator result JSON: explicit single-validator execution artifact

Tracked repository state updated by the flow:
- `registry/repos.yaml`
- `registry/projects.yaml`
- `queue/project_queue.yaml`

## Fail-Closed Checkpoints

Do not continue past a step if any of the following occur:
- request schema validation fails
- profile resolution fails
- bootstrap plan generation fails
- scaffold dry-run fails
- scaffold execution is attempted without `--confirm-local-write`
- applied execution artifact does not report `dry_run: false`
- request metadata and execution artifact metadata do not match
- registry files or queue files are malformed
- duplicate registry or queue identifiers are detected
- handoff packet generation fails
- validator plan generation fails
- explicit validator execution fails

Each failure is a stop condition. The next step must not be run until the failing artifact or repository state is corrected.

## Explicit Prohibited Actions

The current MVP workflow must not be used to:
- run validators from the generated validator plan or through any undeclared execution surface
- create, mutate, or synchronize GitHub repositories
- dispatch bridge prompts to ChatGPT, Claude, Codex, or any other bridge target
- perform queue progression beyond initial queue admission
- update queue blockers or escalations as an execution engine
- perform arbitrary subprocess execution
- use unrestricted shell execution
- use network access as part of the workflow
- deploy anything
- autonomously merge or push changes
- self-modify governance documents or governance policy as part of workflow execution

## Recommended Validation After Documentation Changes

Run:

```bash
python3 tools/validate_profiles.py
python3 tools/validate_registry.py
python3 tools/validate_queue.py
python3 tools/validate_operation_plan.py
python3 tools/validate_handoff_packets.py
python3 validators/validate_ora_contract_stack.py
python3 validators/validate_fail_closed_boundaries.py
pytest -q
```
