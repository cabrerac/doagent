---
id: "2026-02-16_run-api-level-config"
title: "High-level run API using logging level config"
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
- api
- validation
---

# Task: High-level run API using logging level config

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description
Provide a high-level run API (or extend the validation runner API) that accepts logging level configuration and wires it through the run. Users configure level once; the run executes with the appropriate record set. This task focuses on the orchestration surface, not the internal wiring (that's wire-records-to-level).

## Acceptance Criteria
- [ ] Run/validation entry point accepts logging_level (0, 1, 2) as parameter or config.
- [ ] Config flows to shared_data and record writers.
- [ ] Gridworld and push validation examples demonstrate level config usage.
- [ ] Documentation shows how to run with different levels.

## Implementation Notes
- May extend gridworld_validation.py and push_validation.py.
- Consider argparse or config file for CLI usage.
- Keep the API minimal; avoid over-engineering.

## Related
- CIP: 0001
- PRs: N/A
- Documentation: Examples, AGENTS.md

## Progress Updates

### 2026-02-16
Task created. Part of REQ-0001/CIP-0001 iteration 2 backlog.
