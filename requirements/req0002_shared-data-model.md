---
id: "0002"
title: "Shared Data Model as Agent Interface"
status: "Implemented"
priority: "High"
created: "2026-01-22"
last_updated: "2026-02-21"
related_tenets:
- "data-first-shared-model"
stakeholders:
- "platform maintainers"
- "agent developers"
tags:
- requirements
- data-model
---

# REQ-0002: Shared Data Model as Agent Interface

## Description
Agents must be able to communicate and coordinate through a shared data model that acts as the primary interface between them. The shared model should be the canonical source of agent state and communication, enabling external systems to inspect, query, and reason about agent behaviour.

This requirement is about outcomes: a shared data model is the default medium for coordination, and it is observable without needing direct connections to agent runtimes.

**Why this matters**: This enables interpretability, traceability, and collaboration across agents by making state and decisions accessible.

**Who benefits**: Agent developers, platform operators, auditors, and integrators.

## Acceptance Criteria
- [x] Agents can coordinate using a shared data model without direct message passing.
- [x] Agent state and decisions are externally observable through the shared model.
- [x] The shared model can serve as the canonical source of truth for system state.

## Notes (Optional)
This requirement does not prescribe a specific data backend or protocol.

## References
- **Related Tenets**: data-first-shared-model
- **External Links**: None

## Progress Updates

### 2026-01-22
Requirement drafted.

### 2026-02-21
Iteration 2 complete. CIP-0002 moved to Implemented. Shared data model defined with record envelope, listen semantics, provenance (flat attribution), accountability, three adapters (InMemory, File, Mongo), collection-per-kind storage, state deduplication on by default, trace graph, and adapter contract documentation. All backlog items closed. Iteration 3 items noted in CIP-0002: partial/no-outcome environments, SQL/stream adapters (deferred).
