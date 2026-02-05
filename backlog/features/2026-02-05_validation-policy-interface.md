---
id: "2026-02-05_validation-policy-interface"
title: "Define reusable policy interface for validation"
status: "Proposed"
priority: "High"
created: "2026-02-05"
last_updated: "2026-02-05"
category: "features"
related_cips:
- "0010"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- validation
- games
---
# Task: Define reusable policy interface for validation

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Define a policy interface/config that maps to the FunctionAgent decision function so policies are reusable across scenarios (REQ-0011/0012 later).

## Acceptance Criteria
- [ ] Policy interface maps to FunctionAgent/DecisionAgent decision function.
- [ ] Policy assignment is configurable per agent.
- [ ] Policy design is scenario-agnostic.

## Implementation Notes
Keep policies lightweight and deterministic with a seeded RNG for tests.

## Related
- CIP: 0010
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-02-05
Task created.
