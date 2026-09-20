---
id: "2026-09-20_phase1-wt-baselines-cost"
title: "Phase 1 independent W/T baselines and capture-cost runs"
status: "Completed"
priority: "High"
created: "2026-09-20"
last_updated: "2026-09-20"
category: "features"
related_cips:
- "0012"
owner: "Christian Cabrera"
dependencies:
- "2026-09-18_phase1-wt-judges-lookup"
tags:
- backlog
- validation
- evaluation
- attribution
---

# Task: Phase 1 independent W/T baselines and capture-cost runs

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Implement the paper capture protocol from CIP-0012. W and T are independent
collectors under `experiments/attribution/baselines/w` and
`experiments/attribution/baselines/t`. They are not part of `doagent/`.

Paired attribution: one team execution; DOAgent writes D; observe-only W
and T write their packs; judges use that run’s gold.

Unpaired capture cost: three executions (D with DOAgent; W-only and
T-only without DOAgent, using in-process hand-off); time and bytes
only; no judges. W and T are not the communication channel.

## Acceptance Criteria

- [x] W collector writes output-only steps on the shared step clock.
- [x] T collector writes per-step input and output on the same clock.
- [x] Collectors can attach as observers on a DOAgent run without changing gold.
- [x] W-only and T-only cost runs do not use DOAgent; the host loop passes each return value to the next agent.
- [x] Cost summary reports time and bytes for D, W-only, and T-only.
- [x] Judges are not invoked from the cost runner.
- [x] Tests stay offline (no API key).

## Implementation Notes

Do not score W from one seed against T from another. NoOp is not a cost
condition for this team. Projecting W/T from D may remain as a check.

## Related

- CIP: [0012](../../cip/cip0012_magentic-one-doa-evaluation.md)
- Depends: [2026-09-18_phase1-wt-judges-lookup](2026-09-18_phase1-wt-judges-lookup.md)

## Progress Updates

### 2026-09-20

Task created after the protocol was revised: independent baselines, paired
attribution, unpaired capture cost.

Host loop, W/T collectors, `--observe`, and the D vs W-only vs T-only
cost runner are in place. Offline tests cover gold parity and observe-only
hooks.
