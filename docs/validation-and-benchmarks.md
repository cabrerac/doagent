# Validation and Benchmarks

This document describes how DOAgent approaches validation and how the agentic reasoning paper’s benchmarks and application domains inform our validation strategy. It also states an important design principle: **the library is generic** and is intended for use in scenarios beyond the ones we implement as validation examples.

---

## Library is generic; validation examples are a subset

**The DOAgent library is designed to be usable in any use case that fits the data-oriented agent model** — shared data as the interface, configurable topology, open participation, traceability, and provenance. Our **validation examples** (e.g. gridworld, simple push, and any future scientific-discovery or self-adaptive scenarios) are a **chosen subset** of possible applications. They exist to:

- **Demonstrate** that the library supports the required behaviours (coordination, shared data, interpretability, traceability).
- **Stress-test** the three DOA principles (shared-data model, decentralisation, openness) and the recording/analysis pipeline.
- **Provide** reproducible, documented scenarios for development and regression.

They do **not** define the only use cases the library supports. Users can build their own environments, benchmarks, and application domains (scientific discovery, code generation, tool use, custom multi-agent games, etc.) on top of the same public API and data model. Validation scenarios are **reference implementations**, not an exhaustive or limiting set.

---

## Paper as reference for benchmarks and application domains

The **agentic reasoning paper** (see `papers/agentic-reasoning-llm-reading-guide.md`) discusses **§6 Applications** and **§7 Benchmarks**: concrete domains and evaluation setups used in the literature (e.g. mathematical reasoning, scientific discovery, code generation, tool use, multi-agent coordination, self-evolving or adaptive systems). We use that discussion as a **reference** when deciding which validation scenarios to implement and how to prioritise them. We do not commit to implementing every benchmark the paper mentions; we use the list to align our validation work with established domains and to justify our choices. Apart from the paper's alternatives we should explore and do something for the [Denario project](https://github.com/AstroPilot-AI/Denario)

---

## Mapping: paper domains → our validation requirements and DOA principles

| Paper domain / benchmark type | Our validation requirement | DOA principles stressed |
|-------------------------------|----------------------------|--------------------------|
| **Multi-agent games, coordination** | REQ-0010 (Validation on Multi-Agent Games) | Shared data (communication channel), decentralisation (topology, visibility), openness (participation). |
| **Self-adaptive systems, runtime reconfiguration** | REQ-0011 (Validation on Self-Adaptive Systems) | Decentralisation (control distribution), openness (agents joining/leaving, adaptation). |
| **Scientific discovery, mathematical reasoning** | REQ-0012 (Validation on Scientific Discovery in Maths) | Shared data (reasoning traces, provenance), interpretability and traceability, accountability. |
| **Tool use, long-horizon reasoning** | (No dedicated REQ; can be covered by examples or future REQ) | Shared data (memory, search), policy factorisation (reason vs. action). |
| **Code generation, program synthesis** | (No dedicated REQ; optional future validation) | Traceability, provenance, accountability. |

Validation scenarios we implement (e.g. gridworld, push, and future scientific-discovery or self-adaptive demos) are selected from this space to cover the three DOA principles and to match REQ-0010, REQ-0011, and REQ-0012. When we add or change validation examples, we refer to the paper’s §6/§7 and to this mapping to keep validation aligned with recognised benchmarks and application domains.

---

## References

- **Reading guide:** `papers/agentic-reasoning-llm-reading-guide.md` — efficient reading order; §6 Applications and §7 Benchmarks as reference.
- **Validation requirements:** REQ-0010 (multi-agent games), REQ-0011 (self-adaptive systems), REQ-0012 (scientific discovery in maths).
- **Validation CIPs:** CIP-0010 (Validation on Multi-Agent Games); additional CIPs for REQ-0011 and REQ-0012 when implemented.
