---
id: "2026-10-07_information-estimator-validation"
title: "Validate information-theoretic estimators"
status: "Completed"
priority: "High"
created: "2026-10-07"
last_updated: "2026-10-29"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies:
- "2026-10-07_analytic-reference-model"
- "2026-10-07_controlled-information-flow-environment"
- "2026-10-07_common-query-decoding-pipeline"
tags:
- backlog
- entropy
- mutual-information
- statistics
---

# Task: Validate Information-Theoretic Estimators

## Description

Implement and validate the estimators used by the controlled campaign.
Compare empirical estimates against analytic reference values under the exact sample sizes and variable alphabets planned for scoring.
Select estimators, corrections, intervals, and omission rules before inspecting scored results.

## Motivation

Entropy and mutual-information plug-in estimates are biased at finite sample sizes.
Conditional quantities become unstable when joint alphabets grow.
An apparently meaningful difference between recording policies may therefore be estimator noise.

## Justification

The experiment can make an information-theoretic claim only when its measuring procedure is validated.
The analytic reference model makes this possible.
Metrics that cannot recover known values under feasible sample counts must be removed or simplified before the expensive campaign.

## Primary Quantities

The core validation covers:

- entropy of latent states
- entropy of reported belief distributions
- conditional entropy of query answers after decoded evidence
- mutual information between latent states and observations
- mutual information between latent states and actions
- mutual information between truth answers and decoded answers
- conditional mutual information for declared communication relationships
- Hartley ambiguity for finite candidate sets
- Brier score and log loss for belief calibration
- relative entropy from a reported belief to the posterior implied by the held facts

Transfer entropy is validated only in its gated extension task.

## Execution Plan

1. Implement exact counting and probability normalization utilities.
2. Implement plug-in entropy and mutual-information estimates.
3. Select finite-sample corrections suitable for the declared alphabets.
4. Implement a Bayesian or shrinkage alternative where justified.
5. Implement Hartley ambiguity independently of empirical probabilities.
6. Implement Brier score and log loss with explicit zero-probability handling.
7. Implement relative-entropy estimates, keeping a positive infinity when the reference is zero where the estimate is positive.
8. Generate repeated samples from the analytic reference model.
9. Evaluate bias, variance, interval coverage, and failure modes across sample sizes.
10. Test sparse and deliberately misspecified conditions.
11. Test decoded answers with unknown and candidate-set outputs.
12. Define the primary estimator for every scored quantity.
13. Define bootstrap units as independent episodes rather than dependent time points.
14. Select sample count from tolerance and coverage results.
15. Define omission thresholds for unstable metrics.
16. Freeze estimator configuration before the scored campaign.

## Acceptance Criteria

- [x] Every primary estimator has a named target quantity.
- [x] Units and logarithm bases are explicit.
- [x] Empirical estimates recover analytic references within declared tolerances.
- [x] Bias and variance are reported across candidate sample counts.
- [x] Confidence or credible interval coverage is evaluated.
- [x] Dependent observations are not treated as independent bootstrap units.
- [x] Sparse-cell behaviour is tested.
- [x] Unknown decoded answers have a predeclared treatment.
- [x] Candidate-set ambiguity is not mislabeled as Shannon entropy.
- [x] Belief confidence is accompanied by calibration scoring.
- [x] Relative entropy recovers its analytic references, including the infinite case.
- [x] Sample size is selected from simulation evidence.
- [x] Gate 2 pass or failure is recorded in CIP-0015.

## Implementation Notes

Prefer small alphabets and interpretable estimators over high-dimensional estimators with unverifiable assumptions.
Do not estimate mutual information directly from raw natural-language text.
Use decoded discrete variables or declared probability vectors.

Report negative estimates produced by corrections rather than silently clipping unless the estimator definition requires clipping.
Record software versions, seeds, and numerical tolerances.

## Dependencies and Gate

This task requires the analytic model, generated samples, and query output contract.
Gate 2 passes only when the selected estimators recover known values under the planned sample regime.
Failure delays the campaign and does not justify increasing model complexity.

## Related

- CIP: 0015
- Requirement: REQ-0015

## Progress Updates

### 2026-10-07

Task created to prevent finite-sample artefacts from becoming architectural claims.

### 2026-10-15

Relative entropy was added to the quantities validated against analytic references.
The infinite case, where the reference distribution rules out an outcome the estimate still allows, is part of that check.

### 2026-10-23

`sample.py` draws deals with replacement from the exact list of 18.
The plug-in estimates are who holds the bridge fact, and agent A's belief entropy after round 0.
The exact values are 1.585 bits and 0.9635 bits.
A sample of 2 deals estimated the holder entropy as 0, so the error was 1.585 bits.
A sample of 18 draws with replacement was still 0.170 bits away on the holder entropy.
A sample of 4000 was within 0.001 bits of both exact values.
The seed for those draws was 0.
Gate 2 stays open.
Intervals, corrections, and the other exact quantities are not checked yet.

### 2026-10-29

A count passes when it is less than 0.05 bits from the exact answer.
Each sample size was drawn 1,000 times, and a size is kept when at least 950 draws pass.
For who received the bridge fact, 2 deals passed 0 times and 18 deals passed 419 times.
Neither size is kept.
4,000 deals passed all 1,000 times and is kept.
For how uncertain agent A is after the first round, 2 deals passed 900 times and is not kept.
18 deals and 4,000 deals each passed all 1,000 times and are kept.
A later run that cannot play every game needs 4,000 plays to keep both counts.
The same rule now covers every exact count for this game.
The correct route does not vary, so that count is kept at 2 deals, 18 deals, and 4,000 deals.
How uncertain the route remains given one player's facts is kept at all three sizes.
How much that player's messages say about the route is kept at all three sizes.
How uncertain each player's reported chances are is kept at 18 deals and at 4,000 deals.
It is not kept at 2 deals.
Who holds the bridge fact is kept only at 4,000 deals.
Who receives it is kept only at 4,000 deals.
How much the three holdings overlap is kept only at 4,000 deals.
18 deals is not enough for those three counts.
The squared error of a reported chance list uses the same 0.05 line.
It is not a bit count.
That score stayed within the line at 2 deals, 18 deals, and 4,000 deals.
The information lost when a chance is scored is in bits.
A reported chance of zero is infinite.
In this game the reported chance matches the chance implied by the facts, so their distance is zero.
A chance list that allows a ruled-out route has an infinite distance.
That case is checked by hand.
The plain count is kept when it is within 0.05 of the known answer.
Its interval must cover at least 90 percent of the repeats.
The interval uses the spread of earlier repeats of whole deals.
Four counts use a corrected value, because the plain count sits a little low.
They are who holds the bridge fact, who receives it, and how much the holdings overlap.
The fourth is how much agent A's hand and agent B's hand share, given the holder.
At 4,000 deals the plain holder count is about 0.0004 bits low and covers 87 percent of repeats.
The corrected holder count is about 0.000006 bits low and covers 95 percent.
The correction adds a small term for each category that appeared.
It is not clipped.
Repeating one deal still leaves the holder count at zero.
18 deals is still not enough for that count.
The correct route does not vary, so its correction is zero and the plain count is kept.
A missing answer is not given a bit count.
A list of possible answers uses the size of the list.
No count was dropped.
A later game that cannot list every deal should use 4,000 deals.
This game still scores all 18 deals.
Checkpoint 2 passes.
Nothing is scored.
