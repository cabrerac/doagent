# DOAgent Architecture: Three Layers

This document defines the three-layer architecture that separates **what end users use** from **what the DOAgent research project uses internally** for evaluation and comparison.

---

## 1. Overview

| Layer | Purpose | Audience | Public API |
|-------|---------|----------|------------|
| **Core library** (`doagent`) | Build multi-agent systems with transparent recording. | End users. | Yes — documented, stable. |
| **Analysis** (`doagent.analysis`) | Inspect and evaluate the multi-agent systems users build (trace graphs, provenance, causal attribution, interpretability). | End users. | Yes — tools for evaluating *their* systems. |
| **Validation / experiments** | Evaluate DOAgent itself: benchmarks, baselines, version comparisons, ablation studies. | Research team only. | No — internal tooling, not for end users. |

**Rule of thumb:**  
- **Analysis** = “How do I evaluate *my* system?” (user-facing).  
- **Validation** = “How do we evaluate *DOAgent*?” (internal).

---

## 2. Core Library (`doagent`)

**Purpose:** Let users build multi-agent systems with a single, config-driven API. The library records outcomes, traces, and agent decisions transparently.

**Public surface:** `Session`, `make_env`, `RunConfig`; config-driven setup via `Session.from_config`; `session.inspect(kind)` for post-run access. No `doagent.core` or `doagent.records` in user code.

**Documentation:** [library-boundaries.md](library-boundaries.md), [data-model-spec.md](data-model-spec.md), [adapter-contract.md](adapter-contract.md).

---

## 3. Analysis (`doagent.analysis`)

**Purpose:** Provide tools for end users to evaluate and interpret the multi-agent systems they implement with DOAgent. Works on any run output (records from their sessions).

**Planned surface:** Property-based submodules — e.g. `provenance`, `traceability`, `accountability`, `interpretability` — with functions that accept a records source (path, adapter, or iterator). Environment-agnostic.

**Use case:** “I ran my system with DOAgent; now I want trace graphs, causal attribution, or explanation summaries.” This is the **user-facing** evaluation story.

**Reference:** Backlog task `2026-03-04_analysis-module-library.md`; related CIPs 0006–0009.

---

## 4. Validation / Experiments (Internal)

**Purpose:** Support the DOAgent research project’s own evaluation: compare DOAgent with other systems, compare versions of DOAgent, run controlled benchmarks and baselines. Not for end users.

**Current location:** `doagent.validation` (runners, policy registry, env wrappers, `RunReporter`, `measure_baseline`, etc.).

**Target state:** Removed from the public API. Implemented either as:
- A private subpackage (e.g. `doagent._validation` or `doagent._experiments`), or  
- Code outside the main package (e.g. `experiments/` or `research/` at repo root).

**Implications:**
- Not documented as part of the public API.
- Not guaranteed stable across releases.
- Default install (e.g. `pip install doagent`) does not expose validation to end users; optional extras (e.g. `doagent[experiments]`) may be used for replication or development.

**Reference:** Backlog task for “validation internal / experiments” (move validation out of public surface and structure it for research use).

---

## 5. Summary

- **End users** use: **core library** to build systems, **analysis** to evaluate their systems.  
- **Research team** uses: **core library** plus **validation/experiments** to evaluate and compare DOAgent itself.  
- **Validation** is not part of the end-user contract; **analysis** is.

---

## References

- [Library Boundaries](library-boundaries.md)
- Backlog: `2026-03-04_analysis-module-library.md`, validation-internal-experiments task
- CIP-0001: Library First Architecture
