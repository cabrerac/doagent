---
id: "2026-03-04_analysis-module-library"
title: "Implement doagent.analysis module with property-based submodules"
status: "Proposed"
priority: "High"
created: "2026-03-04"
last_updated: "2026-03-04"
category: "features"
related_cips:
- "0006"
- "0007"
- "0008"
- "0009"
owner: "Christian Cabrera"
dependencies:
- "2026-01-28_analysis-suite-demo"
tags:
- backlog
- analysis
- interpretability
- traceability
- provenance
- accountability
---

# Task: Implement doagent.analysis module with property-based submodules

> **Note**: Backlog tasks are DOING the work defined in CIPs (HOW).
> Use `related_cips` to link to CIPs. Don't link directly to requirements (bottom-up pattern).

## Description

Promote the analysis scripts from `examples/analysis/` into a first-class library module `doagent.analysis`, organised by the property each analysis enables. Users can call analysis functions for any environment or experiment. The module is designed for easy extension with new analysis approaches.

**Import pattern**: `from doagent.analysis import provenance, traceability, accountability, interpretability`

**Structure**:
```
doagent/
  analysis/
    __init__.py       # Re-exports submodules
    provenance.py     # Chain walking, "who created what from what"
    traceability.py   # Trace graph, graph traversal, "which actions influenced this outcome"
    accountability.py # Causal attribution, "who contributed what"
    interpretability.py # Explanation retrieval (minimal initially), decision summaries
```

**Design principles**:
- Each submodule exposes functions that accept a records source (path, adapter, or iterator).
- Environment-agnostic: works with any DOAgent run output, not just gridworld.
- Extensible: new analyses added as functions in the appropriate property submodule.

## Alternatives Considered

- **Alternative A**: Keep analysis as standalone scripts in examples/ — users copy and modify. Rejected: not reusable, no library API.
- **Alternative B**: Single flat `doagent.analysis` module with all functions. Rejected: harder to discover, no clear grouping.
- **Alternative C**: Property-based submodules (selected). Rationale: aligns with CIPs 0006–0009, intuitive import (`from doagent.analysis import provenance`), clear extensibility.

## Acceptance Criteria

### Provenance submodule (`doagent.analysis.provenance`)
- [ ] `walk_chain(record_id, records_source, max_depth)` — walk derived_from chain backwards, return structured chain
- [ ] `render_chain_tree(record_id, records_source, output_path)` — produce tree diagram (PNG/PDF)
- [ ] Records source can be Path (to records dir), SharedDataAdapter, or dict of lists

### Traceability submodule (`doagent.analysis.traceability`)
- [ ] `build_trace_graph(records_source)` — return networkx MultiDiGraph from trace/outcome/agent_update records
- [ ] `get_traces_to(record_id, records_source)` / `get_traces_from(record_id, records_source)` — retrieval helpers
- [ ] `render_trace_graph(graph, output_path)` — export PNG/PDF/DOT
- [ ] Graph layout handles chain-like and branching structures

### Accountability submodule (`doagent.analysis.accountability`)
- [ ] `causal_attribution(records_source)` — per-agent contribution from trace edges, return structured dict
- [ ] `render_attribution_charts(attribution, output_path)` — line chart, bar chart, effectiveness chart
- [ ] Attribution logic uses agent-specific observations (not first-agent-wins)

### Interpretability submodule (`doagent.analysis.interpretability`)
- [ ] `get_explanations_for(record_id, records_source)` — retrieve explanation/decision records for a record
- [ ] Minimal initially; extensible for summarisation, aggregation in future

### Module structure
- [ ] `doagent.analysis` package with `__init__.py` re-exporting submodules
- [ ] Examples in `examples/analysis/` updated to use library (thin wrappers or CLI)
- [ ] README and API docs updated
- [ ] Unit tests for each submodule

## Implementation Notes

- Refactor existing `trace_graph.py`, `provenance_walker.py`, `causal_attribution.py` into library code; examples become thin CLI wrappers.
- Records source abstraction: support `Path`, `SharedDataAdapter.listen()`, or pre-loaded `{kind: [records]}` dict.
- Preserve topology_comparison as example script (orchestrates runs + calls library); may add `compare_topologies()` helper later.
- Keep networkx, matplotlib as optional dependencies (analysis module imports them only when needed, or document in extras).

## Related

- **Requirements (WHAT the analysis module delivers):** REQ-0006 (interpretability), REQ-0007 (traceability), REQ-0008 (provenance), REQ-0009 (accountability). The analysis module is the user-facing way to obtain these properties from recorded runs.
- **CIPs (HOW):** 0006, 0007, 0008, 0009
- Depends on: 2026-01-28_analysis-suite-demo (completed)
- Documentation: examples/analysis/README.md, README.md

## Progress Updates

### 2026-03-04
Task created. Analysis demo scripts validated the approach; this task promotes them into the library with property-based organisation.
