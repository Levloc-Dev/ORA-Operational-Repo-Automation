# ORA Governed Architecture Review — CSL Canonical Repo Bootstrap Template

## Document Status

- **Project:** ORA — Operational Repo Automation
- **Review Target:** CSL Standard Repo Template v1.0.0
- **Output Type:** Governed architecture review and refined bootstrap recommendation
- **Recommended Placement:** `governance/workflows/governed_specs/ORA_CSL_CANONICAL_REPO_TEMPLATE_REVIEW.md`
- **Status:** Proposed baseline review for incremental implementation
- **Decision Posture:** Narrow, fail-closed, deterministic, profile-ready

---

# 1. Executive Summary

The proposed CSL Standard Repo Template is directionally sound and should become the first canonical governed repo bootstrap baseline for CSL ecosystem projects.

However, the initial template should be refined before automation by separating:

1. **Canonical baseline assets** that every governed repo should receive.
2. **Profile-specific overlays** that vary by project type.
3. **ORA/PGE automation logic** that must not be embedded inside generated repos.
4. **Future orchestration concepts** that are not yet stable enough to encode as mandatory structure.

The central recommendation is:

> Treat the CSL Standard Repo Template as a narrow, deterministic, file-system bootstrap genome, not as a full runtime architecture.

The template should install governance scaffolding, memory paths, deterministic validator hooks, planning paths, docs/contracts paths, test scaffolds, and repo metadata. It should not yet install advanced queue systems, runtime bridges, dashboard components, economic governance, autonomous execution, or multi-agent orchestration.

---

# 2. Review of Proposed Canonical Repo Structure

The proposed structure is strong because it reflects stable patterns already used across CSL-adjacent projects:

```text
PROJECT-NAME/
├── governance/
├── memory/
├── planning/
├── docs/
├── schemas/
├── src/
├── tools/
├── tests/
├── .githooks/
├── .github/
├── README.md
├── PROJECT_CONTEXT.md
├── CHANGELOG.md
└── pyproject.toml
```

The structure is suitable as a baseline, but some folders should be made **mandatory**, some **conditional**, and some **profile-driven**.

The most important refinement is to avoid allowing the standard template to become a dumping ground for every current or future CSL/ORA concept.

---

# 3. Stable Components

The following components are stable enough to include in the canonical template.

## 3.1 Governance Scaffold

Stable:

```text
governance/
├── constitution/
├── control_plane/
├── workflows/
│   ├── governed_specs/
│   └── validation_reports/
└── reviews/
```

Rationale:

- This matches existing CSL governance-first practice.
- It supports constitutional authority, decision gates, governed specs, validation reports, and review packets.
- It preserves separation between governance records and runtime source code.

Recommended refinement:

Add placeholder `.gitkeep` files or README files in empty folders so the structure is preserved by Git.

## 3.2 Memory Structure

Stable:

```text
memory/
├── evolution/
│   ├── decisions/
│   ├── executions/
│   └── quarantine/
└── indexes/
    └── decision_index.yaml
```

Rationale:

- DEC/EXE structure is already a recurring CSL pattern.
- Quarantine support is valuable because memory artifacts can become malformed, duplicated, or untracked.
- The canonical decision index should be present from repo birth.

Recommended refinement:

Bootstrap should create:

```text
memory/indexes/decision_index.yaml
memory/evolution/decisions/.gitkeep
memory/evolution/executions/.gitkeep
memory/evolution/quarantine/.gitkeep
```

Do not create fake DEC/EXE records unless a bootstrap governance decision is explicitly required.

## 3.3 Planning Structure

Stable:

```text
planning/
├── seeds/
├── prompts/
└── implementation_prompts/
```

Rationale:

- The user’s workflow repeatedly distinguishes seeds, general prompts, and implementation prompts.
- This supports Codex/Claude handoffs without mixing planning artifacts into governance or source code.

Recommended refinement:

Keep all three folders. Do not add more planning subfolders until specific recurring need is proven.

## 3.4 Docs and Contracts

Stable:

```text
docs/
├── architecture/
│   └── snapshots/
└── contracts/
```

Rationale:

- Architecture snapshots are a proven convention.
- Contracts are stable and useful across governance-first projects.

Recommended refinement:

Add:

```text
docs/architecture/README.md
docs/contracts/README.md
docs/architecture/snapshots/.gitkeep
```

## 3.5 Schemas

Stable:

```text
schemas/
```

Rationale:

- Closed schemas are a stable mechanism for deterministic enforcement.
- The folder should exist even if initially sparse.

Recommended refinement:

Do not create many schema subfolders yet. Allow projects to add domain-specific schema namespaces later.

## 3.6 Tools

Stable:

```text
tools/
```

Baseline validator scripts are stable enough to include:

```text
tools/validate_memory.py
tools/check_memory_integrity.py
tools/validate_execution_records.py
tools/check_working_tree_artifact_admission.py
```

Recommended refinement:

Provide these as minimal deterministic stubs first if the canonical implementations are not ready for all repos.

## 3.7 Tests

Stable:

```text
tests/
├── contract/
└── unit/
```

Rationale:

- Contract tests and unit tests are now recurring across CSL/WIO-style projects.
- Keeping them separate prevents schema/contract validation from being blurred with runtime unit testing.

Recommended refinement:

Add one smoke test for repository layout validation only.

## 3.8 Git Hooks

Stable but must be constrained:

```text
.githooks/
├── pre-commit
└── post-commit
```

Recommended behavior:

- `pre-commit`: run validators only.
- `post-commit`: optionally refresh snapshots, but must not auto-amend commits.
- Hooks must avoid hidden mutation.

## 3.9 GitHub Workflows

Stable as a path, not necessarily as active CI:

```text
.github/
└── workflows/
```

Recommended refinement:

For v1, include either:

1. no workflow file, only `.gitkeep`, or
2. a minimal validation workflow that runs deterministic checks only.

Do not include release, deployment, or multi-repo sync workflows in the baseline.

## 3.10 Repo Metadata

Stable:

```text
README.md
PROJECT_CONTEXT.md
CHANGELOG.md
pyproject.toml
```

Recommended refinement:

Add:

```text
.gitignore
```

This is a missing mandatory baseline file.

---

# 4. Unstable Assumptions

The following assumptions should not be treated as mandatory template behavior yet.

## 4.1 Every Project Needs Full Dev/Main Replication

Dev/Main replication is important for CSL-governed projects, but not every repo profile requires it.

Recommendation:

- Make Dev/Main replication mandatory only for `CSL_GOVERNED`.
- Make it optional for `STANDALONE_COMMERCIAL`.
- Exclude it from `STANDALONE_LIGHT`, `RESEARCH_LIBRARY`, and `SANDBOX` unless explicitly enabled.

## 4.2 Every Project Needs Strict Branch Topology

The branch set:

```text
main
develop
feature/*
review/*
hotfix/*
```

is reasonable, but may be too much for light or sandbox projects.

Recommendation:

- `main` is mandatory for all profiles.
- `develop` is default for governed and commercial projects.
- `review/*` is governed-only by default.
- `hotfix/*` is commercial/governed only.
- `feature/*` is optional but recommended.

## 4.3 All Repos Need Identical Validators

Validator paths are stable, but validator strictness should vary by profile.

Recommendation:

Bootstrap installs validator framework consistently, but profile manifests determine which validators are required, advisory, or disabled.

## 4.4 ORA Runtime Structure Belongs in Every Repo

Folders such as:

```text
runtime/
bridges/
queue/
dashboard/
templates/
profiles/
```

belong in the ORA repo itself, not in every generated project.

Recommendation:

Do not include these folders in the canonical generated repo template unless the target repo is ORA itself or a project with that specific role.

## 4.5 Economic Governance Belongs in the Bootstrap Baseline

Economic governance may become important, especially for API usage and TOS integration, but it is not a mandatory repo-birth component.

Recommendation:

Keep economic governance outside the v1 canonical repo template.

## 4.6 Autonomous Execution Should Be Encoded Early

Any structure implying self-authorising runtime execution is premature.

Recommendation:

Bootstrap may create directories for validators and tools, but must not create autonomous execution loops, background agents, or unrestricted shell bridges.

---

# 5. Missing Mandatory Baseline Components

The proposed template should add the following minimal mandatory components.

## 5.1 `.gitignore`

Required for all repos.

Baseline should exclude:

```text
__pycache__/
.pytest_cache/
.venv/
.env
.DS_Store
*.pyc
dist/
build/
```

## 5.2 `LICENSE` or License Placeholder

Recommendation:

- For private/internal CSL repos: `LICENSE_POLICY.md` or `LICENSE_PENDING.md`.
- For public/commercial repos: profile must require explicit license selection.

Do not silently choose a license.

## 5.3 `bootstrap_manifest.yaml`

Required for ORA/PGE compatibility.

Recommended path:

```text
.bootstrap/bootstrap_manifest.yaml
```

or:

```text
repo_bootstrap.yaml
```

Recommendation:

Use `.bootstrap/bootstrap_manifest.yaml` to avoid cluttering the repo root while keeping bootstrap state explicit.

## 5.4 Template Provenance File

Recommended path:

```text
.bootstrap/template_provenance.yaml
```

Purpose:

- template name
- template version
- profile used
- generation timestamp
- generating system
- checksum of manifest
- bootstrap mode

## 5.5 Layout Validator

Recommended path:

```text
tools/validate_repo_layout.py
```

Purpose:

- verify mandatory folders/files exist
- verify forbidden baseline folders are absent
- verify profile-specific paths
- fail closed on missing mandatory structure

This should be the first validator PGE can rely on.

## 5.6 Source Context Policy File

Recommended path:

```text
PROJECT_CONTEXT.md
```

Already included, but should be treated as mandatory.

Purpose:

- project identity
- governance posture
- profile
- allowed automation boundaries
- source-of-truth notes
- human authority statement

## 5.7 Empty Directory Preservation

Every mandatory empty directory needs either:

```text
.gitkeep
```

or a local README explaining purpose.

Recommendation:

Use README files for semantically important folders and `.gitkeep` for purely structural placeholders.

---

# 6. Premature Abstractions

The following should not be included in the v1 canonical generated repo template.

## 6.1 Universal `orchestration/` Folder

Reason:

- Orchestration is not required for every project.
- ORP handles governance orchestration.
- ORA handles operational automation.
- Generated repos should not imply they orchestrate themselves.

Recommendation:

Do not include `orchestration/` in the baseline.

## 6.2 Universal `automation/` Folder

Reason:

- Too broad and likely to become a dumping ground.
- Operational automation should be implemented by ORA/PGE, not copied into every repo.

Recommendation:

Use `tools/` for deterministic repo-local scripts only.

## 6.3 Universal `execution/` Folder

Reason:

- Runtime execution patterns are project-specific.
- WIO-style execution models should not be forced into all repos.

Recommendation:

Only include `src/` and let project profiles add execution structure where justified.

## 6.4 Universal `agents/` Folder

Reason:

- Encourages model-driven agency inside repos before governance boundaries are mature.
- Confuses agent prompts, scripts, and runtime authority.

Recommendation:

Use `planning/prompts/` and `governance/reviews/` for handoff artifacts. Do not add `agents/` yet.

## 6.5 Universal Dashboard/UI Folders

Reason:

- Not all repos need UI.
- Dashboard belongs to ORA or product repos, not the baseline.

Recommendation:

Exclude `dashboard/`, `ui/`, `frontend/`, and similar folders from baseline.

## 6.6 Advanced Profile Taxonomy

The proposed profiles are useful, but v1 should not overfit them.

Recommendation:

Start with three operational profiles:

```text
CSL_GOVERNED
STANDALONE_LIGHT
SANDBOX
```

Hold these as reserved but not fully implemented yet:

```text
STANDALONE_COMMERCIAL
RESEARCH_LIBRARY
```

---

# 7. Recommended Minimal Viable Canonical Repo Template

## 7.1 Refined Baseline Tree

```text
PROJECT-NAME/
├── .bootstrap/
│   ├── bootstrap_manifest.yaml
│   └── template_provenance.yaml
│
├── governance/
│   ├── constitution/
│   │   └── README.md
│   ├── control_plane/
│   │   └── README.md
│   ├── workflows/
│   │   ├── governed_specs/
│   │   │   └── README.md
│   │   └── validation_reports/
│   │       └── README.md
│   └── reviews/
│       └── README.md
│
├── memory/
│   ├── evolution/
│   │   ├── decisions/
│   │   │   └── .gitkeep
│   │   ├── executions/
│   │   │   └── .gitkeep
│   │   └── quarantine/
│   │       └── .gitkeep
│   └── indexes/
│       └── decision_index.yaml
│
├── planning/
│   ├── seeds/
│   │   └── README.md
│   ├── prompts/
│   │   └── README.md
│   └── implementation_prompts/
│       └── README.md
│
├── docs/
│   ├── architecture/
│   │   ├── README.md
│   │   └── snapshots/
│   │       └── .gitkeep
│   └── contracts/
│       └── README.md
│
├── schemas/
│   └── README.md
│
├── src/
│   └── README.md
│
├── tools/
│   ├── validate_repo_layout.py
│   ├── validate_memory.py
│   ├── check_memory_integrity.py
│   ├── validate_execution_records.py
│   └── check_working_tree_artifact_admission.py
│
├── tests/
│   ├── contract/
│   │   └── test_repo_layout.py
│   └── unit/
│       └── .gitkeep
│
├── .githooks/
│   ├── pre-commit
│   └── post-commit
│
├── .github/
│   └── workflows/
│       └── .gitkeep
│
├── .gitignore
├── README.md
├── PROJECT_CONTEXT.md
├── CHANGELOG.md
├── LICENSE_PENDING.md
└── pyproject.toml
```

## 7.2 Minimum Root Files

```text
README.md
PROJECT_CONTEXT.md
CHANGELOG.md
LICENSE_PENDING.md
.gitignore
pyproject.toml
```

## 7.3 Minimum Bootstrap Files

```text
.bootstrap/bootstrap_manifest.yaml
.bootstrap/template_provenance.yaml
```

## 7.4 Minimum Validator Files

```text
tools/validate_repo_layout.py
tools/validate_memory.py
tools/check_memory_integrity.py
tools/validate_execution_records.py
tools/check_working_tree_artifact_admission.py
```

## 7.5 Minimum Tests

```text
tests/contract/test_repo_layout.py
```

---

# 8. Profile Inheritance Strategy

## 8.1 Principle

Profiles should be overlays on top of a small canonical baseline.

Do not create separate full templates for every profile at the start.

Recommended model:

```text
BASELINE
├── CSL_GOVERNED
├── STANDALONE_LIGHT
└── SANDBOX
```

Reserved future overlays:

```text
STANDALONE_COMMERCIAL
RESEARCH_LIBRARY
```

## 8.2 Baseline Profile

All repos receive:

- root metadata
- `.bootstrap/`
- `README.md`
- `PROJECT_CONTEXT.md`
- `.gitignore`
- `CHANGELOG.md`
- `LICENSE_PENDING.md`
- `pyproject.toml`
- `src/`
- `tools/`
- `tests/`
- `docs/`
- `schemas/`

## 8.3 CSL_GOVERNED Overlay

Adds or enforces:

- full `governance/`
- full `memory/`
- DEC/EXE paths
- decision index
- quarantine
- validation reports
- governed specs
- strict validators
- pre-commit validation
- post-commit snapshot refresh without auto-amend
- Dev/Main replication manifest fields
- strict branch policy
- initial governance source context

## 8.4 STANDALONE_LIGHT Overlay

Adds or enforces:

- README
- basic `src/`
- basic `tests/`
- optional `docs/`
- optional `planning/`
- no mandatory DEC/EXE unless opted in
- no Dev/Main replication by default
- simple branch policy

## 8.5 SANDBOX Overlay

Adds or enforces:

- minimal README
- `src/`
- optional `tests/`
- no governance memory
- no strict hooks
- no replication
- explicit disposable status in manifest

## 8.6 Reserved Future: STANDALONE_COMMERCIAL

Likely additions later:

- product roadmap
- release notes
- license policy
- packaging workflow
- commercial docs
- support policy

Do not implement fully yet.

## 8.7 Reserved Future: RESEARCH_LIBRARY

Likely additions later:

- source ingestion paths
- bibliographic metadata
- provenance records
- synthesis reports

Do not implement fully yet.

---

# 9. Bootstrap Manifest Structure

Recommended path:

```text
.bootstrap/bootstrap_manifest.yaml
```

## 9.1 Purpose

The bootstrap manifest is the deterministic declaration of repo birth intent.

It should be read by ORA/PGE and repo-local validators.

It should not be a runtime authority file.

## 9.2 Recommended Minimal Schema

```yaml
manifest_version: "1.0.0"

project:
  name: "PROJECT-NAME"
  slug: "PROJECT-NAME"
  description: ""
  profile: "CSL_GOVERNED"
  status: "bootstrap"

template:
  name: "CSL_STANDARD_REPO_TEMPLATE"
  version: "1.0.0"
  source_document: "CSL_STANDARD_REPO_TEMPLATE_v1.0.0.md"

governance:
  enabled: true
  authority_model: "HUMAN_CONSTITUTIONAL_AUTHORITY"
  fail_closed: true
  decision_records: true
  execution_records: true
  quarantine_enabled: true

validation:
  required_validators:
    - "tools/validate_repo_layout.py"
    - "tools/validate_memory.py"
    - "tools/check_memory_integrity.py"
    - "tools/validate_execution_records.py"
    - "tools/check_working_tree_artifact_admission.py"
  advisory_validators: []
  disabled_validators: []

git:
  default_branch: "main"
  development_branch: "develop"
  branch_policy:
    allowed_patterns:
      - "main"
      - "develop"
      - "feature/*"
      - "review/*"
      - "hotfix/*"

hooks:
  install_pre_commit: true
  install_post_commit: true
  hidden_mutation_allowed: false
  post_commit_auto_amend_allowed: false

snapshots:
  enabled: true
  path: "docs/architecture/snapshots"
  self_inclusion_guard: true
  commit_separately_recommended: true

replication:
  enabled: true
  mode: "DECLARED_ONLY"
  source_account: "Levloc-Dev"
  target_account: "Levloc-Main"
  silent_divergence_allowed: false

ora_pge:
  generated_by: "PGE"
  bootstrap_mode: "deterministic_scaffold"
  may_create_repo: true
  may_write_files: true
  may_install_hooks: true
  may_run_validators: true
  may_commit_initial_scaffold: true
  may_push_remote: false
  may_merge: false
  may_deploy: false
  may_execute_unrestricted_shell: false

provenance:
  created_at_utc: null
  created_by: null
  template_checksum: null
  manifest_checksum: null
```

## 9.3 Closed Profile Enum

Initial closed set:

```yaml
allowed_profiles:
  - CSL_GOVERNED
  - STANDALONE_LIGHT
  - SANDBOX
```

Reserved but not active:

```yaml
reserved_profiles:
  - STANDALONE_COMMERCIAL
  - RESEARCH_LIBRARY
```

---

# 10. Template Provenance Structure

Recommended path:

```text
.bootstrap/template_provenance.yaml
```

Recommended content:

```yaml
provenance_version: "1.0.0"
template_name: "CSL_STANDARD_REPO_TEMPLATE"
template_version: "1.0.0"
profile: "CSL_GOVERNED"
generated_by: "ORA_PGE"
generated_at_utc: null
source_context:
  - "ORA_SOURCE_CONTEXT_v1.0.0.md"
  - "CSL_STANDARD_REPO_TEMPLATE_v1.0.0.md"
generation_mode: "deterministic"
manual_edits_after_generation: false
```

---

# 11. ORA/PGE Integration Boundaries

## 11.1 ORA Responsibility

ORA may coordinate:

- project profile selection
- repo bootstrap request creation
- PGE invocation
- validator orchestration
- Git operation sequencing
- project queue updates
- escalation reporting

ORA must not:

- bypass governance
- grant itself runtime authority
- silently merge changes
- silently push to protected remotes
- perform unrestricted shell execution
- mutate generated repos without observable records

## 11.2 PGE Responsibility

PGE may perform deterministic repo birth:

- create repository structure
- write baseline files
- install validator scripts
- install hooks
- create bootstrap manifest
- create provenance record
- run initial validators
- optionally create initial commit if allowed

PGE must not:

- decide project strategy
- choose a license silently
- create advanced runtime automation
- enable autonomous deployment
- create recursive self-modification paths
- infer missing governance authority

## 11.3 Generated Repo Responsibility

A generated repo should contain:

- its own governance artifacts
- its own memory artifacts
- deterministic validators
- project source context
- docs/contracts
- tests
- local tools

A generated repo should not contain:

- ORA queue internals
- ORA global registry
- ORA dashboard
- ORA execution bridges
- PGE template engine internals

## 11.4 Validator Boundary

Validation belongs in two places:

1. **Repo-local validators** for repo integrity.
2. **ORA/PGE validators** for bootstrap process integrity.

Do not mix these into one layer.

---

# 12. Recommended ORA Repo Placement

Within the ORA repo, store this review at:

```text
governance/workflows/governed_specs/ORA_CSL_CANONICAL_REPO_TEMPLATE_REVIEW.md
```

Store the future canonical template assets under:

```text
templates/csl_standard_repo/
```

Recommended ORA-side structure:

```text
templates/
└── csl_standard_repo/
    ├── template_manifest.yaml
    ├── profiles/
    │   ├── baseline.yaml
    │   ├── csl_governed.yaml
    │   ├── standalone_light.yaml
    │   └── sandbox.yaml
    ├── skeleton/
    │   ├── .bootstrap/
    │   ├── governance/
    │   ├── memory/
    │   ├── planning/
    │   ├── docs/
    │   ├── schemas/
    │   ├── src/
    │   ├── tools/
    │   ├── tests/
    │   ├── .githooks/
    │   └── .github/
    └── validators/
        └── validate_template_manifest.py
```

Store PGE implementation under:

```text
src/ora/pge/
```

or, if ORA begins as scripts-first:

```text
tools/pge/
```

Recommendation:

Start with `tools/pge/` for MVP. Move to `src/ora/pge/` only after the interface stabilises.

---

# 13. Implementation Sequencing Guidance

## Phase 1 — Governed Template Freeze

Create the first canonical reviewed template spec.

Outputs:

```text
governance/workflows/governed_specs/ORA_CSL_CANONICAL_REPO_TEMPLATE_REVIEW.md
templates/csl_standard_repo/template_manifest.yaml
templates/csl_standard_repo/profiles/baseline.yaml
templates/csl_standard_repo/profiles/csl_governed.yaml
```

Do not implement generation yet.

## Phase 2 — Layout Validator

Create:

```text
tools/validate_repo_layout.py
tests/contract/test_repo_layout.py
```

The validator should check the ORA repo’s own expected structure first.

## Phase 3 — Static Skeleton

Create the static skeleton under:

```text
templates/csl_standard_repo/skeleton/
```

Do not add dynamic templating until the static skeleton validates.

## Phase 4 — Minimal PGE Generator

Create a deterministic generator that:

- reads profile YAML
- copies skeleton files
- renders only simple token replacements
- writes `.bootstrap/bootstrap_manifest.yaml`
- writes `.bootstrap/template_provenance.yaml`
- refuses unknown profiles
- refuses missing required fields
- refuses overwriting non-empty targets unless explicitly allowed

## Phase 5 — Initial Bootstrap Dry Run

Run PGE against a temporary local folder only.

No GitHub creation yet.

## Phase 6 — Local Repo Birth

Allow PGE to initialise a local Git repo and run validators.

No remote push yet.

## Phase 7 — GitHub Repo Creation

Add GitHub creation only after local repo birth is deterministic and validated.

## Phase 8 — Dev/Main Replication

Add declared, observable replication.

No silent sync.

## Phase 9 — Queue Integration

Only after repo bootstrap is stable, update the ORA project queue with bootstrap state.

---

# 14. Governance Review Findings

## 14.1 Approved as Stable

- governance scaffold
- memory scaffold
- DEC/EXE paths
- decision index
- quarantine path
- planning paths
- docs/contracts paths
- snapshots path
- schemas path
- tools path
- tests contract/unit split
- `.githooks/`
- `.github/workflows/`
- README, PROJECT_CONTEXT, CHANGELOG, pyproject

## 14.2 Approved with Refinement

- branch topology
- Dev/Main replication
- validator set
- post-commit behavior
- project profiles
- ORA/PGE integration

## 14.3 Not Approved for Baseline Yet

- runtime bridges in generated repos
- queue internals in generated repos
- dashboard folders in generated repos
- autonomous shell execution
- deployment automation
- economic governance
- advanced commercial/research profile structures
- universal agents folder
- universal orchestration folder
- universal execution folder

---

# 15. Final Recommendation

Adopt the CSL Standard Repo Template as the foundation for the first canonical governed repo bootstrap template, but refine it into a layered model:

```text
BASELINE TEMPLATE
    +
PROFILE OVERLAY
    +
BOOTSTRAP MANIFEST
    +
TEMPLATE PROVENANCE
    +
DETERMINISTIC VALIDATORS
```

The first implementation should be boring, narrow, and deterministic.

The correct v1 success criterion is not:

> ORA can autonomously manage all projects.

The correct v1 success criterion is:

> ORA/PGE can create one clean, governed, profile-declared repo scaffold with deterministic validation and no hidden authority expansion.

That is the stable foundation for everything else.
