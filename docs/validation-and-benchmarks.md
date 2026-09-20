# Validation and Benchmarks

This document describes how DOAgent approaches validation and how the agentic reasoning paper’s benchmarks and application domains inform our validation strategy. It also states an important design principle: **the library is generic** and is intended for use in scenarios beyond the ones we implement as validation examples.

---

## Library is generic; validation examples are a subset

**The DOAgent library is designed to be usable in any use case that fits the data-oriented agent model** — shared data as the interface, configurable topology, open participation, traceability, and provenance. Our **validation examples** (e.g. gridworld, simple push, and any future scientific-discovery or self-adaptive scenarios) are a **chosen subset** of possible applications. They exist to:

- **Demonstrate** that the library supports the required behaviours (coordination, shared data, interpretability, traceability).
- **Stress-test** the three DOA principles (shared-data model, decentralisation, openness) and the recording/analysis pipeline.
- **Provide** reproducible, documented scenarios for development and regression.

They do **not** define the only use cases the library supports. Users can build their own environments, benchmarks, and application domains (scientific discovery, code generation, tool use, custom multi-agent games, etc.) on top of the same public API and data model. Validation scenarios are **reference implementations**, not an exhaustive or limiting set.

**Possible external use case (2026-07-13):** ai@cam is developing an AI-policy project that involves simulating social systems in which local and government authorities (and related actors) interact. Jess and Radzim framed this as an opportunity for multi-agent systems architectures. DOAgent is a natural fit: authorities as agents coordinating through a shared data model, with configurable topology, open participation, and traceable decisions. We should treat this as a candidate application domain for demos or collaboration—not a committed validation REQ yet—alongside the paper-aligned scenarios below.

---

## Paper as reference for benchmarks and application domains

The **agentic reasoning paper** (see `papers/agentic-reasoning-llm-reading-guide.md`) discusses **§6 Applications** and **§7 Benchmarks**: concrete domains and evaluation setups used in the literature (e.g. mathematical reasoning, scientific discovery, code generation, tool use, multi-agent coordination, self-evolving or adaptive systems). We use that discussion as a **reference** when deciding which validation scenarios to implement and how to prioritise them. We do not commit to implementing every benchmark the paper mentions; we use the list to align our validation work with established domains and to justify our choices. Apart from the paper's alternatives we should explore and do something for the [Denario project](https://astropilot-ai.github.io/DenarioPaperPage/) ([GitHub](https://github.com/AstroPilot-AI/Denario)).

---

## Mapping: paper domains → our validation requirements and DOA principles

| Paper domain / benchmark type | Our validation requirement | DOA principles stressed |
|-------------------------------|----------------------------|--------------------------|
| **Multi-agent games, coordination** | REQ-0010 (Validation on Multi-Agent Games) | Shared data (communication channel), decentralisation (topology, visibility), openness (participation). |
| **Self-adaptive systems, runtime reconfiguration** | REQ-0011 (Validation on Self-Adaptive Systems) | Decentralisation (control distribution), openness (agents joining/leaving, adaptation). |
| **Scientific discovery, mathematical reasoning** | REQ-0012 (Validation on Scientific Discovery in Maths) | Shared data (reasoning traces, provenance), interpretability and traceability, accountability. |
| **Tool use, long-horizon reasoning / generalist LLM MAS** | REQ-0014 (Magentic-One–style evaluation); CIP-0012 | Shared data (ledgers, tool results), decentralisation (federated orchestrator hub), interpretability / provenance for who/when. |
| **Code generation, program synthesis** | (No dedicated REQ; optional future validation; Coder role appears inside REQ-0014) | Traceability, provenance, accountability. |

Validation scenarios we implement (e.g. gridworld, push, Magentic-One–style LLM MAS, and future scientific-discovery or self-adaptive demos) are selected from this space to cover the three DOA principles and to match REQ-0010–REQ-0012 and REQ-0014. When we add or change validation examples, we refer to the paper’s §6/§7 and to this mapping to keep validation aligned with recognised benchmarks and application domains.

---

## AAMAS 2027 paper evaluation (updated 2026-09-20)

The paper reports a **current multi-agent** setting hosted on DOAgent, not the in-repo games as the lead story. Gridworld and push stay **development / fast runs**. Do not use OpenAI multi-agent emergence as the paper env (classic RL, not 2026 LLM MAS).

**Authoritative design:** [REQ-0014](../requirements/req0014_magentic-one-style-evaluation.md) and [CIP-0012](../cip/cip0012_magentic-one-doa-evaluation.md) (**In Progress**). Use **current** DOAgent APIs; open a new REQ/CIP for library gaps.

**What goes in the paper**

- **Phase 1 (paper-minimum):** a **small** addition team in `experiments/attribution/` (gold = checker / step 2). **Attribution (paired):** one D2 run writes full records; observe-only Who&When and TraceElephant-static collectors write from that same run; D0/D1 are projected from D2; judges score W, T, D0, D1, and D2; lookup uses D2. **Capture cost (unpaired):** live W, T, D0, D1, and D2. Time includes writing the capture log; bytes count only `who_when.json`, `trace_elephant.json`, or `records/`. Run `python -m experiments.runners.attribution_comparison` for cost and `--table accuracy` for judges.
- **Phase 2 (stretch; design 2026-09-20):** five Magentic-One roles on a Session. Specialists are AutoGen `MultimodalWebSurfer`, `FileSurfer`, `MagenticOneCoderAgent`, and `CodeExecutorAgent`. Do not run `MagenticOneGroupChat`. Same W/T/D protocol. New gold (planted or annotated). If it lands, it leads the paper and Phase 1 is the proof of concept.
- Not Who&When / TraceElephant published gold or published accuracies as the controlled arm. Not a task-success bake-off against AutoGen or AgentScope.

Zhang et al. (Who&When) and Chen et al. (TraceElephant) share the who/when question and the W/T observability regimes. Bib: `doagent-paper/references.bib`.

---

## Candidate evaluation environments

Possible environments to evaluate DOAgent, in addition to the in-repo gridworld and push demos. None of these is a committed validation requirement.

- [Multi-agent emergence environments](https://github.com/openai/multi-agent-emergence-environments)

---

## Related links

- [Agent2Agent Protocol (A2A)](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [The Denario Project](https://astropilot-ai.github.io/DenarioPaperPage/)
- [Designing AI agents that know when to step back](https://www.amazon.science/blog/designing-ai-agents-that-know-when-to-step-back)

---

## References

- **Reading guide:** `papers/agentic-reasoning-llm-reading-guide.md` — efficient reading order; §6 Applications and §7 Benchmarks as reference.
- **Validation requirements:** REQ-0010 (multi-agent games), REQ-0011 (self-adaptive systems), REQ-0012 (scientific discovery in maths), REQ-0014 (LLM MAS attribution evaluation).
- **Validation CIPs:** CIP-0010 (Validation on Multi-Agent Games); CIP-0012 (LLM MAS attribution evaluation, In Progress); additional CIPs for REQ-0011 and REQ-0012 when implemented.
