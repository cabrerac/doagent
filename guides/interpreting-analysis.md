# Interpreting analysis artefacts

After a persisted run, `doagent.analysis` can write analysis artefacts under:

`output_base/<run_id>/analysis/<category>/` 

This guide matches the **current** rendering in `doagent/analysis/*.py`. The current set of analysis tools is an **expandable demonstration** of the analysis DOAgent enables, not a closed list. Use this guide together with the [README Analysis section](../README.md#analysis) and the demo notebooks.

---

## Where files land


| Category             | Typical files                                         | When to use                                             |
| -------------------- | ----------------------------------------------------- | ------------------------------------------------------- |
| **provenance**       | `provenance_tree.png`, `provenance_tree.pdf`          | “Why did this outcome happen?” — chain of records       |
| **traceability**     | `trace_graph.png`, `trace_graph.pdf`, optional `.dot` | “How did state evolve?” — transition graph              |
| **accountability**   | `causal_attribution.png`, `causal_attribution.pdf`    | Discovery / grid-style scenarios with cell observations |
| **interpretability** | `atomic_explanations_for_last.json` | Transition-level atomic explanation units with Level 1/2 rendering data |


Push-style demos often skip **accountability** (no meaningful “cells discovered” semantics). Grid-world demos run all four.

---

## Provenance chain tree (`provenance_tree.*`)

**What it shows:** A tree rooted at one record (by default the **last outcome** when you call `render_chain_tree("last", ...)`). Walking **backward** through provenance and trace links, it shows which **outcomes**, **traces**, **agent_updates**, and **initial_state** connect to that outcome.

**How to read it:**

- **Layout:** Depth increases to the **left** (the chosen outcome sits toward the **right**; earlier causes spread left). Multiple siblings at the same depth are stacked vertically.
- **Node colours (record kind):**
  - Light blue (`#87ceeb`): **outcome**
  - Light green (`#90EE90`): **agent_update**
  - Gold (`#FFD700`): **trace**
  - Dark grey (`#333333`): **initial_state**
  - Grey (`#DDDDDD`): other / unknown kinds
- **Arrow colours (relation on the edge):** Arrows run from **child → parent** in the diagram (toward records that explain the child).
  - Blue (`#1f77b4`): **derived_from**
  - Red (`#d62728`): **trace_to**
  - Green (`#2ca02c`): **enabled_by**
  - Orange (`#ff7f0e`): **from**

**Practical tips:** If the tree is wide, reduce scope by analysing a specific `record_id`, or rely on the trace graph for global structure. Truncation appears when the walk hits max depth or revisits a node (“already visited” in the JSON chain if you export it elsewhere).

---

## Trace graph (`trace_graph.*`)

**What it shows:** A **directed multigraph** of **states** (outcome nodes) and **transitions** (one edge per **trace** record). Edges are coloured by the **agent** who enabled the transition. Parallel edges between the same pair of nodes are normal when several agents act in one step.

**How to read it:**

- **Layout:** Usually **by round** on the horizontal axis (`r0`, `r1`, …). If the run is a single chain with many rounds, the layout may **wrap** into multiple rows for readability.
- **Node labels:** `S0` = **initial state**; otherwise `r<round>` = outcome at that round (short labels; full ids are in the underlying graph / records).
- **Node colours:**
  - Dark (`#333333`): **initial** state
  - Gold (`#ffd700`): **dedup convergence** — many incoming edges (in-degree **greater than** `max(number of agents, 1)`), i.e. several traces point at the same outcome (common when logging collapses or converges).
  - Light blue (`#87ceeb`): ordinary outcome nodes
- **Node size:** Grows slightly with high in-degree so convergence nodes stand out.
- **Edge colours:** Match the **legend** — `agent_0`…`agent_3` use fixed palette colours; other agent names use grey (`#999999`). Curved edges separate multiple parallel transitions between the same nodes.

**Practical tips:** Use this view to see **branching**, **reconvergence**, and **who moved** between which states. For “why this state,” pair with the provenance tree or `interpretability.get_explanations_for`.

---

## Causal attribution (`causal_attribution.*`)

**What it shows:** Three panels derived from **trace** records and **outcome** observations (grid / discovery-style payloads with per-agent **cells** in observations).

**How it works (short):** For each trace, the code compares the acting agent’s observed **cells** at the **to** outcome vs the **from** outcome. If the agent sees **new** cells relative to their own prior view, that transition counts as **productive**; otherwise **redundant**. **Globally new** cells (not seen by anyone earlier in the same round’s accounting) feed **cumulative discovery** per agent.

**How to read the panels:**

1. **Left — cumulative over rounds:** Y-axis is **“Cumulative cells discovered”** when discovery data exists, otherwise **“Cumulative contribution”**. One line per agent; it steps up when that agent’s globally new cells increase.
2. **Middle — totals:** Bar height = **count of unique cells** in that agent’s discovered set (cardinality of attributed discovery), with the number printed on the bar.
3. **Right — decision effectiveness:** Stacked bars — **green** = **productive** transitions, **red** = **redundant** transitions (per agent). The **percentage** on top is productive / (productive + redundant) for that agent.

**Agent colours** in lines and bars align with the trace graph (`agent_0` blue, `agent_1` orange, `agent_2` green, `agent_3` red; others grey).

**When to skip:** Scenarios without per-agent **observations.cells** (e.g. simple push games) — bars may be empty or uninformative; omit `accountability.causal_attribution` for those runs.

---

## Interpretability JSON (`atomic_explanations_for_last.json`)

**What it shows:** A JSON list of transition-level atomic explanation units for the **record_id** you pass to `build_atomic_explanations` (filename currently `atomic_explanations_for_last.json` for compatibility with existing analysis naming).

**Typical contents:** each unit includes machine fields (`from_state_id`, `to_state_id`, `agent_id`, `decision_id`, `decision_action`, `links`, `evidence_refs`) and interpretation fields (`level`, `rationale_text`, `rendered_text`).

**Requirements:** Meaningful rationale text (Level 2) needs decision-attached explanation text and/or linked explanation records. Runs without rationale text still produce valid Level 1 units.

### Atomic explanation view (Level 1 vs Level 2)

Interpretability should be read as transition-level atomic explanations:

- `old_state -> decision -> (optional rationale) -> new_state`

Current levels:

- **Level 1 (decision-link only):** decision linkage exists but no explicit rationale text.
  - Example: `System was at state S14. Agent agent_2 made decision move_east. As a result, the system ended at state S15.`
- **Level 2 (explicit rationale):** decision linkage exists and rationale text is present.
  - Example: `System was at state S14. Agent agent_2 made decision move_east because "I moved east to explore unseen cells near the boundary." As a result, the system ended at state S15.`

For the ongoing storage/retrieval/presentation roadmap, see:
`backlog/features/2026-03-19_explanations-storage-doc.md`.

### Atomic explanations export (`atomic_explanations_for_last.json`)

Use `interpretability.build_atomic_explanations(record_id, run_id, ...)` to get a transition-level artefact directly.

Each unit includes machine-friendly fields such as:
- `from_state_id`, `to_state_id`, `agent_id`, `decision_id`, `decision_action`
- `rationale_text` (optional), `level` (1/2), `links`, `evidence_refs`
- `rendered_text` (human-friendly sentence)

This gives a practical bridge between raw records and user-facing interpretability text, and can feed downstream QA/summarisation workflows.

---

## Quick cross-check with code

Legend and layout are defined in:

- `doagent/analysis/provenance.py` — `kind_colors`, `relation_colors`, `render_chain_tree`
- `doagent/analysis/traceability.py` — `render_trace_graph` (node colours, legend patches)
- `doagent/analysis/accountability.py` — `render_attribution_charts`, `_compute_attribution`

If behaviour changes in a release, update this guide to match.