---
id: "2026-03-28_update-data-model-spec"
title: "Update data-model-spec.md for choice, reasoning, and IDK"
status: "Ready"
priority: "Medium"
created: "2026-03-28"
last_updated: "2026-03-28"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies:
- "2026-03-28_policy-return-shape-and-decide"
- "2026-03-28_reasoning-field-in-payload"
tags:
- backlog
- documentation
- data-model
---

# Task: Update data-model-spec.md for choice, reasoning, and IDK

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Update `docs/data-model-spec.md` to reflect the new record shapes:

1. **Section 3.1 (agent_update):** Replace `response.decision` with `response.choice` in the payload description. Document `choice.status` values (`act`, `abstain`, `error`) and `choice.action` semantics.
2. **Reasoning field:** Document the optional `response.reasoning` field for policy factorization (Z vs A split). Note that it lives inside `decision.response`, not as a top-level payload field.
3. **IDK / abstain:** Document that `choice.status: "abstain"` represents explicit agent abstention (IDK), distinct from error. Note that the environment should handle `null` action for abstain/error cases.
4. **Error:** Document `choice.status: "error"` and optional `choice.error` object.

## Acceptance Criteria

- [ ] Section 3.1 accurately describes the new `response.choice` shape.
- [ ] `choice.status` enum values are documented with semantics.
- [ ] Optional `reasoning` field is documented.
- [ ] Abstain and error handling guidance is included.
- [ ] Spec is consistent with implemented code (tasks 1 and 2).

## Implementation Notes

- Can run in parallel with task 3 (heuristic policy updates).
- Keep the spec concise; detailed design rationale lives in CIP-0002.

## Related

- CIP: [0002](../../cip/cip0002_shared-data-model.md)
- Parent task: [2026-03-27_talk-policy-factorization-idk-library](./2026-03-27_talk-policy-factorization-idk-library.md)
- Depends on: [2026-03-28_policy-return-shape-and-decide](./2026-03-28_policy-return-shape-and-decide.md), [2026-03-28_reasoning-field-in-payload](./2026-03-28_reasoning-field-in-payload.md)

## Progress Updates

### 2026-03-28

Task created as sub-task 4 of 6.
