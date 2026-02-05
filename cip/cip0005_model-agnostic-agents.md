---
author: "Christian Cabrera"
created: "2026-02-03"
id: "0005"
last_updated: "2026-02-05"
status: "In Progress"
compressed: false
related_requirements:
- "0005"
related_cips: []
tags:
- cip
- model-agnostic
- architecture
title: "Model-Agnostic Agent Interfaces"
---

# CIP-0005: Model-Agnostic Agent Interfaces

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
Define model-agnostic decision interfaces so agents can use any decision engine while sharing a consistent request/response contract.

## Motivation
Agent systems should not assume a specific model or decision mechanism. A model-agnostic interface allows innovation while keeping data contracts stable.

## Detailed Description
Iteration 1 focuses on request/response structures and a minimal agent protocol.

Options considered:
- **Option A**: Ad-hoc dict payloads without formal contracts.
- **Option B**: Typed request/response payloads and a DecisionAgent protocol.

We select **Option B** to make the interface explicit and reusable across agent implementations.

Key points:
- DecisionRequest and DecisionResponse payload structures.
- DecisionAgent protocol defining decide(request) -> response.
- FunctionAgent adapter to wrap a callable decision function and persist decisions.

## Iteration Deliverable (PoC)
- Decision request/response payload structures.
- DecisionAgent protocol and FunctionAgent adapter.
- Example and tests for model-agnostic decision handling.

## Implementation Plan
1. **Define decision payloads**
   - DecisionRequest and DecisionResponse fields.
2. **Add agent protocol**
   - DecisionAgent interface for model-agnostic decisions.
3. **Implement adapter**
   - FunctionAgent wraps a callable and writes decision records.
4. **Update examples and tests**
   - Example for model-agnostic agent usage.

## Backward Compatibility
Additive only; no breaking changes.

## Testing Strategy
- Unit tests for decision payloads and FunctionAgent behavior.
- Example showing model-agnostic decisions.

## Related Requirements
This CIP addresses the following requirements:
- REQ-0005: Model Agnostic Agent Core

## Implementation Status
- [x] Define decision payloads
- [x] Add agent protocol
- [x] Implement FunctionAgent adapter
- [x] Update examples and tests

## Progress Updates

### 2026-02-03
Iteration 1 complete. Decision payloads, DecisionAgent protocol, FunctionAgent, and tests added. Tests passed. Iteration 2 planned.

The model-agnostic interface is now explicit and usable with any decision engine. Additional agent roles and runtime hooks are deferred.

Gaps and follow-on needs:
- Add sensor/effectors interfaces and lifecycle hooks.
- Consider streaming or multi-step decision protocols.
- Provide guidance for structured decision payload schemas.

## References
- None yet
