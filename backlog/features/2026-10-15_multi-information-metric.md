---
id: "2026-10-15_multi-information-metric"
title: "Add multi-information, relative entropy, and declared-input conditional entropy"
status: "Ready"
priority: "Medium"
created: "2026-10-15"
last_updated: "2026-10-15"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies:
- "2026-10-15_hidden-profile-environment"
tags:
- backlog
- metrics
- information-flow
---

# Task: Add Multi-Information, Relative Entropy, and Declared-Input Conditional Entropy

## Description

Add three exact measures to `experiments/information_flow/metrics.py`.
Multi-information, also called total correlation, measures how much the agents' beliefs share beyond what each holds alone.
Relative entropy measures the distance from one distribution to another, in bits.
Conditional entropy of an action given its declared inputs measures whether a decision record accounts for the action it contains.

## Motivation

The existing measures are pairwise.
The question the study asks is about a group: how much does the collective know, and how much of that is redundant across agents.
Multi-information answers that with the measures already implemented.

It is also the quantity that most directly separates the two implementations.
Each agent's own uncertainty is recoverable from that agent's own log, so the per-agent terms are available under any recording policy.
The joint term needs records from different agents aligned on the same step, which is where a shared session record and independent service logs stop being equivalent.

## Design

Multi-information is the gap between the sum of marginal entropies and the joint entropy.

```text
I(X1, ..., Xn) = sum over i of H(Xi) - H(X1, ..., Xn)
```

For two variables this reduces to mutual information, which gives a free consistency check against the existing implementation.

Both terms come from functions that already exist.
`shannon_entropy` applied to each marginal gives the first term.
`shannon_entropy` applied to the flattened joint gives the second.
No new estimator is needed, only a joint distribution over more than two variables.

The current `JointDistribution` in `channels.py` is two-dimensional, rows and columns.
Extend it to an n-way distribution, or add a sibling type, keeping the nested tuple of floats as the low-level structure and the labels as a view on top.
That is the same split already in place.

### Relative entropy

Relative entropy, also called Kullback-Leibler divergence, is the expected extra bits needed to encode outcomes from one distribution using a code built for another.

```text
D(P || Q) = sum over x of P(x) log2(P(x) / Q(x))
```

It is zero when the two distributions match, and positive otherwise.
The argument order is part of the definition, because the measure is not symmetric.
`P` is the distribution treated as true.
`Q` is the distribution being scored against it.

Two uses are already named.
Belief quality needs the distance from an agent's reported belief to the posterior implied by the facts it held.
The guessing game needs the distance from an agent's belief to the true posterior over the remaining candidates.

Mutual information is the relative entropy between the joint and the product of its two marginals.
Computing that case with `relative_entropy` and comparing it with `mutual_information` checks both functions against each other.

A cell where `P(x)` is positive and `Q(x)` is zero contributes positive infinity.
Return that value and document it.
A cell where both are zero contributes nothing.
Reject an argument that is not a probability distribution, using the same checks as the other measures.

### Conditional entropy of an action given its declared inputs

This measure is `conditional_entropy` applied to the joint of an action and the inputs its decision record declares.

```text
H(action | declared inputs)
```

A DOAgent agent update stores those inputs in the same record as the action, because `decide` writes them there.
The joint can be read off those records directly.
A service log stores the message text, so the decoder has to recover the input set before the same joint can be built.

Zero means the declared inputs fully account for the action.
A positive value means the action varied while the declared inputs stayed fixed, so the decision used something the record does not name.

Scripted policies make the action a function of the held facts, so the true value is exactly zero.
In the scripted core the measure therefore scores the decoder.
A positive value from a reconstructed input set is reconstruction error, in bits.
With LLM agents the same measure detects an undeclared channel, because a positive value against the true inputs means the action depended on something the record omitted.

Build the joint with the labelled distribution in `channels.py` and call `conditional_entropy`.
Do not add a new summation for this measure.

## Execution Plan

1. Extend `channels.py` with an n-way labelled distribution built from weighted histories and a tuple of variable extractors.
2. Add `multi_information` to `metrics.py`, computed as the sum of marginal entropies minus the joint entropy.
3. Validate the input the same way `_validated_joint_distribution` does: non-negative, finite, sums to one, rectangular.
4. Add tests covering independence, full redundancy, the two-variable reduction to mutual information, and non-negativity.
5. Apply multi-information to the Hidden Profile beliefs and record the reference values.
6. Add `relative_entropy` to `metrics.py`.
7. Test a matching pair, an asymmetric pair, a zero cell in `Q`, and the reduction of mutual information to relative entropy.
8. Add a helper that builds the action and declared-input joint from a sequence of decisions and returns its conditional entropy.
9. Test that a deterministic policy yields zero, and that omitting an input the action depends on yields a positive value.
10. Record the Hidden Profile reference for belief-to-posterior relative entropy.

## Acceptance Criteria

- [ ] `multi_information` returns zero for independent variables, within floating point tolerance.
- [ ] It equals `mutual_information` for the two-variable case, within tolerance.
- [ ] It is maximal for fully redundant variables.
- [ ] It is never negative for a valid distribution.
- [ ] It rejects malformed distributions with the same checks as the existing measures.
- [ ] The n-way distribution keeps the nested float structure as the low-level representation.
- [ ] Reference values are computed for the Hidden Profile belief set.
- [ ] `relative_entropy` returns zero for two identical distributions, within tolerance.
- [ ] It reproduces `mutual_information` when applied to the joint against the product of the marginals.
- [ ] It returns positive infinity when `Q` is zero where `P` is positive.
- [ ] It rejects an argument that does not sum to one.
- [ ] The declared-input conditional entropy is zero for a deterministic scripted policy.
- [ ] It is positive when an input the action depends on is omitted from the record.
- [ ] It is computed by calling `conditional_entropy` on a labelled joint.

## Implementation Notes

Build multi-information from `shannon_entropy` and the declared-input measure from `conditional_entropy`.
The point of the metrics module is that every measure is assembled from the ones already derived.

Leave an infinite relative entropy as infinity.
Clipping it would hide a reference distribution that rules out an outcome the compared distribution still allows.

Keep the estimator out of this task.
These are exact measures on a known distribution.
Estimating them from samples is the estimator-validation task.

## Dependencies and Gate

Needs the Hidden Profile belief definition to have something to apply it to.
Belongs to the metric suite in Gate 2.

## Related

- CIP: 0015
- Requirement: REQ-0015

## Progress Updates

### 2026-10-15

Task created. Multi-information is the group-level measure the pairwise set was missing.

The same task now also covers relative entropy and the conditional entropy of an action given its declared inputs.
Relative entropy supplies belief calibration in bits, and it cross-checks mutual information.
The declared-input measure reads a DOAgent decision record directly.
Under scripted policies its true value is zero, so a positive decoded value is reconstruction error.
Partial information decomposition was considered for the same group question and left out.
Several incompatible definitions of redundancy exist, and multi-information already gives the group-level quantity the study needs.
