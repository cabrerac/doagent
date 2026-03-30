---
id: "2026-03-28_policy-return-shape-and-decide"
title: "Update policy return shape to choice and update SessionAgent.decide()"
status: "Completed"
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

- [x] Policy callable contract documented: must return `response` with `choice: {status, action}` (`docs/data-model-spec.md` §3.1).
- [x] `SessionAgent.decide()` reads from `response["choice"]`.
- [x] `Session.record_decision()` updated consistently (passes through external `response`; callers supply `choice` shape; no code change required).
- [x] `RecordWriter.on_agent_decide()` records contain `response.choice` (writer passes policy response through unchanged; no `decision` key assembly).
- [x] Existing tests updated to use new shape; full suite passes (`python -m pytest`).

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

### 2026-03-28 (implementation)

**Completed.** Inside-out implementation: `SessionAgent.decide()` reads `response["choice"]["action"]`; analysis modules (`interpretability`, `provenance`, `traceability`) read `payload.decision.response.choice.action` from stored records; examples (`push_demo`, `gridworld` policies, `minimal_usage`) and tests updated to return/assert `choice` with `status: "act"`. `RecordWriter.on_agent_decide` unchanged (payload mirrors policy response). `pytest`: 95 passed, 3 skipped (push validation; PettingZoo not installed). Data model spec §3.1 documents the policy `choice` contract. Follow-on: task `2026-03-28_reasoning-field-in-payload` next on critical path.
