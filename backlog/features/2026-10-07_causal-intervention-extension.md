---
id: "2026-10-07_causal-intervention-extension"
title: "Add environment-declared causal interventions"
status: "Proposed"
priority: "Medium"
created: "2026-10-07"
last_updated: "2026-10-07"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies:
- "2026-10-07_controlled-observability-campaign"
tags:
- backlog
- extension
- causality
- interventions
---

# Task: Add Environment-Declared Causal Interventions

## Gating Note

This extension is subject to successful completion of the core CIP-0015 backlog through Gate 4.
The task remains Proposed until the controlled campaign demonstrates that the retained records and neutral contracts are stable enough to support intervention replay.
Its existence does not authorize implementation.

## Description

Extend the controlled environment with an explicit causal model and intervention runner.
Store environment-specific causal variables in neutral events and record payloads while keeping the generic record envelope independent of environment semantics.
Compare factual and intervened transitions under controlled state, actions, and randomness.

## Motivation

DOAgent traces identify recorded updates that enabled transitions.
They do not establish that changing one update would change an outcome.
Controlled interventions are required to answer stronger but-for and joint-causation questions.

## Justification

The controlled environment can expose its transition mechanism and reproducible exogenous randomness.
This makes counterfactual replay possible without claiming that causal structure was discovered from one observed trajectory.
The resulting artifacts can test whether recording policies preserve the variables required for reproducible causal analysis.

## Scope

The extension covers immediate transition effects.
Long-run effects that require agents to make new downstream decisions are separate and require an additional design.

The causal specification may include:

- variable names and domains
- parent relationships
- transition equations or simulator contract
- exogenous-noise distribution
- model identifier and version
- intervention targets and legal values
- outcome variables
- assumptions required for interpretation

## Execution Plan

1. Define the controlled environment as a structural transition model.
2. Separate endogenous variables from exogenous noise.
3. Store the causal model identifier and version in run metadata.
4. Extend neutral events with values required for replay.
5. Add environment snapshot and restore support.
6. Add explicit control of exogenous noise or common random seeds.
7. Define factual and intervention record formats.
8. Replay one transition with one agent action replaced.
9. Hold the previous state, other actions, and exogenous randomness fixed.
10. Compare factual and counterfactual outcomes.
11. Repeat stochastic interventions with matched noise samples.
12. Define treatment effects for scalar and categorical outcomes.
13. Add combination interventions for interacting actions.
14. Evaluate whether Shapley-style attribution is justified and computationally feasible.
15. Capture intervention artifacts under every recording policy.
16. Test whether the common query pipeline can recover intervention definitions and results.
17. State which conclusions follow from the declared mechanism and which depend on assumptions.

## Acceptance Criteria

- [ ] The environment declares a versioned causal transition model.
- [ ] Endogenous and exogenous variables are distinguished.
- [ ] Factual transitions are reproducible from recorded inputs and noise.
- [ ] Single-variable interventions can be executed from a snapshot.
- [ ] Other actions and exogenous randomness remain fixed during paired replay.
- [ ] Stochastic effects use repeated matched interventions.
- [ ] Trace enablers are not mislabeled as causal effects.
- [ ] Immediate and downstream effects are distinguished.
- [ ] Intervention artifacts link to their factual parent run.
- [ ] Every recording condition receives the same intervention source events.
- [ ] Assumptions and unsupported causal questions are documented.
- [ ] The extension result is omitted if replay validity cannot be established.

## Implementation Notes

Prefer an experiment-layer causal protocol before proposing a public DOAgent API.
Potential capabilities include `causal_schema`, `snapshot`, `restore`, and controlled `step`.
Any public protocol requires a later API review.

The environment payload may contain causal values.
The core record envelope should not gain domain-specific causal fields.

## Related

- CIP: 0015
- Requirement: REQ-0015

## Progress Updates

### 2026-10-07

Task proposed as a gated extension after distinguishing execution dependencies from counterfactual causal effects.
