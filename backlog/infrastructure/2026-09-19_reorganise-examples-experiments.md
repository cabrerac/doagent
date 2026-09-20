---
id: "2026-09-19_reorganise-examples-experiments"
title: "Reorganise examples and experiments"
status: "Completed"
priority: "High"
created: "2026-09-19"
last_updated: "2026-09-19"
category: "infrastructure"
related_cips:
- "0013"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- examples
- experiments
- reproducibility
---

# Task: Reorganise examples and experiments

## Description

Implement CIP-0013 in safe stages. Separate runnable examples, shared support,
paper evaluations, and comparison runners while preserving existing imports
and commands.

## Acceptance Criteria

- [x] Examples do not import experiments.
- [x] Shared LLM clients expose response text, model identity, and token usage.
- [x] Minimal, gridworld, and push examples use a consistent layout.
- [x] Attribution evaluation lives under experiments and has a tested judge.
- [x] Experiment evaluators execute and time each condition once.
- [x] Public commands use the canonical example and experiment paths.
- [x] Public documentation reflects the final layout.
- [x] Full tests and smoke commands pass.

## Related

- CIP: [0013](../../cip/cip0013_examples-experiments-layout.md)

## Progress Updates

### 2026-09-19

Task started from the approved repository-reorganisation plan.

Reorganisation completed with compatibility shims. The complete suite passes
(128 tests, 14 optional-dependency skips). Stale modules remain in place until
a separately approved compatibility-breaking cleanup.

### 2026-09-19 — canonicalisation

Moved the real implementations into the new folders. Removed unused
`experiments/*/agents.py` and `experiments/multiprocess_interface.py`.
Removed the remaining compatibility shims and unused experiment run loops.
Canonical paths are the only remaining public commands.
