---
id: "2026-02-16_tests-trace-dedup"
title: "Add tests for trace graph and state deduplication"
status: "Proposed"
priority: "Medium"
created: "2026-02-16"
last_updated: "2026-02-16"
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

- [ ] Test: First trace has from_id = "initial_state".
- [ ] Test: Trace chain forms valid transitions (from -> to, enabled_by).
- [ ] Test: Equivalent states deduplicate; to_id points to existing outcome.
- [ ] Test: Multiple traces can point to the same outcome (state reuse).
- [ ] Tests pass with JSON adapter that implements state lookup index.

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
