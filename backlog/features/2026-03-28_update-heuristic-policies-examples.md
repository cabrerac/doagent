---
id: "2026-03-28_update-heuristic-policies-examples"
title: "Update existing heuristic policies and examples to new choice shape"
status: "Ready"
priority: "High"
created: "2026-03-28"
last_updated: "2026-03-28"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies:
- "2026-03-28_policy-return-shape-and-decide"
tags:
- backlog
- policy-factorization
- migration
---

# Task: Update existing heuristic policies and examples to new choice shape

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Update all existing policy implementations and example scripts to return the new `choice` shape instead of `response.decision.action`. No backward-compat shim; this is a clean migration.

**Files to update (non-exhaustive, verify during implementation):**
- `examples/push_demo/push_demo.py` — heuristic push policies
- `examples/gridworld_demo/` — gridworld policies
- Any test fixtures or helpers that define inline policies
- Any other policy callables across the codebase

**Before:**
```python
return {"decision": {"action": 4}, "explanation": "..."}
```

**After:**
```python
return {"choice": {"status": "act", "action": 4}, "explanation": "..."}
```

Heuristic policies always return `status: "act"` with no `reasoning` field.

## Acceptance Criteria

- [ ] All existing policies return `response.choice.{status, action}`.
- [ ] All examples run successfully end-to-end.
- [ ] Full test suite passes (`python -m pytest`).
- [ ] No references to old `response.decision.action` pattern remain in policy code.

## Implementation Notes

- Can run in parallel with task 2 (reasoning field) since heuristic policies don't emit reasoning.
- Use grep/search to find all `"decision":` patterns in policy return paths.

## Related

- CIP: [0002](../../cip/cip0002_shared-data-model.md)
- Parent task: [2026-03-27_talk-policy-factorization-idk-library](./2026-03-27_talk-policy-factorization-idk-library.md)
- Depends on: [2026-03-28_policy-return-shape-and-decide](./2026-03-28_policy-return-shape-and-decide.md)

## Progress Updates

### 2026-03-28

Task created as sub-task 3 of 6. Clean migration (no compat shim) per design decision.
