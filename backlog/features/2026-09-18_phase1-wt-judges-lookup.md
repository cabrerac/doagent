---
id: "2026-09-18_phase1-wt-judges-lookup"
title: "Phase 1 W/T export, LLM judges, lookup, and costs"
status: "Completed"
priority: "High"
created: "2026-09-18"
last_updated: "2026-09-20"
category: "features"
related_cips:
- "0012"
owner: "Christian Cabrera"
dependencies:
- "2026-09-18_phase1-small-team-scaffold"
tags:
- backlog
- validation
- evaluation
- attribution
---

# Task: Phase 1 W/T export, LLM judges, lookup, and costs

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

From one Phase 1 store **D**, project **W** (Who&When-like outputs) and **T** (TraceElephant-static step I/O). Run Zhang/Chen-style LLM judges on W, T, and D. Run **lookup** on D only. Record judge tokens and recording overhead vs NoOp.

Depends on the small-team scaffold producing D + planted gold.

## Acceptance Criteria

- [x] Documented W and T projection rules; W omits step inputs that D/T have.
- [x] Same LLM judge family on W, T, and D (GPT-4o).
- [x] Lookup on D (who = `actor`, when = step/record id) with the plant rule documented.
- [x] Lookup is reported beside LLM methods, not as a fourth prompting style.
- [x] Judge token counts and recording overhead vs NoOp.
- [x] Run manifest (`run_id`, commit, config).
- [x] Exporters/judges live in validation/examples, not as silent core APIs (open a CIP if they should be library).

## Implementation Notes

Hypothesis to measure, not assume: D ≷ T > W for LLM judges; lookup competitive and cheaper to judge.

No TraceElephant dynamic (counterfactual re-run) in this task.

## Related

- CIP: [0012](../../cip/cip0012_magentic-one-doa-evaluation.md)
- Depends: [2026-09-18_phase1-small-team-scaffold](2026-09-18_phase1-small-team-scaffold.md)

## Progress Updates

### 2026-09-18

Task created (Ready). Scaffold is complete; this is the next implementation session.

Do not start coding until a chat walkthrough of W/T projection rules and judge/lookup I/O.

### 2026-09-19

Added W, T, and D artefacts derived from the same DOAgent run. Added a
documented structured lookup that recovers the planted checker failure.
The full test suite passed. Judges were the next implementation slice.

### 2026-09-19 — judge harness

Moved the paper evaluation to `experiments/attribution/`. Added GPT-4o
all-at-once, step-by-step, and binary-search judges with fake-client tests,
hidden attribution labels, returned model identity, and token accounting.
Added run manifests, recursive output-byte counting, an evaluator that
times the same addition-team run it reports, a NoOp/memory/file
comparison runner, and scores that place lookup beside the LLM judges.
