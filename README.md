# ORA - Operational Repo Automation

ORA is a CSL-governed repository for operational repo automation.

The current repository state is a narrow governed MVP with these implemented slices:
- deterministic PGE bootstrap plan generation
- explicit local scaffold writing with required confirmation
- repo registry admission
- queue admission
- validator plan generation only
- governed handoff packet generation
- deterministic validation entrypoints and supporting schemas

Current fail-closed boundary:
- no autonomous execution engine
- no GitHub or network bridge execution
- no unrestricted shell execution
- no deployment
- no autonomous merges
- no dashboard implementation
- no PGE expansion beyond the implemented local planning and scaffold flow

See [PROJECT_CONTEXT.md](/home/levloc/dev/ORA-Operational-Repo-Automation/PROJECT_CONTEXT.md) for project definition and boundaries.
