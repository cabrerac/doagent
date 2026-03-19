---
id: "2026-03-10_validation-internal-experiments"
title: "Validation internal: remove from public API, structure for research/experiments"
status: "Completed"
priority: "High"
created: "2026-03-10"
last_updated: "2026-03-19"
category: "features"
related_cips:
- "0001"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- validation
- architecture
- experiments
- public-api
---

# Task: Validation internal — remove from public API, structure for research/experiments

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Aligns with the three-layer architecture: core library and analysis are for end users; validation is for the DOAgent research project's own evaluation.

## Description

DOAgent is a research project. We need to evaluate it, compare it with other systems, and compare different versions of itself. Those evaluation tools are for the research team, not for end users. End users evaluate *their* multi-agent systems via the **analysis** module (trace graphs, provenance, causal attribution, interpretability). Therefore:

- **Remove validation from end-user access.** The former `doagent.validation` package has been removed; no validation code lives under `doagent`.
- **Architect validation for our purposes.** Validation/experiments code lives in `experiments/` at repo root (runners, reporters, baselines, push/gridworld scenario wiring). End-user demos are in `examples/push_demo/` and `examples/gridworld_demo/` and use only the public Session API.

**Reference:** [docs/architecture-layers.md](../../docs/architecture-layers.md) — core library | analysis (user-facing) | validation/experiments (internal).

## Goals

1. ~~End users never need to import `doagent.validation`.~~ **Done:** `doagent.validation` removed. Public surface is **only** `doagent.Session`, `doagent.RunConfig`, and `doagent.make_env`; `doagent.analysis` (when implemented) will be the user-facing way to analyse records. Adapters, PolicyRegistry, and record types are internal (`doagent.core` / `doagent.records`).
2. Validation/experiments code remains in the repo and usable by the research team: `experiments/` at repo root.
3. Default install does not expose validation as part of the public API; demos in `examples/` use Session API and optionally import `experiments` for running comparisons.
4. Documentation and packaging clearly separate "what users use" from "what we use for research."

## Implementation Notes (completed)

- Removed `doagent.validation` entirely. Session.from_config uses `doagent.core.noop_adapter` and `doagent.core.policy`.
- Created `experiments/` at repo root: baseline, reporting, environment, multiprocess_interface, push/, gridworld/.
- Restructured examples: `examples/push_demo/`, `examples/gridworld_demo/`, `examples/minimal_usage.py`; removed `examples/validation/` and `examples/features/`.
- Updated docs (README, architecture-layers, library-boundaries) and this backlog task.

## Related

- [docs/architecture-layers.md](../../docs/architecture-layers.md) — three-layer model (core | analysis | validation/experiments)
- CIP-0001: Library First Architecture
- Backlog: 2026-03-04_analysis-module-library (user-facing analysis)
- Backlog: 2026-03-04_config-driven-api (completed; examples no longer rely on validation in user path)
