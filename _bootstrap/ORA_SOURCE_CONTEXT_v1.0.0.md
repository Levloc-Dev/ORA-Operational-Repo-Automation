# ORA — Operational Repo Automation
## Source Context & Project Definition
### Version: 1.0.0
### Status: Foundational Project Definition
### Profile Recommendation: CSL_GOVERNED

---

# 1. Project Overview

ORA (Operational Repo Automation) is a governed operational automation layer designed to remove the human transport bottleneck from multi-project AI-assisted software development workflows.

ORA exists to automate the repetitive operational aspects of project creation, repository management, slice execution, validation orchestration, and agent handoff workflows while preserving explicit governance, fail-closed execution boundaries, and human constitutional authority.

ORA is not intended to be:
- an unrestricted autonomous coding agent
- a self-authorising runtime
- a replacement for CSL governance
- a freeform autonomous shell executor

ORA is intended to become:
- a governed workflow orchestration substrate
- a project operations automation system
- a repo birth and lifecycle automation layer
- an execution bridge between ChatGPT, Codex, Claude, GitHub, VS Code, and local tooling
- a multi-project coordination and escalation system

---

# 2. Core Problem Statement

Current workflow friction exists because the human operator manually performs:

- file downloads
- file movement
- prompt relaying
- repo bootstrap repetition
- branch setup
- validator execution
- project tracking
- Codex/Claude handoffs
- result relays between systems
- repetitive governance setup

The human has effectively become the "transport layer" between otherwise automatable systems.

ORA exists to remove this bottleneck.

---

# 3. High-Level Vision

ORA should enable a future workflow similar to:

ChatGPT / Claude / Codex
    ↓
ORA Operational Layer
    ↓
ORP Governance Layer
    ↓
Repo Operations
    ↓
Validation Layer
    ↓
Git Operations
    ↓
Project Queue / Escalation System

Where:
- humans define constitutional authority and escalation decisions
- ORP governs what is allowed
- ORA automates operational workflow execution
- validators enforce deterministic integrity
- projects progress with minimal manual transport overhead

---

# 4. Primary Goals

## 4.1 Workflow Automation
Remove repetitive manual workflow operations.

## 4.2 Multi-Project Coordination
Track and coordinate multiple concurrent projects.

## 4.3 Governed Automation
Preserve explicit authority boundaries and fail-closed execution.

## 4.4 Repo Birth Automation
Automate creation of new repositories using standardised project profiles.

## 4.5 Execution Handoff Automation
Automate relay between:
- ChatGPT
- Codex
- Claude
- GitHub
- local repos
- validators

## 4.6 Human Escalation Layer
Escalate only when:
- ambiguity exists
- governance approval is required
- execution fails
- conflicts occur
- strategic decisions are needed

---

# 5. Key Architectural Principles

## 5.1 Governance First
ORA must never bypass constitutional governance.

## 5.2 Fail Closed
Ambiguous authority or invalid execution states must fail closed.

## 5.3 Deterministic Validation
Critical validation must use scripts/hooks instead of model judgment.

## 5.4 Modular Automation
Avoid monolithic "AI agent" architecture.

## 5.5 Explicit Capability Boundaries
Every capability must be declared and scoped.

## 5.6 Human Constitutional Authority
Humans remain the ultimate authority layer.

---

# 6. Proposed Ecosystem Position

CSL
- Constitutional governance

ORP
- Governance orchestration and policy routing

ORA
- Operational automation and workflow execution

PGE
- Project/repo birth automation subsystem

TOS
- Economic and treasury substrate

WIO
- Deterministic execution and verification patterns

PAL
- External adapter layer

CPT
- Observability and accounting

---

# 7. Core Functional Areas

## 7.1 Project Profiles

Projects should use explicit operational profiles.

Initial proposed profiles:

### CSL_GOVERNED
Full governance stack:
- memory gates
- DEC/EXE
- validation reports
- Dev/Main sync
- strict branch governance

### STANDALONE_LIGHT
Lightweight project automation:
- README
- basic structure
- optional tests
- simple branches

### STANDALONE_COMMERCIAL
Commercial product profile:
- roadmap
- licensing
- release workflow
- product documentation

### RESEARCH_LIBRARY
Knowledge ingestion and synthesis projects.

### SANDBOX
Disposable experimental projects.

---

## 7.2 Repo Bootstrap Automation (PGE)

Automate:
- GitHub repo creation
- Levloc-Dev repo setup
- Levloc-Main replication
- collaborator setup
- local clone creation
- governance scaffold installation
- validator installation
- sync workflow installation
- initial DEC/EXE creation
- initial snapshot creation

---

## 7.3 Repo Operations

Automate:
- file writing
- branch creation
- patch application
- validator execution
- commit creation
- project state tracking

---

## 7.4 Execution Bridges

Integrate with:
- ChatGPT
- Codex
- Claude Code
- GitHub
- VS Code
- local scripts/hooks

Future:
- WhatsApp escalation
- Tasker/AEX notifications
- mobile approvals

---

## 7.5 Project Queue System

Track:
- current slice
- current branch
- validation state
- pending escalation
- project blockers
- next recommended actions

---

# 8. Initial Recommended Scope

## ORA v1 MVP

The initial MVP should remain intentionally narrow.

Recommended v1 capabilities:

- project profiles
- repo bootstrap
- repo registry
- direct file writing
- validator runner
- commit generation
- Dev/Main sync
- project queue tracking

Explicitly excluded from v1:
- unrestricted shell execution
- autonomous deployment
- autonomous merges
- recursive self-modification
- unrestricted runtime authority

---

# 9. Recommended Technology Stack

## Runtime Layer
Rust preferred for:
- concurrency
- deterministic execution
- orchestration reliability
- long-running services

## Automation Layer
Python preferred for:
- scripts
- validators
- YAML handling
- repo templating
- GitHub integration
- glue logic

## Dashboard Layer
Flutter or lightweight web UI.

## Storage
Initial:
- filesystem + YAML

Later:
- SQLite

---

# 10. Suggested Repo Structure

```text
ORA-Operational-Repo-Automation/
├── governance/
├── memory/
├── planning/
├── docs/
├── schemas/
├── tools/
├── profiles/
├── templates/
├── runtime/
├── bridges/
├── validators/
├── queue/
├── tests/
└── dashboard/
```

---

# 11. Recommended Immediate Development Sequence

## Phase 1
Project profiles and repo bootstrap.

## Phase 2
Direct repo writing.

## Phase 3
Codex/Claude execution bridge.

## Phase 4
Validator orchestration.

## Phase 5
Project queue and escalation dashboard.

## Phase 6
Governed multi-project orchestration.

---

# 12. Long-Term Strategic Value

ORA is not merely a helper utility.

ORA has the potential to become:
- a governed software operations substrate
- a multi-agent workflow platform
- a repo lifecycle automation system
- a constitutional AI operations framework
- a commercial-grade governed autonomous engineering platform

The long-term goal is not:
"AI writes code."

The long-term goal is:
"Governed autonomous software operations with human constitutional oversight."

---

# 13. Final Guidance

ORA should evolve incrementally.

Do not:
- over-engineer early
- attempt unrestricted autonomy
- collapse governance and execution into one layer
- rely on model memory for deterministic enforcement

Prefer:
- deterministic hooks
- explicit contracts
- modular boundaries
- capability scoping
- governed escalation
- progressive automation

ORA should remove the human from repetitive transport workflows while preserving human authority over governance and strategic direction.
