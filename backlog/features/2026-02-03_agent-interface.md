---
id: "2026-02-03_agent-interface"
title: "Define model-agnostic agent interface"
status: "Completed"
priority: "High"
created: "2026-02-03"
last_updated: "2026-02-03"
category: "features"
related_cips:
- "0005"
owner: "Christian Cabrera"
dependencies:
- "2026-02-03_decision-models"
tags:
- backlog
- model-agnostic
---

# Task: Define model-agnostic agent interface

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Define a minimal agent interface with a `decide` method.

## Acceptance Criteria
- [x] Interface method signature is defined and documented.
- [x] Interface uses the decision request/response models.

## Implementation Notes
Keep the interface small and synchronous for the first iteration.

## Related
- CIP: 0005
- PRs: N/A
- Documentation: N/A

## Progress Updates

### 2026-02-03
Task created.

### 2026-02-03
Added `DecisionAgent` protocol and linked decision models.
