---
id: "2026-03-28_reasoning-field-in-payload"
title: "Add optional reasoning field to agent_update payload"
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
- reasoning-trace
---

# Task: Add optional reasoning field to agent_update payload

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Enable policy factorization (Z vs A split) by recording the reasoning trace as a structured field inside the existing `agent_update` record. This is **Option B** from the factorization design discussion: reasoning lives inside the `agent_update` payload (not a separate record kind), because inspecting reasoning traces only makes sense in the context of the whole decision.

**Record shape after this task:**

```json
{
  "kind": "agent_update",
  "payload": {
    "local_knowledge": {...},
    "decision": {
      "request": {...},
      "response": {
        "choice": {"status": "act", "action": 4},
        "reasoning": {"trace": "...", "steps": [...]},
        "explanation": "..."
      }
    }
  }
}
```

Reasoning stays inside `decision.response` (no duplication to a top-level payload field). Policies that don't produce reasoning (heuristic/degenerate) omit the field or set it to `null`.

## Acceptance Criteria

- [ ] `RecordWriter.on_agent_decide()` passes through `reasoning` from the policy response into the recorded `decision.response`.
- [ ] Records with `reasoning` present are correctly written and readable via `inspect("agent_update")`.
- [ ] Records without `reasoning` (heuristic policies) are unchanged and valid.
- [ ] Tests cover: record with reasoning, record without reasoning, reasoning content is queryable from inspect output.

## Implementation Notes

- The `reasoning` field is whatever the policy returns — the library does not prescribe its internal structure (could be chain-of-thought string, list of steps, tool call log, etc.).
- Logging level may control whether reasoning is included (similar to how `explanation` is controlled). To discuss during Stage 3 for this task.

## Related

- CIP: [0002](../../cip/cip0002_shared-data-model.md)
- Parent task: [2026-03-27_talk-policy-factorization-idk-library](./2026-03-27_talk-policy-factorization-idk-library.md)
- Depends on: [2026-03-28_policy-return-shape-and-decide](./2026-03-28_policy-return-shape-and-decide.md)

## Progress Updates

### 2026-03-28

Task created as sub-task 2 of 6. Design decision: Option B (structured field on existing agent_update) chosen over Option A (new record kind) because reasoning is only meaningful alongside the decision it produced.
