---
id: "2026-03-10_validation-internal-experiments"
title: "Validation internal: remove from public API, structure for research/experiments"
status: "Proposed"
priority: "High"
created: "2026-03-10"
last_updated: "2026-03-10"
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

- **Remove validation from end-user access.** The current `doagent.validation` package must not be part of the documented, supported public API.
- **Architect validation for our purposes.** Structure it as internal tooling for running experiments, benchmarks, baselines, and version comparisons. No need to keep it "user-friendly"; we control the runners and configs.

**Reference:** [docs/architecture-layers.md](../../docs/architecture-layers.md) — core library | analysis (user-facing) | validation/experiments (internal).

## Goals

1. End users never need to import `doagent.validation`. Public surface is `doagent` (Session, make_env) and `doagent.analysis` (when implemented).
2. Validation/experiments code remains in the repo and usable by the research team for evaluating DOAgent (benchmarks, baselines, topology comparisons, etc.).
3. Default install (e.g. `pip install doagent`) does not expose validation as part of the public API; optional extra (e.g. `pip install doagent[experiments]`) may be used for replication or development.
4. Documentation and packaging clearly separate "what users use" from "what we use for research."

## Alternatives Considered

### Where to put validation code

- **A. Private subpackage (`doagent._validation` or `doagent._experiments`):** Keep under `doagent` but prefix with underscore; exclude from `doagent` public exports and from docs. Pro: single package, simple layout. Con: still inside the main package namespace.
- **B. Separate top-level directory (`experiments/` or `research/`):** Move validation runners, reporters, baseline helpers, and scenario wiring to a directory at repo root that is not part of the `doagent` package. Pro: clear separation; `doagent` package contains only core + analysis. Con: imports may need path or package adjustments; tests and examples under `examples/validation/` would import from this location.
- **C. Optional extra only:** Keep `doagent.validation` but do not document it; ship it only when installing `doagent[experiments]`. Pro: one codebase. Con: validation is still a submodule of the main package; naming suggests it is "validation for users."

**Recommendation:** Explore A (private subpackage) first: rename to `doagent._experiments` or keep as `doagent._validation`, remove from `doagent`'s public `__all__` and from any re-exports, update docs to state that only `doagent` and `doagent.analysis` are the public API. If we later want stronger separation, we can move to B.

## Acceptance Criteria

- [ ] Validation code is not part of the public API: not listed in user-facing docs, not re-exported from `doagent` top-level, and either under a private name (e.g. `_validation` / `_experiments`) or in a non-package directory.
- [ ] Public API documentation (README, library-boundaries, architecture-layers) states that the supported surface is core library + analysis; validation/experiments are for internal/research use.
- [ ] Our own tests and experiment scripts (e.g. `examples/validation/`, analysis comparison scripts) can still run and import validation/experiments code (via the chosen internal location).
- [ ] Packaging (e.g. `pyproject.toml` or `setup.cfg`) does not advertise or require validation for normal install; optional extra for experiments is documented if we ship it.

## Implementation Notes

- Rename `doagent.validation` to `doagent._validation` (or `doagent._experiments`) and update all internal imports (tests, examples/validation, Session.from_config if it uses NoOpSharedData from validation, etc.).
- Remove any re-export of validation from `doagent/__init__.py` if present. Ensure `doagent` only exposes Session, make_env, RunConfig, and (when implemented) analysis.
- Update [docs/architecture-layers.md](../../docs/architecture-layers.md) and [docs/library-boundaries.md](../../docs/library-boundaries.md) §6 to state that validation scenarios are internal; point to architecture-layers for the three-layer model.
- Update README and any "quick start" or "API" sections to mention only core + analysis.
- If we use an optional extra: add `[experiments]` (or similar) to pyproject.toml that pulls in or exposes the private module for development/replication; document in CONTRIBUTING or a dedicated "Replicating experiments" section.

## Related

- [docs/architecture-layers.md](../../docs/architecture-layers.md) — three-layer model (core | analysis | validation/experiments)
- CIP-0001: Library First Architecture
- Backlog: 2026-03-04_analysis-module-library (user-facing analysis)
- Backlog: 2026-03-04_config-driven-api (completed; examples no longer rely on validation in user path)
