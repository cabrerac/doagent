---
id: "2026-02-16_tests-trace-dedup"
title: "Add tests for trace graph and state deduplication"
status: "Completed"
priority: "Medium"
created: "2026-02-16"
last_updated: "2026-02-21"
category: "features"
related_cips:
- "0002"
owner: "Christian Cabrera"
dependencies:
- "2026-02-16_state-lookup-index"
- "2026-02-16_trace-schema"
tags:
- backlog
- tests
- trace
- deduplication
---

# Task: Add tests for trace graph and state deduplication

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Add tests that verify the trace graph and state deduplication. When equivalent environment states occur (e.g. revisiting same state), outcomes should be deduplicated and traces should form a proper graph with from_id, to_id, enabled_by_id. Tests should cover: initial_state reference, transition chains, and state reuse when hash matches.

## Acceptance Criteria

- [x] Test: First trace has from_id = "initial_state".
- [x] Test: Trace chain forms valid transitions (from -> to, enabled_by).
- [x] Test: Equivalent states deduplicate; to_id points to existing outcome.
- [x] Test: Multiple traces can point to the same outcome (state reuse).
- [x] Tests pass with JSON adapter that implements state lookup index.

## Implementation Notes

- Create minimal scenario that produces deterministic, repeatable states.
- Assert on trace structure and outcome id reuse.

## Related

- CIP: 0002
- PRs: N/A
- Documentation: Trace schema, state dedup contract

## Progress Updates

### 2026-02-16
Task created. Part of REQ-0001/CIP-0002 iteration 2 backlog.

### 2026-02-21
Created `tests/test_trace_dedup.py` with 12 tests across 3 test classes:
- **TestTraceGraph** (4 tests, no dedup): first trace references INITIAL_STATE_ID; trace chain has valid from/to/enabled_by links; traces reference real agent_updates; outcomes are all unique without dedup.
- **TestStateDedup** (6 tests): cycling env revisiting 3 states over 6 rounds produces exactly 3 outcomes; multiple traces share to_id; first-round traces still reference initial_state; default_state_hash (includes round) prevents dedup; adapter index has 3 entries; FileSharedData dedup works identically.
- **TestNoHashFnNoDedup** (2 tests): without state_hash_fn all outcomes are unique; index stays empty.
- Uses a `CyclingEnv` that cycles through 3 deterministic states and a `_state_only_hash` that hashes only observations.
- All 61 tests pass (49 existing + 12 new).
