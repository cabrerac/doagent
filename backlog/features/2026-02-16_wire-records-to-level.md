---
id: "2026-02-16_wire-records-to-level"
title: "Wire record writing to configured logging level"
status: "Completed"
priority: "High"
created: "2026-02-20"
last_updated: "2026-02-17"
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
The library must write records according to the configured logging level. Record kinds: agent_update, environment_outcome, trace. Level 0: agent_update, environment_outcome (no trace, no decision.explanation). Level 1: adds trace and decision.explanation. Level 2: adds provenance and accountability on envelope. Gate whether to write trace, populate decision.explanation, and populate envelope provenance/accountability based on level.

## Acceptance Criteria
- [x] At level 0, agent_update and environment_outcome are written; no trace; decision has no explanation.
- [x] At level 1, trace is written; decision.explanation is populated in agent_update.
- [x] At level 2, provenance and accountability are populated on all record envelopes.
- [x] At levels 0 and 1, provenance/accountability may be omitted or minimal.
- [x] Validation runs produce expected record content for each level.
- [x] RecordWriter exists; scenarios call hooks, not new_record/new_agent_update_record/new_trace_record directly.

## Implementation Notes
- Use **hooks** for record writing: library defines hook points (on_agent_decide, on_env_step, after_outcome); a built-in hook writes records based on level. Transparent for users—they invoke agents and step env; hooks fire automatically.
- Alternatives considered: built-in side-effects (recording inside agent.decide/step impl), event/observer, wrapper/decorator. Chosen: hooks—clean extension point, decoupled record-writing, optionally extensible for user hooks later.
- Gate trace, decision.explanation, and envelope fields at hook implementation.
- No separate explanation records; explanation is a field inside agent_update.payload.decision.
- See docs/library-boundaries.md §4 (Configured Once), §8 (Identity), §13 (Implications).

**Phased implementation:**
- Phase 1: Create RecordWriter (record_writer.py) with on_agent_decide, on_env_step, after_outcome. RecordWriter holds shared_data, run_config; encapsulates all new_* calls.
- Phase 2: Refactor gridworld and push scenarios to use RecordWriter; remove direct new_* imports from scenarios.
- Phase 3 (optional): Wire FunctionAgent and step helpers to call RecordWriter when user invokes them.

## Related
- CIP: 0001
- PRs: N/A
- Documentation: docs/library-boundaries.md, docs/data-model-spec.md §8

## Progress Updates

### 2026-02-16
Task created. Part of REQ-0001/CIP-0001 iteration 2 backlog.

### 2026-02-17
Level gating implemented (RunConfig, helpers, conditional writes in scenarios). Tests pass.

### 2026-02-20
RecordWriter implemented (doagent/core/record_writer.py). Hooks: on_agent_decide, on_outcome_and_traces. Gridworld and push scenarios refactored to use RecordWriter; removed all direct new_* imports from scenarios. All 35 tests pass. Marked complete. Next: transparent user API via Session (new task).
