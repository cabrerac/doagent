---
id: "0003"
title: "Configurable Decentralisation Spectrum"
status: "Implemented"
priority: "High"
created: "2026-01-22"
last_updated: "2026-09-05"
related_tenets:
- "decentralised-by-design"
stakeholders:
- "platform maintainers"
- "system operators"
tags:
- requirements
- decentralisation
---

# REQ-0003: Configurable Decentralisation Spectrum

## Description
The system must support multiple coordination topologies, ranging from centralised control to federated and peer to peer modes. Users should be able to select or evolve a topology without rewriting agents or their core logic.

This requirement ensures that decentralisation is a first class capability and can be adapted to different environments and constraints.

**Why this matters**: Different deployments require different control models, and the system must remain flexible.

**Who benefits**: System operators, infrastructure teams, and researchers.

## Acceptance Criteria
- [x] The system supports centralised, federated, and peer to peer coordination modes.
- [x] Agents can operate across these modes without code changes.
- [x] Topology changes can be expressed through configuration or orchestration policy.

## Notes (Optional)
Specific protocols and orchestration mechanisms are defined in CIPs. CIP-0003 records a future **coordination
protocol** layer (default behaviour plus a replaceable hook): visibility (who may read) and relay (who republishes
so others can see an event). This is distinct from Python interface protocols (`SharedDataAdapter`, `DecisionAgent`).
Users should be able to pick a built-in or supply their own without rewriting agents.

## Status and future iterations

**Implemented** means the **acceptance criteria above** are satisfied for the current product. **Further decentralisation work** (distributed stores, dynamic topology, mechanism design, replaceable coordination protocols, etc.) continues through **CIP-0003** (*Discussion items / Future iteration*, unchecked Implementation Status lines) and **backlog** tasks. You may **add or refine criteria** later if the WHAT expands—this is normal, not a contradiction.

## References
- **Related Tenets**: decentralised-by-design
- **External Links**: None

## Progress Updates

### 2026-09-05
Pointer added to CIP-0003 coordination-protocol design note (default + replaceable visibility and relay). Requirement
status unchanged.

### 2026-03-19
Status set to **Implemented** while keeping **CIP-0003** as the home for future iterations (see *Status and future iterations* above).

### 2026-01-22
Requirement drafted.

### 2026-02-21
CIP-0003 iteration 1 complete (4/4 items). `Topology` enum (centralised, peer-to-peer, federated), `TopologyConfig`, `select_routing()`, and topology tests implemented. Grid-world validation exercises all three modes via YAML config. Session API applies topology-filtered `visible_records()` transparently. Routing policies remain stubbed (iteration 2).
