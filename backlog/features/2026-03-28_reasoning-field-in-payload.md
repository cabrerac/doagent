---
id: "2026-03-28_reasoning-field-in-payload"
title: "Add optional reasoning field to agent_update payload"
status: "Completed"
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

- [x] `RecordWriter.on_agent_decide()` passes through `reasoning` from the policy response into the recorded `decision.response`.
- [x] Records with `reasoning` present are correctly written and readable via `inspect("agent_update")`.
- [x] Records without `reasoning` (heuristic policies) are unchanged and valid.
- [x] Tests cover: record with reasoning, record without reasoning, reasoning content is queryable from inspect output.

## Implementation Notes

- The `reasoning` field is whatever the policy returns — the library does not prescribe its internal structure (could be chain-of-thought string, list of steps, tool call log, etc.).
- Logging levels were **swapped** during this task's implementation: Level 1 now gates provenance + accountability; Level 2 gates explanation + reasoning. `reasoning` is stripped from `decision.response` below Level 2 by `RecordWriter`.

## Related

- CIP: [0002](../../cip/cip0002_shared-data-model.md)
- Parent task: [2026-03-27_talk-policy-factorization-idk-library](./2026-03-27_talk-policy-factorization-idk-library.md)
- Depends on: [2026-03-28_policy-return-shape-and-decide](./2026-03-28_policy-return-shape-and-decide.md)

## Progress Updates

### 2026-03-28

Task created as sub-task 2 of 6. Design decision: Option B (structured field on existing agent_update) chosen over Option A (new record kind) because reasoning is only meaningful alongside the decision it produced.

### 2026-03-28 (completed)

Implemented reasoning gating and logging level swap:

- **Logging level swap:** Level 1 now gates provenance + accountability (structural metadata); Level 2 gates explanation + reasoning (interpretability content). This was a deliberate re-ordering to separate structural traceability (Level 1) from content-heavy interpretability (Level 2).
- **`run_config.py`:** `should_include_provenance_accountability` moved to `>= 1`; `should_include_explanation` moved to `>= 2`; new `should_include_reasoning` at `>= 2`.
- **`record_writer.py`:** Imports `should_include_reasoning`; strips `reasoning` from `decision.response` below Level 2.
- **`test_logging_levels.py`:** All three level tests updated to match new semantics; Level 1 now asserts provenance but no explanation; Level 2 asserts both.
- **`data-model-spec.md`:** Section 8 table and §3.1 updated to document new level semantics and `reasoning` field.
- All 95 tests pass (3 skipped: push_demo env dependency).
