---
id: "2026-02-19_session-api"
title: "Transparent user API via Session (env wrapping, agent recording)"
status: "Completed"
priority: "High"
created: "2026-02-19"
last_updated: "2026-02-20"
category: "features"
related_cips:
- "0001"
owner: "Christian Cabrera"
dependencies:
- "2026-02-16_wire-records-to-level"
- "2026-02-16_logging-level-config"
tags:
- backlog
- api
- transparency
- session
---

# Task: Transparent user API via Session (env wrapping, agent recording)

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Implement a Session-based API so users configure DOAgent once and then use their normal run loop. The library records agent decisions, environment outcomes, and traces transparently—no RecordWriter, INITIAL_STATE_ID, prev_outcome_id, or record helpers in user code.

**User code should look like:**

```python
session = doagent.Session(shared_data, run_config)
env = session.wrap_env(my_env)              # or with adapter for custom envs
agents = session.create_agents(configs)

observations = env.reset(seed=seed)
for round_id in range(1, rounds + 1):
    actions = {}
    for agent_id, agent in agents.items():
        response = agent.decide(observations[agent_id], round_id)
        actions[agent_id] = response["action"]
    observations, rewards, done = env.step(actions)
```

**User imports:** `doagent.Session`, `InMemorySharedData`, `RunConfig`, `PolicyRegistry`.
**User does NOT import:** `RecordWriter`, `INITIAL_STATE_ID`, `DecisionRequest`, `new_record`, `new_provenance`, etc.

## Alternatives Considered

- **Step recorder (explicit per-step call):** User calls `step_recorder.step(...)` after env.step. Less transparent—user must remember to call it.
- **Standalone functions (no Session):** `doagent.wrap(env, shared_data, run_config)` and `doagent.create_agents(...)` — user passes config to each call separately.
- **Session object:** User creates one Session, wraps components through it. Config passed once; internal state (prev_outcome_id, round tracking) managed centrally.

**Selected:** Session object.

**Rationale:** Single config point; tracks internal state (prev_outcome_id) across components; aligns with "configure once, applied automatically" from library-boundaries.md §4.

## Acceptance Criteria

- [x] `Session` class exists, accepts `shared_data` and `run_config`.
- [x] `session.wrap_env(env)` returns a wrapped env whose `step()` records outcome and traces internally.
- [x] `session.wrap_env(env, adapter=...)` supports custom env return shapes (hybrid adapter).
- [x] Auto-detection of common env conventions (dict, tuple, attribute-based) with clear error on unknown.
- [x] `session.create_agents(configs)` returns agent objects whose `decide()` records agent_update internally.
- [x] `agent.decide(observation, round_id)` is the user-facing signature—no DecisionRequest construction needed.
- [x] Validation scenarios (gridworld, push) refactored to use Session, demonstrating transparent API.
- [x] No imports of RecordWriter, INITIAL_STATE_ID, new_record, new_provenance in scenario code.
- [x] All existing tests pass; new tests verify Session-based usage.
- [x] Integration tests verify full-stack wiring (real env + real policies + Session).

## Implementation Notes

- **Session** holds: shared_data, run_config, RecordWriter (internal), prev_outcome_id state.
- **Wrapped env:** Delegates to user's env for reset/step; intercepts step result to call RecordWriter.on_outcome_and_traces. Tracks prev_outcome_id internally.
- **Hybrid env adapter:** Default auto-detects common return shapes (dict with observations/rewards/done keys; Gymnasium tuple; object with attributes). User can override with `adapter=lambda result: {"observations": ..., "rewards": ..., "done": ...}`. Clear error if auto-detection fails and no adapter provided.
- **Wrapped agents:** Each agent wraps user's policy callable. `decide(observation, round_id)` builds DecisionRequest internally, calls policy, calls RecordWriter.on_agent_decide, returns action-level response.
- **PolicyRegistry** remains user-facing for registering policy factories.
- See docs/library-boundaries.md §2 (User vs Library), §3 (Records Are Internal), §4 (Configured Once), §13 (Implications).

## Related

- CIP: 0001
- PRs: N/A
- Documentation: docs/library-boundaries.md
- Supersedes user-facing surface of: 2026-02-16_run-api-level-config

## Progress Updates

### 2026-02-19
Task created. Based on brainstorming: scenarios are usage examples and should demonstrate transparency. Session API selected over step recorder and standalone functions.

### 2026-01-28 (initial)
Implementation of core Session API:
- Created `doagent/core/session.py` with `Session`, `WrappedEnv`, `SessionAgent` classes.
- `WrappedEnv` auto-detects common step result formats (dict, tuple, attribute-based) with user-overridable adapter.
- `SessionAgent.decide(observation, round_id)` builds DecisionRequest internally, calls policy, records agent_update via RecordWriter.
- Added `session.record_decision()` for externally-computed decisions (multiprocessing).
- Added `session.record_update()` for non-decision updates (hub summaries).
- Refactored push and gridworld scenarios to use Session internally.
- Exported `Session` from `doagent` top-level package.

### 2026-01-28 (decentralisation + examples rewrite)
Session moved from library internals to user-facing code. All three DOA principles now supported:
- **Shared-data model**: `session.wrap_env()`, `session.create_agents()` record transparently.
- **Decentralisation**: Added `session.visible_records(agent_id, kind)` with topology-aware filtering (CENTRALISED, PEER_TO_PEER, FEDERATED). Session accepts `topology`, `visibility`, `hub_id` parameters.
- **Openness**: Records accessible via `shared_data.listen()`, extensible agents/policies via PolicyRegistry.
- Rewrote `examples/validation/gridworld/gridworld_validation.py` to use Session directly with user-owned run loop, demonstrating all three principles.
- Rewrote `examples/validation/push/push_validation.py` to use Session directly.
- 10 Session tests (3 new for topology filtering) + full suite: 42 passed, 3 skipped.

### 2026-01-28 (integration tests + bug fixes)
Two wiring bugs discovered while running the gridworld example:
1. `build_shared_map` couldn't extract cells from records — `local_knowledge` structure changed to `{"observation": {...}, "shared_map": {...}}` but extraction still looked for `local_knowledge.cells`.
2. `_move_towards` returned action 1 (left) when src == dest, causing frontier agents to drift left and get stuck.

Both bugs were invisible to unit tests because stubs don't exercise real observation structures. Added 7 integration tests in `tests/test_session_integration.py`:
- `test_policies_receive_correct_observation_structure`: verifies position, width, height, cells present.
- `test_agents_actually_move`: asserts agent positions change after 10 rounds.
- `test_shared_map_accumulates_cells`: shared map grows from records.
- `test_action_is_valid_integer`: actions are valid ints in {0,1,2,3,4}.
- `test_records_have_correct_structure`: `local_knowledge.observation.cells` exists.
- `test_peer_to_peer_topology_filters_records`: topology filtering works end-to-end.
- `test_coverage_increases_over_rounds`: exploration discovers new cells over time.

Also added `inputs` kwarg to `SessionAgent.decide()` for structured request inputs.
Full suite: 49 passed, 3 skipped.
