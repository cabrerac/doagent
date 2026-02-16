---
id: "2026-02-16_logging-levels-definition"
title: "Define data-oriented logging levels (0, 1, 2)"
status: "Proposed"
priority: "High"
created: "2026-02-16"
last_updated: "2026-02-16"
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
Define the three data-oriented logging levels per the data model spec. Record kinds: agent_update, environment_outcome, trace. Level 0: agent_update (with local_knowledge, decision), environment_outcome, trace. Level 1: same records but with decision.explanation populated. Level 2: same records plus provenance and accountability on envelope.

## Acceptance Criteria
- [ ] Level 0 is documented: agent_update (local_knowledge, decision without explanation), environment_outcome, trace.
- [ ] Level 1 adds: decision.explanation populated in agent_update.
- [ ] Level 2 adds: provenance and accountability on envelope for all records.
- [ ] Levels are documented in CIP-0001 or data model spec.
- [ ] Special case: initial_state id for first env outcome is documented.

## Implementation Notes
- Level 0: communication.
- Level 1: interpretability via decision.explanation.
- Level 2: provenance (authorship) and accountability (responsibility) on envelope.

## Related
- CIP: 0001
- PRs: N/A
- Documentation: CIP-0001, data model spec

## Progress Updates

### 2026-02-16
Task created. Part of REQ-0001/CIP-0001 iteration 2 backlog.
