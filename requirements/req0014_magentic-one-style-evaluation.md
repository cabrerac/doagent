---
id: "0014"
title: "Magentic-One–Style LLM MAS Evaluation with Reproducible Attribution Comparison"
status: "In Progress"
priority: "High"
created: "2026-09-15"
last_updated: "2026-09-20"
related_tenets:
- "data-first-shared-model"
- "interpretability-and-traceability"
- "library-first"
- "model-agnostic-core"
- "provenance-and-accountability"
stakeholders:
- "researchers"
- "AAMAS 2027 paper authors"
- "agent developers"
tags:
- requirements
- validation
- evaluation
- llm-mas
- magentic-one
- reproducibility
---

# REQ-0014: Magentic-One–Style LLM MAS Evaluation with Reproducible Attribution Comparison

## Description

DOAgent must support a **reproducible research evaluation** on a Magentic-One–style LLM multi-agent system: a fixed specialist team coordinated by an orchestrator, run on a documented query subset from the Who&When / GAIA / AssistantBench family. The evaluation must make it possible to measure failure attribution (who / when) under a **conventional log-oriented regime** and under a **DOAgent data-oriented regime**, using the same attribution question family as Zhang et al. (Who&When), without treating Who&When’s published gold labels as a controlled counterpart for new DOAgent runs.

The Magentic-One–style system should be built **using DOAgent’s existing public capabilities** wherever they suffice. Gaps that block a faithful or paper-usable port are recorded as new requirements and/or CIPs rather than hidden as one-off forks of the core library.

**Why this matters**: The AAMAS paper claims concern data-oriented multi-agent systems, not toy games alone. Magentic-One is Who&When’s hand-crafted generalist baseline. Evaluating DOAgent on that style of system ties the library claim to a recognised LLM MAS setting and to interpretability / provenance outcomes.

**Who benefits**: Paper authors (credible, re-runnable eval), researchers comparing regimes, and developers who need a reference LLM MAS port on DOAgent.

## Acceptance Criteria

- [ ] A small DOAgent team (Phase 1) runs end-to-end and supports W / T / D attribution (paper-minimum). A Magentic-One–style team (Phase 2) is stretch; if it lands, Phase 1 is the proof of concept.
- [ ] Versioned tasks or plants and run configuration make paper runs reproducible (models, limits, logging level, topology, run manifests).
- [ ] Failure attribution is measured with LLM judges on W, T, and D plus lookup on D; gold is planted and/or newly annotated — not Who&When / TraceElephant published labels.
- [ ] Gaps that cannot be met with current DOAgent APIs are tracked as new requirements and/or CIPs (not silent workarounds in validation-only code that imply library features that do not exist).
- [ ] Gridworld / push remain development aids; they are not presented as the paper’s primary LLM MAS evaluation.

## Notes (Optional)

- Related validation REQs (games / self-adaptive / scientific discovery) stay in place. This REQ covers the **LLM generalist team** paper track.
- Who&When supplies system family, task sources, and attribution methods as related work. It does not replace a same-protocol log vs DOAgent comparison.
- Implementation HOW lives in CIP-0012 (and follow-on CIPs if gaps require library changes).

## References

- **Related Tenets**: data-first-shared-model, interpretability-and-traceability, library-first, model-agnostic-core, provenance-and-accountability
- **Validation overview**: [docs/validation-and-benchmarks.md](../docs/validation-and-benchmarks.md)
- **External**: Fourney et al., Magentic-One (arXiv:2411.04468); Zhang et al., Who&When (arXiv:2505.00212); [Agents_Failure_Attribution](https://github.com/ag2ai/Agents_Failure_Attribution)

## Progress Updates

### 2026-09-15
Requirement drafted (Proposed). Evaluation plan: reproduce Magentic-One as closely as feasible on DOAgent. Define reporting after implementation progress. Prefer building on current Session/topology/record APIs and open new REQ/CIP for gaps.

### 2026-09-18
In Progress with CIP-0012. Paper-minimum is Phase 1 (small team, W/T/D, lookup, costs). Magentic-One is Phase 2 stretch.

The addition-team experiment is in `experiments/attribution/` (orchestrator /
solver / checker; planted wrong sum; recoverability gold is the checker at
step 2). Independent Who&When and TraceElephant collectors, D0/D1 projections
from D2, lookup, GPT-4o judges, and unpaired W/T/D0/D1/D2 capture-cost runs
are in place. W and T are not projected from D.
