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

## AAMAS 2027 paper evaluation (updated 2026-09-23)

The paper reports a **current multi-agent** setting hosted on DOAgent, not the in-repo games as the lead story. Gridworld and push stay **development / fast runs**. Do not use OpenAI multi-agent emergence as the paper env (classic RL, not 2026 LLM MAS).

**Authoritative design:** [REQ-0014](../requirements/req0014_magentic-one-style-evaluation.md) and [CIP-0012](../cip/cip0012_magentic-one-doa-evaluation.md) (**In Progress**). Use **current** DOAgent APIs; open a new REQ/CIP for library gaps.

**What goes in the paper**

- **Phase 1 (paper-minimum):** a **small** addition team in `experiments/attribution/` (gold = checker / step 2). **Attribution (paired):** one D2 run writes full records; observe-only Who&When and TraceElephant-static collectors write from that same run; D0/D1 are projected from D2; judges score W, T, D0, D1, and D2; lookup uses D2. **Capture cost (unpaired):** live W, T, D0, D1, and D2. Time includes writing the capture log; bytes count only `who_when.json`, `trace_elephant.json`, or `records/`. Run `python -m experiments.runners.attribution_comparison` for cost and `--table accuracy` for judges.
- **Phase 2 (in progress):** five Magentic-One roles in `experiments/magentic_one/`. The judge reads that team's roster from `gold.json`. A stand-in answers through `on_messages`, and the Session stores the action. The four AutoGen specialist classes construct, and one live browser smoke wrote gold and collector packs. Do not run `MagenticOneGroupChat`. Same W/T/D protocol. Campaign `--team magentic_one` runs the stand-in team.
- Not Who&When / TraceElephant published gold or published accuracies as the controlled arm. Not a task-success bake-off against AutoGen or AgentScope.

**Runs on 2026-09-23.** `attribution_campaign_20260923_000112` used the capital question and a planted web fact of Lyon. DOAgent levels did not beat Who&When. The judge already knew Paris, and a level-1 link moved the blame onto WebSurfer. `attribution_campaign_20260923_004741` used crate 4817 (web code M-19, file code M-17, accept at step 4). Almost every pack scored 1.00. Who&When was as accurate and cheaper. The plan text said to accept a code only when the two sources agree, and every pack contained that sentence.

**Restart next session.** Build a who and when case as close as possible to an execution in the Who&When dataset. The trajectory should be long, with distractor steps. The accept note should state only the code the orchestrator believes. The plan should not contain the grading rule. New gold stays on the missed check. Published `mistake_agent` and `mistake_step` values are not copied onto a log we did not replay.

**Open question, discuss before coding.** If a dataset execution is fully described, it is not yet clear why this implementation cannot reproduce that execution. Settle that before writing another plant.

Zhang et al. (Who&When) and Chen et al. (TraceElephant) share the who/when question and the W/T observability regimes. Bib: `doagent-paper/references.bib`.

---

## Candidate evaluation environments

Possible environments to evaluate DOAgent, in addition to the in-repo gridworld and push demos. None of these is a committed validation requirement.

- [Multi-agent emergence environments](https://github.com/openai/multi-agent-emergence-environments)

---

## Candidate: network-change detection (recorded 2026-09-23)

This is a proposal for a second experiment. It is not implemented, and it is not a paper result.

The attribution campaign asks who made one failure inevitable. This experiment asks when the shape of the whole network changes. A ledger fits the second question because the signal is a pattern across many agents.

Agentic services computing is the message-interface neighbour. A service call exists in flight, and a later reader depends on a log kept beside the service. That is the hypothesis for the transient side. It is not a result. Service systems already keep bus logs. If both sides retain the same edges, detection can tie, and the data-oriented gain is that the detector reads the interface.

### Visibility regimes

These are four ways the detector is allowed to see edges. They are not four steps of "more data."

| Regime | What the detector may read |
| --- | --- |
| Current tick | Messages from this tick only. The buffer is wiped afterwards. |
| Siloed ledger | Records inside one visibility silo. Cross-silo edges can be missing. |
| Global ledger | The append-only history of state changes. |
| Ledger plus notes | That history, plus the note each agent stored with its action. |

A siloed ledger can see less than one full tick. Plot the four regimes as categories.

A fair run keeps three checks.

- The traditional side may retain the same edges the ledger retains. A win with no retained log only shows that memory helps.
- The injected change must be too small to see in one tick. A cartel that rewires every edge inside the trigger tick is already visible without a ledger.
- Agent notes record a local belief, such as a price. They do not announce the cartel or the echo chamber.

The sample generators switch the rules at a chosen step. That is an injected change. It is ground truth for the detector. It is not spontaneous emergence.

Count alarms on the random phase, over many repeats, before reporting lead time. Lead time is the tick of the first alarm minus the trigger tick. An alarm before the trigger is a false alarm.

### What the library already provides

Read records with `Session.inspect`. Logging levels are 0, 1, and 2. Shared storage is `memory`, `file`, `mongo`, or `noop`. Mongo needs `pymongo`. There is no `get_accessible_records()` method. Provenance on a record is a list of source ids. It is not an intent vector.

### Reusable pieces

Check the entropy number on a random graph and on a star before any agent run. Build the graph with NetworkX. Take the eigenvalues of the symmetric normalized Laplacian with `numpy.linalg.eigvalsh`. That exact step is cubic in the number of nodes.

`networkx.spectral_graph_forge` generates a graph. It does not compute this entropy. `algebraic_connectivity` is a different single number. Do not use either as the detector.

FINGER is a published linear-time approximation for von Neumann graph entropy. It is a candidate once the exact eigenvalue check is in place. Confirm the paper and the code before depending on them. An empty tick must not be scored as a collapse.

Compare the entropy alarm with other detectors on the same edges. Candidates are dynamic betweenness (`networkx.betweenness_centrality`), the distance between successive adjacency matrices, and, for the opinion case, Louvain modularity (`networkx.community.louvain_communities`). These are controls. They are not a proof that entropy is better.

Agent behaviour can be generated outside DOAgent and then written into a session.

- Resource trading: adapt a Mesa trade or resource model. Mesa's own scheduler stays outside the run. Each trade is either a transient message or a session record.
- Opinion change: the Hegselmann-Krause model in NDlib (`ndlib.models.opinions.HegselmannKrauseModel`). Convert each step into read and post records. The bounded-confidence cutoff is the injected rule, and it belongs in the generator, not in an agent note that confesses the split.

Public graphs are a later check, after the synthetic runs. The Enron email corpus is a real temporal network. Confirm how it is loaded. Do not assume `networkx.enron_graph()` exists. A Moltbook observatory archive was named with the citation arXiv:2605.13860. Confirm that citation before use.

### Order of work

1. Toy graphs: random graph versus star, with false alarms counted.
2. Trading generator, current-tick window versus the same edges retained.
3. The same trades written through `Session`, read back with `inspect`.
4. Opinion generator, only if the trading case still shows a difference once memory is fair.
5. Plots of lead time, false alarms, and the time to build the spectrum. One series per visibility regime.

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
