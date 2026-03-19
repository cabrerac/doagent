---
author: "Christian Cabrera"
created: "2026-02-03"
id: "0003"
last_updated: "2026-03-19"
status: "Implemented"
compressed: false
related_requirements:
- "0003"
related_cips: []
tags:
- cip
- decentralisation
- architecture
title: "Decentralisation Spectrum and Topology"
---

# CIP-0003: Decentralisation Spectrum and Topology

> **Note**: CIPs describe HOW to achieve requirements (WHAT).
> Use `related_requirements` to link to the requirements this CIP implements.

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [ ] In Progress - Actively being implemented
- [x] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

**Implemented** for this CIP means **iteration 1** (topology model, configuration, coordination hook stub, tests/examples) is delivered and **REQ-0003**’s current criteria are met. **Further decentralisation work** remains explicitly listed under **Discussion items / Future iteration** and as **unchecked** items in **Implementation Status** below—plus future backlog/CIP slices. Marking Implemented does **not** block those follow-ons.

## Summary
Define a configurable decentralisation spectrum so systems can choose centralised, federated, or peer-to-peer coordination without rewriting agents.

## Motivation
Deployments have different control and trust models. The library should expose topology configuration and routing hooks so the same agents can operate across coordination modes.

**Alignment with DOA and the agentic reasoning paper.** The paper states that multi-agent evolution requires **shared memory, communication mechanisms, and collaboration** — the three DOA principles. Decentralisation is the **communication mechanisms** pillar: it defines *how* the shared memory is accessed (who sees what, topology, visibility). The paper also frames communication as part of collective reasoning: what agents observe from the shared substrate extends their observations and feeds their reasoning. So topology and visibility are not just "who gets messages" — they define *what context each agent has for reasoning*. The shared data model (CIP-0002) is the channel; decentralisation configures the mechanisms that govern access to it. See `papers/agentic-reasoning-llm-reading-guide.md` §3 for the full mapping.

## Detailed Description
Iteration 1 focuses on a topology model and coordination hook stubs.

Options considered:
- **Option A**: Fixed centralised coordination (simple but inflexible).
- **Option B**: Configurable topology model with routing hook stubs.
- **Option C**: Fully dynamic topology discovery and negotiation.

We select **Option B** for the PoC. It provides explicit topology configuration and leaves routing policies to a later iteration.

Key points:
- Topology model captures coordination modes (centralised, federated, peer-to-peer).
- TopologyConfig allows selecting mode and optional settings.
- select_routing (or equivalent) provides a coordination hook stub for future policies and returns a RoutingDecision.

### Discussion items / Future iteration

- **Distributed shared data model.** The shared data model (CIP-0002) is currently implemented as a **central** store (one in-memory, file, or Mongo instance); topology only filters visibility. In a decentralised and open setting, the store may need to be **distributed**: each agent or group holds a chunk of the logical model, so the "shared data model" is one contract but many physical shards. Placement, routing, and consistency are open design points. Exploring e.g. MongoDB sharding (one logical namespace, data spread across shards) is one possible direction. Resolves the tension between "data-first shared model" (one substrate) and "decentralised-by-design" (no single point of control).

- **Mechanism design / incentives.** Today we have topology and visibility only. The paper mentions mechanism design (incentives, rewards). Future iterations may want hooks for: who is allowed to write where (write authorisation), cost or quota of visibility (e.g. federated hubs limiting or charging access), or contribution/reward semantics (credit for useful writes). No commitment; document as a discussion topic so "mechanisms" can later include incentives, not only visibility.

- **Dynamic topology.** Support for topology that changes at runtime (agents join/leave, graph changes). Already in gaps; explicitly relevant for open environments where the set of participants and their connectivity evolves during a run or across runs.

- **Cross-domain / federation boundaries.** Domains as trust or administrative boundaries (e.g. hub ↔ domain); which data or chunk belongs to which domain; rules for sharing and writing across federated domains. When the shared data model becomes distributed, "this chunk belongs to domain X" and cross-boundary policies (what can cross, who can write) align with federation. For future iteration.

## Iteration Deliverable (PoC)
- Topology enum/model and configuration structure.
- Coordination hook stub (routing decision placeholder) returning a RoutingDecision.
- Example and tests for topology selection.

## Implementation Plan
1. **Define topology model**
   - Enumerate supported modes.
2. **Add topology configuration**
   - Provide a config object for selecting modes.
3. **Add coordination hook**
   - Stub routing selection function.
4. **Update examples and tests**
   - Minimal test coverage for topology selection.

## Backward Compatibility
Additive only; no breaking changes.

## Testing Strategy
- Unit tests for topology config and routing selection.
- Example demonstrating mode selection.

## Related Requirements
This CIP addresses the following requirements:
- REQ-0003: Configurable Decentralisation Spectrum

## Implementation Status
- [x] Define topology model
- [x] Add topology configuration
- [x] Add coordination hook stub
- [x] Update examples and tests
- [ ] Distributed shared data model (chunks, sharding, placement, routing) — future iteration; see Discussion items
- [ ] Mechanism design / incentives (write auth, visibility quotas, contribution rewards) — future iteration; discussion topic
- [ ] Dynamic topology (runtime join/leave, graph changes) — future iteration; already in gaps
- [ ] Cross-domain / federation boundaries (domain authority, chunk ownership, cross-boundary rules) — future iteration; see Discussion items

## Progress Updates

### 2026-02-03
Iteration 1 complete. Topology model, configuration, coordination hook stub, and tests added. Tests passed. Iteration 2 planned.

The topology selection API is now explicit and configurable, but routing policies remain stubbed for later iterations.

Gaps and follow-on needs:
- Implement routing policies and coordination strategies per topology.
- Support dynamic topology changes and negotiation.
- Align routing with participation registry and trust policies.

### 2026-02-06
Iteration 2 discussion item: The current simple_push validation example does not exercise decentralisation modes. Iteration 2 should include a scenario that demonstrates centralised vs federated vs peer-to-peer coordination choices.

### 2026-03-19
CIP marked **Implemented** for current scoped delivery; future items unchanged (distributed store, mechanisms, dynamic topology, federation—see Discussion items).

### 2025-03-13
Added **alignment with DOA and the agentic reasoning paper** to Motivation: decentralisation as the "communication mechanisms" pillar (how shared memory is accessed); communication as part of collective reasoning (topology/visibility define reasoning context, not just message delivery). References reading guide §3.

### 2025-03-13
Added **Discussion items / Future iteration**: (1) Distributed shared data model — central store today; in decentralised/open settings may need chunks per agent/group or sharding (e.g. Mongo sharding); placement, routing, consistency for later. (2) Mechanism design / incentives — optional hooks for write auth, visibility quotas, contribution rewards. (3) Dynamic topology — runtime join/leave, explicit tie to open environments. (4) Cross-domain / federation boundaries — domain authority, chunk ownership, cross-boundary rules. Implementation Status updated with unchecked items for these.

## References
- None yet
