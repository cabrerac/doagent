---
id: "2026-03-28_policy-return-shape-and-decide"
title: "Update policy return shape to choice and update SessionAgent.decide()"
status: "Ready"
priority: "High"
created: "2026-03-28"
last_updated: "2026-03-28"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- policy-factorization
- idk
- breaking-change
---

# Task: Update policy return shape to choice and update SessionAgent.decide()

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Replace the inner `response.decision` object (containing `action`) with `response.choice`, a structured commit object containing `status` and `action`. This is the foundational change for policy factorization and IDK support.

**New policy return shape:**

```python
response = {
    "choice": {"status": "act", "action": 4},
    "reasoning": {...},       # optional, see task 2
    "explanation": "...",     # optional, by logging level
}
```

**`choice` fields:**
- `status`: `"act"` | `"abstain"` | `"error"`
- `action`: env primitive when `status == "act"`; `null` when abstaining or erroring
- `error` (optional): error details when `status == "error"`

**`SessionAgent.decide()` changes:**
- Read `response["choice"]["action"]` instead of `response.get("decision", {}).get("action")`
- Return `{"action": response["choice"]["action"], "response": response}` (same shape as today, but sourced from `choice`)

**`RecordWriter.on_agent_decide()` changes:**
- If any assembly logic references the old `decision` key inside the response, update to `choice`.

**No backward-compat shim** — old policies and examples will be updated in task 3.

## Acceptance Criteria

- [ ] Policy callable contract documented: must return `response` with `choice: {status, action}`.
- [ ] `SessionAgent.decide()` reads from `response["choice"]`.
- [ ] `Session.record_decision()` updated consistently.
- [ ] `RecordWriter.on_agent_decide()` records contain `response.choice` (not `response.decision`).
- [ ] Existing tests updated to use new shape; full suite passes (`python -m pytest`).

## Implementation Notes

- This is the foundational task; tasks 2-6 depend on or parallel this.
- The outer `payload.decision` key (request + response bundle) is unchanged.
- `Session.record_update()` (non-decision updates, e.g. hub summaries) remains as-is with empty decision dict.

## Related

- CIP: [0002](../../cip/cip0002_shared-data-model.md)
- Parent task: [2026-03-27_talk-policy-factorization-idk-library](./2026-03-27_talk-policy-factorization-idk-library.md)

## Progress Updates

### 2026-03-28

Task created as sub-task 1 of 6 for policy factorization and IDK implementation. Design decisions captured in CIP-0002 progress update (2026-03-28).
