---
author: "Christian Cabrera"
created: "2026-02-03"
id: "0004"
last_updated: "2025-03-13"
status: "In Progress"
compressed: false
related_requirements:
- "0004"
related_cips: []
tags:
- cip
- participation
- architecture
title: "Open Participation Registry"
---

# CIP-0004: Open Participation Registry

> **Note**: CIPs describe HOW to achieve requirements (WHAT).
> Use `related_requirements` to link to the requirements this CIP implements.

## Status

- [x] Proposed - Initial idea documented
- [x] Accepted - Approved, ready to start work
- [x] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

## Summary
Define participation records and a registry interface so agents can join, leave, and advertise capabilities in an open system.

## Motivation
Open participation requires discoverable capabilities and stable interfaces so agents can integrate without bespoke wiring. A minimal registry provides a shared contract.

**Alignment with DOA and the agentic reasoning paper.** The paper states that multi-agent evolution requires **shared memory, communication mechanisms, and collaboration** — the three DOA principles. Openness (open collaboration) is the **collaboration** pillar: who can join, what they can contribute, and how participation scales. The registry and participation model enable the kind of multi-agent collaboration the paper has in mind (agents joining, leaving, advertising capabilities) without bespoke wiring, so that the shared data model and topology (the other two pillars) can operate in an open ecosystem. See `papers/agentic-reasoning-llm-reading-guide.md` §3 for the full mapping.

## Detailed Description
Iteration 1 focuses on participation records and an in-memory registry.

Options considered:
- **Option A**: Central registry interface with in-memory implementation.
- **Option B**: Decentralised registry with gossip or peer-to-peer discovery.
- **Option C**: Hybrid registry with pluggable backends.

We select **Option A** for the PoC. It provides a simple contract while deferring decentralised discovery to later iterations.

Key points:
- ParticipationRecord captures agent id, capabilities, resource limits, and optional metadata.
- ParticipationRegistry interface defines register, update, deregister, get, and list methods.
- InMemoryParticipationRegistry provides a minimal adapter.

### Discussion items / Future iteration

- **Registry vs store / chunk ownership.** Today the registry (who is in, capabilities) is separate from the shared data store. If the shared data model becomes distributed (CIP-0002/0003: chunks per agent or group), the registry may need to describe **data placement** or **chunk ownership** (e.g. "agent X hosts chunk for kind K in region R"). So "align participation registry with topology" can evolve into "registry describes who holds which chunk." For future iteration.

- **Admission and policy enforcement.** Already in gaps. "Who can join" may depend on policy (e.g. only agents that accept a given contract); admission and policy hooks keep openness manageable at scale. No change to scope; ensure it remains an explicit discussion topic.

- **Discovery across domains.** Open collaboration across organisations may require **discovery** beyond a single registry: (a) **participant discovery** — finding agents or capabilities across multiple registries or domains (e.g. federated directory, registry-of-registries); (b) **data/resource discovery** — finding where a given chunk or capability lives when data is distributed. For future iteration.

## Iteration Deliverable (PoC)
- Participation record structure.
- Registry interface + in-memory implementation.
- Example and tests for participation registration and retrieval.

## Implementation Plan
1. **Define participation record**
   - Capture agent id, capabilities, and resource limits.
2. **Define registry interface**
   - Register, update, deregister, get, list operations.
3. **Implement in-memory registry**
   - Simple adapter for tests and examples.
4. **Update examples and tests**
   - Cover registration and listing.

## Backward Compatibility
Additive only; no breaking changes.

## Testing Strategy
- Unit tests for registry operations and record storage.
- Example showing registration and lookup.

## Related Requirements
This CIP addresses the following requirements:
- REQ-0004: Open Participation and Resource Exchange

## Implementation Status
- [x] Define participation record
- [x] Define registry interface
- [x] Implement in-memory registry
- [x] Update examples and tests
- [ ] Registry vs store / chunk ownership (placement in registry when data is distributed) — future iteration; see Discussion items
- [ ] Admission and policy enforcement hooks — future iteration; already in gaps
- [ ] Discovery across domains (participant and data/resource discovery) — future iteration; see Discussion items

## Progress Updates

### 2026-02-03
Iteration 1 complete. Participation record, registry interface, in-memory registry, and tests added. Tests passed. Iteration 2 planned.

The system now exposes a participation registry contract, but decentralised discovery and policy controls are deferred.

Gaps and follow-on needs:
- Align participation registry with topology modes (centralised vs federated).
- Provide distributed or pluggable registry backends.
- Add admission and policy enforcement hooks.

### 2026-02-06
Iteration 2 discussion item: The current simple_push validation example does not demonstrate open participation. Iteration 2 should include a scenario that exercises join/leave and capability discovery.

### 2025-03-13
Added **alignment with DOA and the agentic reasoning paper** to Motivation: openness as the "collaboration" pillar in the paper's triad (shared memory, communication mechanisms, collaboration); registry and participation enable multi-agent collaboration in an open ecosystem. References reading guide §3.

### 2025-03-13
Added **Discussion items / Future iteration**: (1) Registry vs store / chunk ownership — registry may describe data placement or chunk ownership when shared data is distributed. (2) Admission and policy enforcement — keep as explicit discussion topic (already in gaps). (3) Discovery across domains — participant discovery across registries (federated directory) and data/resource discovery (where is chunk X). Implementation Status updated with unchecked items for these.

## References
- None yet
