---
id: "2026-10-07_analytic-reference-model"
title: "Define the analytic information-flow reference model"
status: "In Progress"
priority: "High"
created: "2026-10-07"
last_updated: "2026-10-22"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies:
- "2026-10-07_formal-information-channel-specification"
tags:
- backlog
- information-theory
- probability
- simulation
---

# Task: Define the Analytic Information-Flow Reference Model

## Description

Define a small stochastic multi-agent process whose key information quantities can be calculated analytically.
The model provides the ground truth used to validate entropy, mutual-information, belief, and uncertainty estimators before any LLM experiment.
It also determines the minimum episode count required for stable estimates.

## Motivation

Estimating Shannon quantities from natural-language Werewolf trajectories would combine estimator error, semantic decoding error, variable-length histories, and model behaviour.
Those effects cannot be separated without a known reference.
A tractable stochastic model allows implementation errors and finite-sample bias to be detected before expensive runs.

## Justification

The model must be rich enough to contain private observations, communication, belief updates, actions, and temporal dependence.
It must remain small enough for exact joint distributions or high-precision enumeration.
This balance supports credible information-theoretic validation without pretending that a toy model provides external validity by itself.

## Model Requirements

The first model uses:

- a four-valued latent state
- a declared initial distribution
- a declared Markov transition matrix
- at least three agents
- heterogeneous noisy observation channels
- a fixed communication graph
- a finite message alphabet
- Bayesian belief updates
- a finite action alphabet
- a fixed episode horizon

The model must permit analytic or enumerated calculation of selected marginal and joint distributions.

## Execution Plan

1. Select the latent-state alphabet and fixed horizon.
2. Define the initial distribution and transition matrix.
3. Define one observation channel per agent.
4. Define the fixed communication topology and message policy.
5. Define Bayesian agent updates and action policies.
6. Specify all exogenous random variables and independence assumptions.
7. Derive or enumerate the joint distribution over states, observations, messages, beliefs, and actions.
8. Calculate reference state entropy and selected conditional entropies.
9. Calculate reference mutual information and conditional mutual information.
10. Define exact belief entropy, Brier score, and log-loss references.
11. Identify which temporal variables could support transfer entropy later.
12. Simulate repeated samples and measure plug-in estimator bias.
13. Compare candidate finite-sample corrections or Bayesian estimators.
14. Determine episode counts required for declared tolerance and interval width.
15. Record analytic values, simulation seeds, and sample-size recommendations.

## Acceptance Criteria

- [ ] The model defines every random variable and probability distribution.
- [ ] The dependency structure and conditional independences are explicit.
- [ ] Bayesian belief updates are reproducible from the specification.
- [ ] At least one entropy has an exact analytic value.
- [ ] At least one mutual-information quantity has an exact analytic value.
- [ ] At least one conditional-information quantity has an exact analytic value.
- [ ] Belief calibration reference values are defined.
- [ ] Simulation reproduces the analytic values within a declared tolerance.
- [ ] Finite-sample bias is measured across candidate episode counts.
- [ ] The recommended sample size is justified by simulation.
- [ ] Variables not identifiable from the proposed observations are listed.
- [ ] The model specification is reviewed before environment implementation begins.

## Implementation Notes

Prefer exact enumeration over Monte Carlo when the state space permits it.
Use base-two logarithms and state units in bits.
Handle zero probabilities explicitly.
Keep analytic calculations independent of DOAgent and service recorder code.

The reference model is not a benchmark result.
It is the measuring instrument used to validate the benchmark.

## Dependencies and Gate

This task starts after the formal information-channel specification is reviewed.
Its successful analytic and simulation results are required before the controlled environment becomes a scored implementation.

## Related

- CIP: 0015
- Requirement: REQ-0015

## Progress Updates

### 2026-10-07

Task created as the probability model and sample-size foundation for the controlled evaluation.

### 2026-10-14

An unscored walking skeleton now uses four uniform hidden states and three heterogeneous symmetric observation channels.
One agent sends its observation over independently sampled delivery channels.
Agents calculate Bayesian beliefs from their own observations and any received message.
They select the maximum-posterior state and receive a correct or incorrect outcome.

The current model is one round and has no latent-state transition matrix.
Exact enumeration, reference information quantities, finite-sample simulation, and sample-size selection remain open.
No analytic acceptance criterion or estimator gate is marked complete yet.

### 2026-10-15

The primary environment is now Hidden Profile, so the reference model follows it rather than the one-round signalling skeleton.
The enumeration target moves to `experiments/information_flow/hidden_profile/reference.py`, which must produce exact entropy, conditional entropy, mutual information, and multi-information for the frozen Hidden Profile configuration.
The signalling skeleton remains as a calibration case, since its small state space makes estimator errors easy to see.
Sample-size selection still has to be done against the Hidden Profile reference rather than against the skeleton.

### 2026-10-21

`experiments/information_flow/hidden_profile/reference.py` now enumerates the reference configuration.
Thirty-six equally likely shuffles produce 18 deals, and the scripted policy plays each deal once.
Entropy, conditional entropy, mutual information, and multi-information are computed from that list.
The correct route is constant, so its entropy is zero.
The bridge-fact holder and recipient each have entropy and mutual information `log2(3)`.
Finite-sample simulation and sample-size selection remain open.

### 2026-10-22

The belief figures of about 0.96 bits and about 1.00 bits are the entropy of the three reported route probabilities.
They are not uncertainty about the correct route.
That route is the hill in every deal, so its entropy remains zero.
Sample size is still open.
