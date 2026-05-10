# ORA System Overview

ORA v1 is a deterministic, governed operational automation repository with a
narrow implemented MVP surface.

Current implemented slices include:
- repository structure and source context
- profile declarations and schema-backed validation
- deterministic PGE bootstrap plan generation
- explicit local scaffold writing
- repo registry admission
- initial queue admission
- governed handoff packet generation
- validator plan generation only

The current boundary still excludes autonomous runtime execution, deployment,
merge automation, GitHub bridge execution, dashboard implementation, and
unrestricted shell authority.

Primary architecture reference:
- `planning/architecture/ORA_v1_ARCHITECTURE_AND_REPO_TREE.md`

Source context references:
- `PROJECT_CONTEXT.md`
- `ORA_SOURCE_CONTEXT_v1.0.0.md`
