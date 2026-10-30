---
id: "2026-10-07_controlled-information-flow-environment"
title: "Implement the controlled information-flow environment"
status: "In Progress"
priority: "High"
created: "2026-10-07"
last_updated: "2026-10-21"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies:
- "2026-10-07_formal-information-channel-specification"
- "2026-10-07_analytic-reference-model"
tags:
- backlog
- environment
- information-flow
- simulation
---

# Task: Implement the Controlled Information-Flow Environment

## Description

Implement the analytic reference model as a fixed-length multi-agent environment.
The environment emits neutral events and private truth without importing DOAgent or any service recorder.
It supports deterministic seeded reproduction and enough repeated episodes for estimator validation.

## Motivation

The primary experiment needs a source of trajectories whose probability model is known.
The source must remain independent of the representation policy so that no artifact format receives privileged variables or semantics.
Implementing the analytic model as a neutral environment provides that source.

## Justification

The environment is deliberately minimal.
It contains the private observations, communication, beliefs, actions, and temporal dependence required by the primary metrics.
Additional topology, conflict, language, and realism are gated extensions rather than initial complexity.

## Scope

The environment includes:

- latent-state initialization and transition
- agent-specific noisy observations
- fixed communication topology
- finite structured messages
- Bayesian or scripted policies
- structured belief reports
- finite actions
- fixed measurement points
- fixed episode horizon
- private truth output
- neutral event output
- reproducible exogenous randomness

The environment excludes:

- LLM calls
- natural-language semantic decoding
- representation-specific record objects
- causal attribution beyond declared transition dependencies
- dynamic topology in the first level
- variable-length death or elimination mechanics

## Execution Plan

1. Define environment configuration models from the analytic specification.
2. Implement seeded reset and latent-state initialization.
3. Implement observation sampling from declared channels.
4. Implement Bayesian or scripted policy interfaces.
5. Implement communication over the fixed topology.
6. Implement belief reports at every declared measurement point.
7. Implement action selection and state transition.
8. Emit neutral events for observations, messages, beliefs, actions, transitions, and outcomes.
9. Write private truth through a separate sink unavailable to recorders.
10. Record the exogenous random seed or noise key required for exact replay.
11. Implement deterministic replay for identical configuration and seed.
12. Add invariant checks for probability normalization and event ordering.
13. Add unit tests against analytic one-step cases.
14. Add an integration test for one complete episode.
15. Run a small unscored batch and compare empirical frequencies with the reference model.

## Acceptance Criteria

- [x] The environment imports no DOAgent or service recorder implementation.
- [ ] Configuration fully determines state, observation, communication, and action distributions.
- [x] Identical seeds reproduce identical neutral events and private truth.
- [ ] Neutral events contain every field required by the primary query suite.
- [x] No neutral event contains a DOAgent-specific record identifier or kind.
- [x] Private truth is inaccessible through recorder inputs.
- [x] Bayesian belief reports match the analytic update in fixed tests.
- [x] Event ordering and episode length are deterministic for a fixed seed.
- [ ] Empirical frequencies converge toward reference probabilities.
- [x] Unit and integration tests pass.
- [x] A complete episode can run without any recorder attached.
- [ ] The calibration configuration is frozen before any implementation comparison is scored.
- [x] Rules and scripted policies are separate, and the rules expose `reset` and `step`.

## Implementation Notes

Keep the environment under `experiments/`.
Use small typed models or data classes for neutral events.
Assign neutral event identifiers before any recorder sees an event.
Do not reuse DOAgent record identifiers as neutral identifiers.

The environment may expose an optional snapshot and replay interface for the later causal-intervention extension.
That interface is not required for core completion unless it is needed for deterministic validation.

## Dependencies and Gate

The formal specification and analytic reference model must be complete.
The environment remains unscored until estimator validation confirms that its generated samples recover reference quantities.

## Related

- CIP: 0015
- Requirement: REQ-0015

## Progress Updates

### 2026-10-07

Task created to implement the recorder-independent source of controlled multi-agent trajectories.

### 2026-10-14

An unscored one-round walking skeleton now runs without any recorder.
It samples one of four hidden states for three agents with heterogeneous symmetric observation channels.
One agent sends its observation to an independently sampled recipient set.
Agents report Bayesian beliefs, select maximum-posterior actions, and receive correct or incorrect outcomes.

Private state truth is separate from the ordered recorder-visible event stream.
Identical configuration and seed reproduce the full episode.
Six environment tests cover replay, ordering, privacy, Bayesian updates, message inputs, actions, and outcomes.
The complete information-flow suite passes 38 tests.

State transitions, fixed multi-step horizons, empirical frequency checks, and shadow recorders remain open.
The environment remains unscored until the formal and estimator gates pass.

### 2026-10-15

Re-scoped to the Lewis signalling calibration case.
Shadow recorders are no longer part of the study.
The game is not expected to separate the two implementations, because every relationship is one hop.
Its role is to calibrate the metrics against exact enumerated references.

Remaining work in this task:

1. Split the environment into rules with `reset` and `step` and separate scripted policies.
2. Keep the neutral event stream and private truth as the scoring sink.
3. Check that the rules can be wrapped by a DOAgent session and by a MARBLE environment.
4. Compare empirical frequencies with the analytic reference.

Multi-step transitions are optional for calibration and move to Hidden Profile where rounds matter.

### 2026-10-21

The signalling round is now split into rules and a scripted policy.
`SignallingRules.reset` draws the hidden colour and the glimpses.
The first `step` delivers the sender message.
The second `step` records the reported beliefs and scores the chosen colours.
`run_episode` loops over those calls.
The same seed still replays the same episode.
`step` returns observations, rewards, and a finished flag.
The hidden colour stays on the rules and is absent from the observation mappings.
