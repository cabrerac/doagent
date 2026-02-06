---
author: "Christian Cabrera"
created: "2026-02-03"
id: "0004"
last_updated: "2026-02-05"
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

## References
- None yet
