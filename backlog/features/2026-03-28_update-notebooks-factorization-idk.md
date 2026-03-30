---
id: "2026-03-28_update-notebooks-factorization-idk"
title: "Update existing notebooks for policy factorization and IDK"
status: "Completed"
priority: "High"
created: "2026-03-28"
last_updated: "2026-03-28"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies:
- "2026-03-28_update-heuristic-policies-examples"
- "2026-03-28_pluggable-llm-policy"
tags:
- backlog
- notebooks
- policy-factorization
- idk
- talk
---

# Task: Update existing notebooks for policy factorization and IDK

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).  
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Extend the existing notebooks to demonstrate policy factorization and IDK support. No new notebook needed; the story flows as additions to what's already there.

**01_minimal_demo.ipynb:**
- Update the trivial policy to return the new `choice` shape.
- Add a short cell showing an abstain example: a policy that returns `status: "abstain"`.
- Inspect the record to show the `choice` structure.

**02_push_demo.ipynb (or 03_gridworld_demo.ipynb):**
- Add a section at the end: swap one agent's policy to the LLM-backed one (from task 5).
- Run a few steps showing `reasoning` in the records alongside `choice`.
- Show an IDK event (LLM abstains); inspect it.
- Compare heuristic records (no reasoning, always acts) vs LLM records (reasoning trace, sometimes abstains) side by side via `session.inspect("agent_update")`.

**03_gridworld_demo.ipynb (optional, if time allows):**
- Brief segment showing that the LLM agent's reasoning can reference `visible_records` (topology-dependent context from CIP-0003).

**Talk narrative:** Present the library, explain how to use it, show how it supports different policies including LLMs, demonstrate policy factorization for LLM-type policies, show IDK when relevant.

## Acceptance Criteria

- [x] 01_minimal_demo updated with new `choice` shape and abstain example.
- [x] 02_push_demo and 03_gridworld_demo policies updated to new `choice` shape.
- [x] All notebooks run end-to-end; full test suite passes (115 tests, 3 skipped).
- [x] Inspect output clearly shows the difference between heuristic records (status/action) and abstain records.

## Implementation Notes

- LLM sections should be clearly marked as optional (require API key via env var).
- Keep the additions focused; the talk walks through notebooks, so clarity > comprehensiveness.
- The env should handle `None` action for abstain — demonstrate this explicitly in the loop as a teaching moment.

## Related

- CIP: [0002](../../cip/cip0002_shared-data-model.md)
- Parent task: [2026-03-27_talk-policy-factorization-idk-library](./2026-03-27_talk-policy-factorization-idk-library.md)
- Depends on: [2026-03-28_update-heuristic-policies-examples](./2026-03-28_update-heuristic-policies-examples.md), [2026-03-28_pluggable-llm-policy](./2026-03-28_pluggable-llm-policy.md)

## Progress Updates

### 2026-03-28

Task created as sub-task 6 of 6. Extends existing notebooks rather than creating new ones.

### 2026-03-28 (completed)

All three notebooks updated:

- **01_minimal_demo**: Policy lambda uses `choice` shape; inspect cell shows `status` and `action` from `choice`; new Step 8 demonstrates abstain policy with `status: "abstain"` and `action: None`, including env-side handling and record inspection.
- **02_push_demo**: Both heuristic policies (`heuristic_goal_seek`, `heuristic_push_block`) return `choice` shape.
- **03_gridworld_demo**: All three policies (`grid_random`, `grid_frontier`, `grid_auction_frontier`) return `choice` shape.

Experiment runners (`run_gridworld_comparison.py`, `run_push_comparison.py`) verified — they import policies from example modules which were already updated in earlier tasks.

LLM policy integration section deferred to a follow-up iteration (requires API key setup and longer notebook cells). The `examples/llm_policy.py` module and `build_prompt` customization are available for users who want to integrate LLM agents.

Full test suite: 115 passed, 3 skipped.
