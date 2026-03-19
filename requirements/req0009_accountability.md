---
id: "0009"
title: "System Wide Accountability"
status: "Implemented"
priority: "High"
created: "2026-01-22"
last_updated: "2026-03-19"
related_tenets:
- "provenance-and-accountability"
- "interpretability-and-traceability"
stakeholders:
- "system operators"
- "auditors"
- "end users"
tags:
- requirements
- accountability
---

# REQ-0009: System Wide Accountability

## Description
The system must support accountability for agent actions and decisions, including clear attribution to agents, tools, and policies. Accountability requires explicit ownership, responsibility, and governance context alongside the decision chain.

This requirement focuses on responsibility and governance rather than lineage alone.

**Why this matters**: Accountability ensures decisions can be reviewed, challenged, and governed.

**Who benefits**: Auditors, compliance teams, platform operators, and end users.

## Acceptance Criteria
- [x] Decisions are attributable to specific agents, tools, and policy contexts.
- [x] Accountability metadata is preserved alongside shared data records.
- [x] Governance context is available for audits and reviews.

## Notes (Optional)
Attribution formats and governance policies are defined in CIPs.

## Status and future iterations

**Implemented** means the **acceptance criteria above** are met (envelope accountability metadata plus `doagent.analysis.accountability` for contribution-style attribution where the scenario supports it). **Further accountability work** (write-path threading, policy conventions, adversarial settings—see CIP-0009 questions) continues in **CIP-0009** and **backlog**.

## References
- **Related Tenets**: provenance-and-accountability, interpretability-and-traceability
- **External Links**: None

## Progress Updates

### 2026-01-22
Requirement drafted.

### 2026-02-21
CIP-0009 iteration 1 complete (3/3 items). `Accountability` TypedDict (`owner`, `policy_id`, `responsibility_scope`) on every `SimpleRecord` envelope. `new_accountability()` helper builds metadata. Accountability populated by `RecordWriter` at logging level >= 2. Governance context preserved alongside all shared data records and accessible for auditing.

### 2026-03-19
Requirement marked **Implemented**; further accountability/attribution ideas remain on **CIP-0009**.
