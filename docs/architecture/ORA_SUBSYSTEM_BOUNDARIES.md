# ORA Subsystem Boundaries

Profile Registry:
- declares project scaffolds and validator sets

PGE:
- deterministic bootstrap planning and explicit local scaffold writing only

Registry:
- stores admitted machine-readable repo metadata

Queue:
- stores deterministic initial governed admission state only

Operations:
- reserved for allowlisted operation planning only

Validation:
- deterministic schema validation plus validator plan generation only
- validator selection is sourced from profile YAML and checked against admitted registry state

Bridges:
- governed packet generation only for supported bridges
