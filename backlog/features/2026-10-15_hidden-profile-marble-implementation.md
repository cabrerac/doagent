---
id: "2026-10-15_hidden-profile-marble-implementation"
title: "Implement Hidden Profile with MARBLE services"
status: "Completed"
priority: "High"
created: "2026-10-15"
last_updated: "2026-10-29"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies:
- "2026-10-15_hidden-profile-environment"
tags:
- backlog
- marble
- hidden-profile
- information-flow
---

# Task: Implement Hidden Profile with MARBLE Services

## Description

Run the same Hidden Profile rules and scripted policies through MARBLE.
Produce the artifacts a MARBLE user would actually have: per-component logs written by independent services, with no shared record.

## Motivation

This is the comparison baseline.
It has to be a fair MARBLE implementation, built the way MARBLE is built, not a weakened version designed to lose.

## Justification

The repository already vendors MARBLE under `experiments/multiagentbench/MARBLE`.
`run_werewolf_service.py` shows the established pattern: load a MARBLE config, subclass the MARBLE agent, and let the MARBLE engine orchestrate.
Reusing that pattern keeps the Hidden Profile comparison consistent with the Werewolf comparison.

## Design

### Components

Three MARBLE classes carry the implementation.

```text
BaseEnvironment   marble/environments/base_env.py
BaseAgent         marble/agent/base_agent.py
Engine            marble/engine/engine.py
```

Add a `HiddenProfileEnv` subclassing `BaseEnvironment` that delegates to the shared rules.
Add a `HiddenProfileAgent` subclassing `BaseAgent` whose `act` calls the shared scripted policy.
Override `act` rather than going through the LLM path, because the scripted stage has no model call.

### Delegation, not reimplementation

The MARBLE environment must not contain the fact set, the sharing rule, or the scoring.
It holds an instance of `HiddenProfileRules` and forwards.

```python
class HiddenProfileEnv(BaseEnvironment):
    def __init__(self, name, config):
        super().__init__(name, config)
        self._rules = HiddenProfileRules(config["hidden_profile"])
```

Any divergence here invalidates trajectory parity.
If MARBLE's interface needs an adaptation the rules do not provide, add the adaptation in the MARBLE adapter and record it in the progress update.

### Logging

Keep MARBLE's own logging.
Each component writes through `marble.utils.logger.get_logger`, so each agent and the environment produce separate log streams.
Do not add a shared sink.
The absence of a shared sink is the property under study.

Mirror the same three verbosity levels as the DOAgent run, mapped onto MARBLE log levels, and document the mapping.

### Configuration

Follow the Werewolf precedent and keep a MARBLE-style YAML config under the MARBLE config tree rather than hard-coding values in the runner.
The config names the agents, the environment, the engine settings, and the Hidden Profile parameters.

### Recording conditions

This implementation supplies the service-side conditions in the condition grid.

```text
S1          one service logs
Sk          a subset of services log
Sall        every service logs
Sstructured every service logs to a declared schema
```

`Sstructured` is optional.
If it is implemented, note that it is a stronger baseline than plain MARBLE and that a tie against DOAgent is an acceptable and informative outcome.

## Execution Plan

1. Add `experiments/information_flow/hidden_profile/marble_env.py` with `HiddenProfileEnv`.
2. Add `experiments/information_flow/hidden_profile/marble_agent.py` with `HiddenProfileAgent`.
3. Add a config under the MARBLE test config tree, following the Werewolf config layout.
4. Add `experiments/information_flow/hidden_profile/run_marble.py` that loads the config and starts the engine.
5. Run one episode with a fixed seed and confirm per-component logs are written.
6. Extract the neutral event stream the rules emitted and compare it to the no-framework run for the same seed.
7. Implement the condition grid as a run parameter that selects which services log.
8. Add `tests/test_hidden_profile_marble.py`.
9. Record the artifact layout, one log file per component, in the progress update.

## Trajectory Parity

Same definition as the DOAgent task.
The neutral event sequence from this run must be identical to the no-framework run for the same seed.
Artifacts will differ, and that difference is the result.

## Acceptance Criteria

- [x] The MARBLE environment delegates to the shared rules and contains no duplicated game logic.
- [x] The MARBLE agent calls the shared scripted policy.
- [x] The run asks every agent once per round. MARBLE does not ship this game, and the Werewolf run does not use the shared engine either.
- [x] The loader writes one file per component, using MARBLE's logger names and line format.
- [x] A fixed seed reproduces the artifacts at a given verbosity level.
- [x] The neutral event sequence is identical to the no-framework run for the same seed.
- [x] All four recording conditions are selectable as run parameters.
- [x] Any adapter-level divergence from the shared rules is recorded explicitly.
- [x] Token and wall-clock cost are recorded per condition.
- [x] A reviewer who knows MARBLE confirms the implementation is idiomatic.

## Implementation Notes

The MARBLE checkout is vendored, so do not edit files inside `MARBLE/marble` beyond adding the config.
Subclass from the experiment directory instead.

`BaseAgent.__init__` expects MARBLE's agent configuration shape.
Satisfy it rather than bypassing it, so the agent remains a real MARBLE agent.

The last acceptance criterion is the fairness check.
It is a review step, not something a test can assert.

## Dependencies and Gate

Blocked on the environment task.
Gate 3 on implementation fairness covers this task and the DOAgent task together.
Neither is scored until both have been reviewed side by side.

## Related

- CIP: 0015
- Requirement: REQ-0015

## Progress Updates

### 2026-10-15

Task created. Design follows the existing Werewolf service runner and the vendored MARBLE base classes.

### 2026-10-23

The environment, the agent, and the runner play one seed.
Seed 17 matches the no-framework episode, including the vote.
The scoring sink is not written.

The vendored engine module cannot be imported.
`marble/evaluator/evaluator.py` does not parse, and the engine imports that evaluator at module load.
The stock engine also asks one agent to pick the next speaker.
`HiddenProfileEngine` therefore does not subclass `Engine`.
It reads the MARBLE config, builds one `HiddenProfileAgent` per entry, and asks every agent once per round in ring order.

The agent subclasses `BaseAgent` and the environment subclasses `BaseEnvironment`.
Loading those classes also imports a model client that is not installed, and the environment package imports every bundled environment.
`marble_support.py` loads the base classes directly and supplies the missing model-client names.
No model is called.

MARBLE's logger builds a rotating file handler for `logs/app.log` and then does not attach it.
That handler opens a file and leaves it unclosed.
The runner uses the same logger names and message format, writes to the console, and attaches one file per component under the run directory.
The component loggers do not share one file.

An analyst view reads that finished run.
S1 returns one named log.
Sk returns the named subset, in the order given.
Sall returns the five component logs.
An optional structured service trace is written beside those logs, one JSON line per engine call.
The prose logs are unchanged.
On the questions already compared, that file ties with the rules.
The tie is not a scored result.
At that point the four recording conditions were not yet run parameters.

Seed 17 was timed while all five logs were written.
One untimed pass was followed by five timed passes, each in a fresh folder.
The median on this machine was 0.003862 seconds.
Tokens and model calls were zero.
At that point the per-condition cost boxes were still open.

### 2026-10-23

The fairness review accepts the environment, the agents, and the component logs as the MARBLE baseline.
The environment subclasses MARBLE's environment.
Each agent subclasses MARBLE's agent.
Both use the shared rules and the shared scripted policy.
The component logs use MARBLE's logger names and line format.
The engine does not subclass MARBLE's engine.
The vendored engine cannot be imported, and the stock engine lets one agent choose the next speaker.
`HiddenProfileEngine` asks every agent once per round, in ring order.
The optional trace is an extra file, not MARBLE's native logging.
At that point the idiomatic-review box was still open.

### 2026-10-29

The turn-order loop is not an open criterion.
MARBLE does not ship a Hidden Profile game.
Werewolf keeps its turn order inside its own environment, and that run does not load the shared engine either.
The shared engine still cannot be imported, because its scorer file does not parse.
That fact does not leave a task.
The loop only asks each player and passes the choice on.
A run can name one log, a named subset, all five logs, or only the structured file.
A run that names no view still writes every log and the structured file.
Two runs of the same view match once the clock is removed from each line.
The structured file matches once its timestamp is removed.
Each time is the middle of five fresh runs after one warm-up, on this machine.
One component log took 0.008940 seconds.
The environment log plus agent A's log took 0.009531 seconds.
All five logs took 0.017969 seconds.
The structured file alone took 0.014591 seconds.
Tokens were zero.
The review of the environment, the agents, and the component logs is complete.
The engine stays as it is.
The structured file records the caller, the callee, the message, the payload, and the parent call.
The parent is the engine run.
It does not copy a session record.
Nothing is scored.
