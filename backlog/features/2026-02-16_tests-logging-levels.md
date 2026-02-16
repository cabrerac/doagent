---
id: "2026-02-16_tests-logging-levels"
title: "Add tests for logging levels"
status: "Proposed"
priority: "Medium"
created: "2026-02-16"
last_updated: "2026-02-16"
category: "features"
related_cips:
- "0001"
owner: "Christian Cabrera"
dependencies:
- "2026-02-16_wire-records-to-level"
tags:
- backlog
- tests
- logging
---

# Task: Add tests for logging levels

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Add unit and/or integration tests that verify logging level behaviour. At level 0: agent_update (no decision.explanation), environment_outcome, trace. At level 1: decision.explanation populated. At level 2: provenance and accountability on envelope.

## Acceptance Criteria

- [ ] Test: Level 0 run produces agent_update without decision.explanation.
- [ ] Test: Level 1 run produces agent_update with decision.explanation populated.
- [ ] Test: Level 2 run has provenance and accountability on all record envelopes.
- [ ] Tests are deterministic and run via pytest or unittest.

## Implementation Notes

- Use in-memory adapter for fast tests; assert on record kinds and presence of fields.
- May use gridworld or a minimal stub scenario.

## Related

- CIP: 0001
- PRs: N/A
- Documentation: Logging levels definition

## Progress Updates

### 2026-02-16
Task created. Part of REQ-0001 iteration 2 backlog.
