---
id: "2026-02-19_session-api"
title: "Transparent user API via Session (env wrapping, agent recording)"
status: "Proposed"
priority: "High"
created: "2026-02-19"
last_updated: "2026-02-19"
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

- [ ] `Session` class exists, accepts `shared_data` and `run_config`.
- [ ] `session.wrap_env(env)` returns a wrapped env whose `step()` records outcome and traces internally.
- [ ] `session.wrap_env(env, adapter=...)` supports custom env return shapes (hybrid adapter).
- [ ] Auto-detection of common env conventions (dict, tuple, attribute-based) with clear error on unknown.
- [ ] `session.create_agents(configs)` returns agent objects whose `decide()` records agent_update internally.
- [ ] `agent.decide(observation, round_id)` is the user-facing signature—no DecisionRequest construction needed.
- [ ] Validation scenarios (gridworld, push) refactored to use Session, demonstrating transparent API.
- [ ] No imports of RecordWriter, INITIAL_STATE_ID, new_record, new_provenance in scenario code.
- [ ] All existing tests pass; new tests verify Session-based usage.

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
