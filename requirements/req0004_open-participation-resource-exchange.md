---
id: "0004"
title: "Open Participation and Resource Exchange"
status: "Implemented"
priority: "High"
created: "2026-01-22"
last_updated: "2026-09-05"
related_tenets:
- "open-participation"
stakeholders:
- "agent developers"
- "platform maintainers"
- "external integrators"
tags:
- requirements
- openness
---

# REQ-0004: Open Participation and Resource Exchange

## Description
Agents should be able to join and leave systems dynamically, and the system should support transparent capability and resource exchange. Participation should be possible through documented interfaces and clear capability contracts, without requiring bespoke integration for each agent.

This requirement focuses on openness at the system boundary so that agents can contribute resources and collaborate across organisational or infrastructure boundaries.

**Why this matters**: Open participation allows the system to scale and adapt by leveraging diverse resources and capabilities.

**Who benefits**: External partners, platform operators, and end users.

## Acceptance Criteria
- [x] Agents can join or leave without manual system reconfiguration.
- [x] Agents can advertise capabilities and resource constraints in a transparent way.
- [x] Participation is supported through stable and documented interfaces.

## Notes (Optional)
Discovery, admission, and policy enforcement mechanisms are specified in CIPs.

## Status and future iterations

**Implemented** — all acceptance criteria above are met (CIP-0004: registry plus `participation` events in the shared
data model, inspectable via `session.inspect("participation")`). **Additional participation features** (registry
replay after restart, distributed discovery, admission policy, etc.) stay on **CIP-0004** as future iterations and
do not reopen this requirement until scoped as new criteria.

## References
- **Related Tenets**: open-participation
- **External Links**: None

## Progress Updates

### 2026-01-22
Requirement drafted.

### 2026-02-21
CIP-0004 iteration 1 complete (4/4 items). `ParticipationRecord`, `ParticipationRegistry` protocol, and `InMemoryParticipationRegistry` implemented. Grid-world validation exercises stochastic join/leave with energy model. Capability advertisement (criterion 2) not yet implemented — deferred to iteration 2.

### 2026-03-19
Clarified **In Progress** + future work model in *Status and future iterations* (Session-exposed registry landed in CIP-0004 progress notes; REQ criterion 2 still open).

### 2026-09-05
Criterion 2 met: join/leave write `participation` records with capabilities and resource limits; `inspect("participation")` reads them. Requirement marked **Implemented**. Replay of live membership after restart remains on CIP-0004.
