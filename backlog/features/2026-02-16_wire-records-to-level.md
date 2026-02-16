---
id: "2026-02-16_wire-records-to-level"
title: "Wire record writing to configured logging level"
status: "Proposed"
priority: "High"
created: "2026-02-16"
last_updated: "2026-02-16"
category: "features"
related_cips:
- "0001"
owner: "Christian Cabrera"
dependencies:
- "2026-02-16_logging-level-config"
tags:
- backlog
- logging
- shared-data
---

# Task: Wire record writing to configured logging level

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
The library must write records according to the configured logging level. Record kinds: agent_update, environment_outcome, trace. Level 0: all three, but agent_update.decision has no explanation. Level 1: same records, decision.explanation populated. Level 2: same records, provenance and accountability on envelope. Gate whether to populate decision.explanation and envelope provenance/accountability based on level.

## Acceptance Criteria
- [ ] At level 0, agent_update, environment_outcome, trace are written; decision has no explanation.
- [ ] At level 1, decision.explanation is populated in agent_update.
- [ ] At level 2, provenance and accountability are populated on all record envelopes.
- [ ] At levels 0 and 1, provenance/accountability may be omitted or minimal.
- [ ] Validation runs produce expected record content for each level.

## Implementation Notes
- Gate decision.explanation and envelope fields at record creation (shared_data, scenario, reporter).
- No separate explanation records; explanation is a field inside agent_update.payload.decision.
- Consider a shared helper for level checks.

## Related
- CIP: 0001
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-02-16
Task created. Part of REQ-0001/CIP-0001 iteration 2 backlog.
