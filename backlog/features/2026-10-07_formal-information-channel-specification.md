---
id: "2026-10-07_formal-information-channel-specification"
title: "Specify recording policies as information channels"
status: "Completed"
priority: "High"
created: "2026-10-07"
last_updated: "2026-10-21"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- information-theory
- observability
- specification
---

# Task: Specify Recording Policies as Information Channels

## Description

Write the formal specification that every later CIP-0015 implementation and experiment must follow.
The specification defines the execution history, neutral event stream, recording policies, retained representations, query variables, access conditions, cost boundaries, and permitted claims.
It also defines the difference between an execution dependency, a causal claim, and a counterfactual effect.

This task is the implementation of Gate 1.
No environment, recorder, decoder, or estimator should be treated as scored work until this task is complete.

## Motivation

The Werewolf pilot showed that an intuitive metric can describe game behaviour without measuring the information retained by the artifacts.
It also showed that complete service logs can collectively reconstruct information that no individual service log contains.
A formal contract is therefore required before implementation so that the experiment cannot redefine its questions, baselines, or evidence after observing results.

## Justification

Information-theoretic quantities are properties of declared random variables and probability distributions.
Analysis-cost quantities are properties of declared access and computation models.
Without these declarations, the same bytes can be scored differently for different representations.
The formal specification prevents an advantage from being created by DOAgent-specific terminology or instrumentation.

## Learning Objective

Use the formal specification to build a working understanding of the basic objects in probability and information theory.
The learner should be able to distinguish an outcome, sample space, event, random variable, observed value, probability distribution, and retained representation.
The learner should also be able to explain why uncertainty belongs to an observer's distribution over possible answers rather than to the length of one stored answer.

The first example uses three agents and one message-delivery event.
The possible recipient sets form the sample space.
A random variable maps each possible run to the recipient set or to one selected property of that set.
Different recorders retain different evidence about the same realized delivery.

## Reading Guide

Read only the material required for the current checkpoint.

1. Bishop, *Pattern Recognition and Machine Learning*, Section 1.2 for discrete random variables, joint probability, marginal probability, conditional probability, and Bayes' rule.
2. MacKay, *Information Theory, Inference, and Learning Algorithms*, Section 2.4 when the task reaches self-information and entropy.
3. MacKay, Section 2.6 when the task reaches relative entropy and mutual information.
4. Cover and Thomas, *Elements of Information Theory*, Chapter 2, Sections 2.1 through 2.5 after the intuitive calculations are understood.

Cover and Thomas is the rigorous reference rather than the first explanation.
Later chapters and transfer-entropy papers are outside this task.

## Scope

The specification must define:

- the complete execution history `H`
- the neutral event stream emitted by the environment
- recording policy `pi`
- retained artifact `R_pi`
- query variable `Q`
- answer space for each query
- candidate answer set when evidence is incomplete
- representation access conditions
- recording and analysis cost boundaries
- primary and optional metrics
- primary and extension claims
- core kill tests and stopping rules

The primary claim concerns analysis of one fixed execution.
It does not claim that DOAgent changes agent behaviour or information flow.

## Execution Plan

1. Explain outcomes, sample spaces, events, random variables, observed values, and distributions with the three-agent delivery example.
2. Calculate the example by hand and record unresolved questions in chat.
3. Read the matching Bishop material and reconcile its terminology with the example.
4. Define the mathematical objects and notation used throughout CIP-0015.
5. Explain bits, self-information, Shannon entropy, and Hartley ambiguity only when the specification first uses them.
6. Verify each new quantity with a hand calculation and a small executable test.
7. Define a neutral event envelope that does not copy the DOAgent record envelope.
8. Define the minimum event types for state, observation, message, belief, action, transition, and outcome.
9. Define which fields are private truth and which fields are offered to recorders.
10. Define the recording conditions S1, Sk, Sall, Sstructured, D0, D1, and D2.
11. Define the fixed primary query suite and finite answer spaces.
12. Define the representation parser contract and neutral evidence model.
13. Define the common decoder contract and its unknown and candidate-set outputs.
14. Define exact answerability, Hartley ambiguity, Shannon quantities, analysis cost, and recording cost.
15. Define when a trace is an enabler link and when a causal claim is permitted.
16. Define the primary hypotheses without assuming a DOAgent advantage.
17. Review the specification in plain language before formal approval.
18. Define Gate 1 completion evidence and record the decision in CIP-0015.

## Acceptance Criteria

- [x] Every primary random variable and answer space is defined.
- [x] The neutral event contract is independent of every recording representation.
- [x] Private truth is separated from all analysed artifacts.
- [x] Recording conditions and access permissions are explicit.
- [x] The primary query suite is fixed and contains no undefined causal language.
- [x] Representation parsers and the common decoder have distinct contracts.
- [x] Shannon, Hartley, computational, and economic measures are distinguished.
- [x] Recording and analysis cost boundaries are fixed.
- [x] Primary hypotheses permit ties and service advantages.
- [x] Core work and gated extensions have separate completion criteria.
- [x] The three-agent delivery example is calculated manually and reproduced by an executable test.
- [x] The learner can explain every probability and information-theory term used by the primary specification.
- [x] Reading progress and the next study handoff are recorded in the studying workspace.
- [x] Gate 1 is marked passed in CIP-0015 only after review.

## Implementation Notes

The specification belongs in CIP-0015 or a supplementary file under `cip/cip0015/`.
Core design decisions must remain in the CIP.
Machine-readable schemas may later live beside the controlled experiment, but the prose contract is authoritative during design.

Use `recorded enabler` for an update linked to a transition.
Reserve `cause` for a declared mechanism, justified identification assumptions, or controlled intervention.

## Related

- CIP: 0015
- Requirement: REQ-0015

## Progress Updates

### 2026-10-07

Task created after the CIP review fixed the experiment's claim to information retained and analysis facilitated for one shared execution.
The task now uses a learning-first workflow with hand calculations, exact reading references, executable checks, and study-note updates.

### 2026-10-08

Implementation began with the three-agent delivery example.
Manual work distinguished outcomes, sample spaces, random variables, retained artifacts, remaining uncertainty, and information gained.
`experiments/information_flow/metrics.py` now provides exact self-information, Shannon entropy, and Hartley ambiguity.
Eleven unit tests reproduce the manual values and reject invalid inputs.
The next conceptual step is conditional entropy after the discrete entropy reading.

### 2026-10-14

The count-policy conditional entropy was calculated manually as `(6 / 8) * log2(3)`.
The resulting value is about 1.189 bits.
Its mutual information is about 1.811 bits.

`conditional_entropy` and `mutual_information` now operate on exact joint probability tables.
Tests cover full, local-A, count, independent, and perfectly correlated policies.
`build_joint_distribution` maps named query answers and recording-policy outputs to the low-level probability matrix.
The resulting object preserves row and column labels so the matrix can be inspected directly or presented as a DataFrame later.
`MessageDeliveryEvent` provides the first typed neutral event without importing a DOAgent or service-log schema.
The recipient query derives private scoring truth before recording policies transform the same event into retained artifacts.
`StateTruth` now holds private latent state and optional random-draw provenance.
`ObservationEvent` exposes an agent observation and source truth identifier without exposing the latent value.
All typed events distinguish logical time from total sequence order.
Belief, action, and outcome events complete the first one-round execution path.
The targeted suite passes 38 tests.

The formal contract now separates the private truth store, permitted recorder-input events, retained artifacts, neutral evidence, and decoder access.
It defines state truth, observation, message delivery, belief, action, transition, and outcome event semantics.
It also distinguishes logical time from total event sequence order.
Execution-plan steps 7 through 9 are complete at the specification level.
Typed implementation and review remain required before Gate 1 can pass.

An unscored walking skeleton now exercises the contract in one complete episode.
It is a design aid while the analytic model and remaining Gate 1 definitions are completed.
It is not a scored environment result.

The metrics remain in `experiments/information_flow`.
This placement follows CIP-0013 because the code evaluates DOAgent itself rather than exposing an end-user analysis API or runnable example.

### 2026-10-21

Gate 1 passed after the plain-language review.
`TransitionEvent` stores the action, the other input identifiers, and the hidden-state identifiers for one step.
It does not store the hidden values, and the signalling episode does not emit one.
The guessing-game task was aligned with the sum-and-feedback game in the plan.
The information-flow tests passed, 42 in total.
