# CSL Standard Repo Template
## Canonical Bootstrap Specification
### Version: 1.0.0
### Status: Foundational Template Definition
### Target Project: ORA — Operational Repo Automation

---

# 1. Purpose

This document defines the first canonical CSL Standard Repo Template.

The template exists to standardise:
- repository birth
- governance structure
- memory structure
- validation workflows
- project scaffolding
- repo operational conventions
- Dev/Main replication conventions
- deterministic governance boundaries

This template is intended to become:
- the baseline for future CSL ecosystem projects
- the foundation for ORA/PGE automation
- the canonical repo bootstrap structure
- the operational genome for governed projects

This template is NOT intended to:
- represent the final perfect architecture
- encode every future governance concept
- prematurely automate unstable workflows
- introduce unnecessary complexity

The template should evolve incrementally and remain versioned.

---

# 2. Design Principles

## 2.1 Governance First
All governed repos must preserve explicit authority boundaries.

## 2.2 Fail Closed
Ambiguous or invalid execution states must fail closed.

## 2.3 Deterministic Validation
Critical enforcement should use scripts/hooks rather than model memory.

## 2.4 Incremental Evolution
The template must evolve gradually based on stable patterns.

## 2.5 Modular Structure
Avoid tightly coupled monolithic architecture.

## 2.6 Profile Compatibility
The template must support future project profiles.

---

# 3. Initial Scope

The v1 template should include ONLY patterns already proven stable across multiple projects.

Included:
- governance scaffold
- memory structure
- DEC/EXE structure
- validator tooling
- snapshot conventions
- branch conventions
- sync conventions
- planning structure
- tests scaffold
- repo metadata

Explicitly excluded:
- autonomous deployment
- unrestricted runtime authority
- advanced orchestration
- economic governance
- unrestricted agent execution
- recursive self-modification

---

# 4. Canonical Repo Structure

```text
PROJECT-NAME/
├── governance/
│   ├── constitution/
│   ├── control_plane/
│   ├── workflows/
│   │   ├── governed_specs/
│   │   └── validation_reports/
│   └── reviews/
│
├── memory/
│   ├── evolution/
│   │   ├── decisions/
│   │   ├── executions/
│   │   └── quarantine/
│   └── indexes/
│
├── planning/
│   ├── seeds/
│   ├── prompts/
│   └── implementation_prompts/
│
├── docs/
│   ├── architecture/
│   │   └── snapshots/
│   └── contracts/
│
├── schemas/
├── src/
├── tools/
├── tests/
│   ├── contract/
│   └── unit/
│
├── .githooks/
├── .github/
│   └── workflows/
│
├── README.md
├── PROJECT_CONTEXT.md
├── CHANGELOG.md
└── pyproject.toml
```

---

# 5. Mandatory Governance Components

## 5.1 Memory Structure

Required:
- decision records
- execution records
- canonical index
- quarantine support

## 5.2 Decision Records

Canonical location:

```text
memory/evolution/decisions/
```

Format:
```text
DEC-XXXX.yaml
```

## 5.3 Execution Records

Canonical location:

```text
memory/evolution/executions/
```

Format:
```text
EXE-XXXX.yaml
```

## 5.4 Canonical Index

Canonical location:

```text
memory/indexes/decision_index.yaml
```

---

# 6. Validator Requirements

The template should install deterministic validators.

Initial validator set:

```text
tools/validate_memory.py
tools/check_memory_integrity.py
tools/validate_execution_records.py
tools/check_working_tree_artifact_admission.py
```

Future validators may be added incrementally.

---

# 7. Git Hook Requirements

The template should install:

```text
.githooks/pre-commit
.githooks/post-commit
```

Initial responsibilities:
- validation execution
- snapshot refresh
- deterministic enforcement
- optional admission checks

Hooks must avoid hidden mutation whenever possible.

---

# 8. Snapshot Conventions

Canonical location:

```text
docs/architecture/snapshots/
```

Snapshots should:
- remain deterministic
- avoid self-inclusion drift
- be committed separately from governed changes whenever practical

---

# 9. Branching Conventions

Initial recommendation:

```text
main
develop
feature/*
review/*
hotfix/*
```

Governed repos may apply stricter branch policies.

---

# 10. Dev/Main Replication

CSL-governed projects should support:

```text
Levloc-Dev ↔ Levloc-Main
```

Replication conventions:
- deterministic sync
- explicit automation
- observable operations
- no silent divergence

The exact implementation may evolve.

---

# 11. Project Profiles

The template must support future profile-driven generation.

Initial proposed profiles:

```text
CSL_GOVERNED
STANDALONE_LIGHT
STANDALONE_COMMERCIAL
RESEARCH_LIBRARY
SANDBOX
```

Profiles should determine:
- governance strictness
- validator requirements
- branch policies
- automation boundaries
- reporting requirements

---

# 12. ORA/PGE Integration

This template is expected to become:
- the bootstrap source for PGE
- the canonical repo profile for ORA
- the baseline for automated repo birth

Future automation should instantiate repositories from governed templates rather than hand-building repositories manually.

---

# 13. Recommended Immediate Next Steps

## Phase 1
Define canonical template assets.

## Phase 2
Define profile variations.

## Phase 3
Define bootstrap manifest schema.

## Phase 4
Define PGE repo-instantiation workflow.

## Phase 5
Implement ORA bootstrap automation.

---

# 14. Final Guidance

This template should remain:
- intentionally narrow
- operationally useful
- governance-aware
- versioned
- incrementally evolving

Do not attempt to encode every future architectural possibility into the initial version.

Prefer:
- stability
- deterministic operation
- clear boundaries
- explicit governance
- reusable structure
