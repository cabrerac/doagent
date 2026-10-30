---
id: "2026-10-07_transfer-entropy-extension"
title: "Validate temporal information-flow estimation"
status: "Proposed"
priority: "Medium"
created: "2026-10-07"
last_updated: "2026-10-07"
category: "features"
related_cips:
- "0015"
owner: "Christian Cabrera"
dependencies:
- "2026-10-07_information-estimator-validation"
- "2026-10-07_controlled-observability-campaign"
tags:
- backlog
- extension
- transfer-entropy
- temporal-information
---

# Task: Validate Temporal Information-Flow Estimation

## Gating Note

This extension is subject to successful completion of the primary estimator validation and controlled campaign.
It remains Proposed unless the fixed process supplies enough repeated transitions and a manageable joint alphabet.
Failure to validate transfer entropy does not block core CIP completion.

## Description

Determine whether transfer entropy or a related conditional-information measure can estimate directed temporal information flow in the controlled environment.
Validate the estimator against a process with known directional coupling before applying it to any agent trajectory.

## Motivation

Mutual information detects statistical dependence but does not encode temporal direction.
Transfer entropy asks whether a source history improves prediction of a target's next state beyond the target's own history.
This is potentially relevant to communication between agents, but it is especially vulnerable to sparse samples, common causes, and non-stationarity.

## Justification

Transfer entropy should be included only if it adds a stable result beyond simpler conditional mutual information.
A dedicated validation task prevents an attractive but unreliable metric from entering the main evaluation.

## Candidate Quantity

The initial candidate is:

```text
TE(M to B) = CMI(B_next, M_now | B_now)
```

The variables are discrete messages and discretized or categorical belief states.
History lengths longer than one step require separate validation.

## Execution Plan

1. Define a reference stochastic process with known directed coupling.
2. Define a matched null process with no source-to-target influence.
3. Calculate or approximate the reference transfer entropy.
4. Implement the estimator with explicit history lengths and alphabets.
5. Test bias and false positives across sample sizes.
6. Test sensitivity to common causes and omitted conditioning variables.
7. Test stationary and deliberately non-stationary processes.
8. Compare transfer entropy with simpler conditional mutual information.
9. Define belief discretization before seeing agent results.
10. Determine the minimum transition count required for stable estimates.
11. Apply the estimator to controlled-policy trajectories only after reference validation.
12. Use episode-aware resampling rather than treating transitions as independent.
13. Decide whether the result is primary, descriptive, or omitted.
14. Record the decision and evidence in CIP-0015.

## Acceptance Criteria

- [ ] A reference process has a known direction and nonzero target value.
- [ ] A null process has no directed coupling.
- [ ] The estimator separates reference and null processes at the planned sample size.
- [ ] Bias and variance are reported.
- [ ] Common-cause sensitivity is evaluated.
- [ ] Non-stationarity limitations are evaluated.
- [ ] History length and discretization are fixed before application.
- [ ] Independent episodes define uncertainty units.
- [ ] The metric adds information beyond simpler conditional measures.
- [ ] Unstable or misleading estimates are omitted.
- [ ] Omission does not affect core CIP status.

## Implementation Notes

Do not estimate transfer entropy directly from raw text.
Do not infer direction solely from message timestamps.
Conditioning variables must be justified by the declared process.

An apparent source-to-target value can result from a shared observation or synchronized state transition.
The analysis must test this confounding explicitly.

## Related

- CIP: 0015
- Requirement: REQ-0015

## Progress Updates

### 2026-10-07

Task proposed as an optional temporal-information extension with an explicit omission path.
