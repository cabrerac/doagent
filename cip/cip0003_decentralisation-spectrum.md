---
author: "Christian Cabrera"
created: "2026-02-03"
id: "0003"
last_updated: "2026-02-05"
status: "In Progress"
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
- [x] In Progress - Actively being implemented
- [ ] Implemented - Work complete, awaiting verification
- [ ] Closed - Verified and complete
- [ ] Rejected - Will not be implemented (add reason, use superseded_by if replaced)
- [ ] Deferred - Postponed (use blocked_by field to indicate blocker)

## Summary
Define a configurable decentralisation spectrum so systems can choose centralised, federated, or peer-to-peer coordination without rewriting agents.

## Motivation
Deployments have different control and trust models. The library should expose topology configuration and routing hooks so the same agents can operate across coordination modes.

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

## Progress Updates

### 2026-02-03
Iteration 1 complete. Topology model, configuration, coordination hook stub, and tests added. Tests passed. Iteration 2 planned.

The topology selection API is now explicit and configurable, but routing policies remain stubbed for later iterations.

Gaps and follow-on needs:
- Implement routing policies and coordination strategies per topology.
- Support dynamic topology changes and negotiation.
- Align routing with participation registry and trust policies.

## References
- None yet
