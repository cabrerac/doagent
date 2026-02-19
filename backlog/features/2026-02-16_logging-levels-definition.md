---
id: "2026-02-16_logging-levels-definition"
title: "Define data-oriented logging levels (0, 1, 2)"
status: "Completed"
priority: "High"
created: "2026-02-16"
last_updated: "2026-02-19"
category: "features"
related_cips:
- "0001"
owner: "Christian Cabrera"
dependencies:
- "2026-02-16_data-model-spec"
tags:
- backlog
- logging
- configuration
---

# Task: Define data-oriented logging levels (0, 1, 2)

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Define the three data-oriented logging levels per the data model spec. Record kinds: agent_update, environment_outcome, trace. Level 0: agent_update (local_knowledge, decision without explanation), environment_outcome; no trace. Level 1: Level 0 + trace + decision.explanation. Level 2: Level 1 + provenance and accountability on envelope.

## Acceptance Criteria
- [x] Level 0 is documented: agent_update (local_knowledge, decision without explanation), environment_outcome; no trace.
- [x] Level 1 adds: trace records and decision.explanation populated in agent_update.
- [x] Level 2 adds: provenance and accountability on envelope for all records.
- [x] Levels are documented in CIP-0001 or data model spec.
- [x] Special case: initial_state id for first env outcome is documented.

## Implementation Notes
- Level 0: communication.
- Level 1: interpretability via decision.explanation.
- Level 2: provenance (authorship) and accountability (responsibility) on envelope.

## Related
- CIP: 0001
- PRs: N/A
- Documentation: CIP-0001, docs/data-model-spec.md §8, docs/library-boundaries.md

## Progress Updates

### 2026-02-16
Task created. Part of REQ-0001/CIP-0001 iteration 2 backlog.

### 2026-02-19
Levels documented in data-model-spec.md §8 and library-boundaries.md §7. Implemented in run_config.py. Marked complete.
