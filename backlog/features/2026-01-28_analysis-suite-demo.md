---
id: "2026-01-28_analysis-suite-demo"
title: "Analysis suite for interpretability and traceability demo"
status: "Completed"
priority: "High"
created: "2026-01-28"
last_updated: "2026-01-28"
category: "features"
related_cips:
- "0006"
- "0007"
- "0008"
owner: "Christian Cabrera"
dependencies: []
tags:
- backlog
- analysis
- interpretability
- traceability
- demo
---

# Task: Analysis suite for interpretability and traceability demo

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Build presentation-ready analysis tools that demonstrate DOAgent's interpretability and traceability from recorded data. Four scripts in `examples/analysis/`:

1. **trace_graph.py** — Directed state-transition graph from trace records; nodes = outcomes, edges = traces coloured by agent; wrapped grid layout for chain-like graphs; exports PNG, PDF, DOT.
2. **provenance_walker.py** — Walks provenance chain backwards from any record; outputs formatted text tree and matplotlib tree diagram.
3. **causal_attribution.py** — Per-agent causal contribution from traces; line chart (cumulative discovery), bar chart (total discovery), decision effectiveness (productive vs redundant).
4. **topology_comparison.py** — Runs gridworld under centralised, peer-to-peer, federated topologies; side-by-side comparison of graph structure, coverage, and attribution.

## Acceptance Criteria

- [x] Trace graph builds from trace.jsonl, outcome.jsonl, agent_update.jsonl; renders with agent-coloured edges.
- [x] Provenance walker supports "last" or record ID; outputs chain and tree diagram.
- [x] Causal attribution uses trace edges to attribute discoveries per agent; produces 3 charts.
- [x] Topology comparison runs 3 topologies with same seed; produces comparison charts.
- [x] All scripts documented in examples/analysis/README.md.

## Implementation Notes

- Uses networkx for graph construction, matplotlib for rendering.
- Configs for short demo run and topology comparison in examples/analysis/configs/.

## Related

- CIP: 0006, 0007, 0008
- Documentation: examples/analysis/README.md

## Progress Updates

### 2026-01-28
Completed. All four scripts implemented and tested. Demo presented successfully.
