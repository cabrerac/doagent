---
id: "0002"
title: "Shared Data Model as Agent Interface"
status: "Proposed"
priority: "High"
created: "2026-01-22"
last_updated: "2026-01-22"
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
- [ ] Agents can coordinate using a shared data model without direct message passing.
- [ ] Agent state and decisions are externally observable through the shared model.
- [ ] The shared model can serve as the canonical source of truth for system state.

## Notes (Optional)
This requirement does not prescribe a specific data backend or protocol.

## References
- **Related Tenets**: data-first-shared-model
- **External Links**: None

## Progress Updates

### 2026-01-22
Requirement drafted.
