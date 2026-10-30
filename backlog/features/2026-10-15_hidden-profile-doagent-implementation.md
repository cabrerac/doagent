---
id: "2026-10-15_hidden-profile-doagent-implementation"
title: "Implement Hidden Profile with a DOAgent session"
status: "In Progress"
priority: "High"
created: "2026-10-15"
last_updated: "2026-10-30"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies:
- "2026-10-15_hidden-profile-environment"
tags:
- backlog
- doagent
- hidden-profile
- information-flow
---

# Task: Implement Hidden Profile with a DOAgent Session

## Description

Run the Hidden Profile rules and scripted policies through a DOAgent session.
Produce the artifacts a DOAgent user would actually have after the run, with nothing added for the study.

## Motivation

One side of the comparison needs to be an honest DOAgent run.
If the session is configured to record more than a normal user would configure, the comparison measures our tuning rather than the framework.

## Justification

The pattern already exists in this repository.
`experiments/multiagentbench/run_werewolf_doagent.py` builds a session from config, wraps the environment, creates agents from policies, and reads outcomes back with `session.inspect`.
Following that file keeps the two Werewolf runs and the two Hidden Profile runs comparable with each other.

## Design

### Session construction

Follow the existing Werewolf runner.

```python
config = {
    "shared_data": {"type": "file"},
    "run_config": {"logging_level": logging_level},
    "topology": {"mode": "peer_to_peer"},
    "policies": {
        agent_id: scripted_policy(agent_id)
        for agent_id in rules.agents
    },
    "scenario_name": "hidden_profile_doagent",
    "output_base": str(OUTPUT_BASE),
}
session = Session.from_config(config)
wrapped = session.wrap_env(rules, env_actor="hidden_profile_env")
agents = session.create_agents(
    [
        {"id": agent_id, "policy": {"name": agent_id, "params": {}}}
        for agent_id in rules.agents
    ],
    wrapped,
)
```

The topology is `peer_to_peer` because the ring has no coordinator.
Do not switch to a centralised mode for convenience.

### The loop

```python
observations = wrapped.reset(seed=seed)
for round_index in range(rules.horizon):
    actions = {
        agent.id: agent.decide(
            observations[agent.id],
            round_id=f"round-{round_index}",
            inputs=observations[agent.id],
        )["action"]
        for agent in agents
    }
    observations, *_ = wrapped.step(actions)
session.close()
```

Pass the observation through `inputs` as well as the positional argument.
That is what puts the decision inputs into the record, and it is what the decoder later reads.

### Logging levels

Run every level the comparison needs.

```text
0  minimal
1  default
2  explanations
```

Level is a run parameter, not a code branch.
The same script must produce all three.

### Artifacts

The run writes the session store under `output_base`.
Export the three record kinds the decoder consumes.

```python
records = {
    "outcome": list(session.inspect("outcome")),
    "agent_update": list(session.inspect("agent_update")),
    "trace": list(session.inspect("trace")),
}
```

Write them to `records.json` beside the scoring sink, but never merge the two files.

### What is forbidden

Do not write any file the rules did not already produce.
Do not add fields to records to make a query answerable.
Do not read the scoring sink from inside the run.
If a query cannot be answered from the DOAgent artifacts, that is a result, not a bug.

## Execution Plan

1. Add `experiments/information_flow/hidden_profile/run_doagent.py`.
2. Mirror the argument surface of the Werewolf runner: `--seed`, `--logging-level`, `--output-base`, `--rounds`.
3. Build the session, wrap the rules, create the agents.
4. Run the loop with a fixed seed and close the session.
5. Export `records.json` and the neutral event stream for the same episode.
6. Assert the neutral event stream matches the one the rules produce with no framework attached.
7. Add `tests/test_hidden_profile_doagent.py`.
8. Run seeds at all three logging levels and record where the artifacts land.

## Trajectory Parity

Parity is defined on the neutral event sequence, not on the artifacts.
After the run, compare the events the rules emitted under the session against the events the same seed emits with no framework attached.
They must be identical in order, identity, and content.
If they differ, the session is changing the system and the comparison is void until that is fixed.

## Acceptance Criteria

- [x] The run uses the public session API only.
- [x] Policies and rules are imported unchanged from the environment task.
- [ ] A fixed seed reproduces the artifacts byte for byte at a given logging level.
- [x] The neutral event sequence is identical to the no-framework run for the same seed.
- [x] All three logging levels run from the same script.
- [x] `records.json` exports `outcome`, `agent_update`, and `trace`.
- [x] No study-specific field is added to any record.
- [x] The scoring sink is never opened by the run.
- [x] Token and wall-clock cost are recorded for each logging level.

## Implementation Notes

`SessionAgent.decide` returns a mapping with `action` and `response`.
Take `action` for the environment and leave `response` to the record.

Keep the runner thin.
Any logic that is not session plumbing belongs in the rules or the policies, where the other implementation can reach it.

## Dependencies and Gate

Blocked on the environment task.
Scored only once Gate 3 on implementation fairness is satisfied, which requires this task and the MARBLE task to be reviewed side by side.

## Related

- CIP: 0015
- Requirement: REQ-0015

## Progress Updates

### 2026-10-15

Task created. Design follows the existing Werewolf DOAgent runner rather than inventing a session pattern.

### 2026-10-23

`run_doagent.py` plays one episode through `Session.from_config`, `wrap_env`, `create_agents`, and `decide`.
Seed 17 matches the no-framework episode at logging levels 0, 1, and 2.
`records.json` exports `outcome`, `agent_update`, and `trace`.
The session has no `env_update` kind.
The environment step is an `outcome` record, and level 1 adds a `trace` from each decision to that outcome.
The scripted policy now accepts lists as well as tuples, because the session serializes tuples before the policy sees them.
Byte-for-byte artifact replay remains open.
The run is unscored.

Seed 17 was timed at logging level 1.
One untimed pass was followed by five timed passes, each in a fresh folder.
The median on this machine was 0.008072 seconds.
Tokens and model calls were zero.
The other logging levels have not been timed, and the run is unscored.

### 2026-10-29

A second run of the same seed does not write the same bytes.
The library gives each record a new id and a clock.
With those fields removed, the two files match at logging levels 0, 1, and 2.
Links are compared by each record's place in the file.
The byte-for-byte line fails.
The library is left unchanged.
Each time is the middle of five fresh runs after one warm-up, on this machine.
Level 0 took 0.027019 seconds.
Level 1 took 0.028447 seconds.
Level 2 took 0.028679 seconds.
Tokens were zero.
Nothing is scored.

### 2026-10-30

The campaign scored the session file at all three logging levels.
Levels 1 and 2 match the stated questions.
Level 0 misses the links that need a trace.
The byte-for-byte line is still open.
The library is still unchanged.
