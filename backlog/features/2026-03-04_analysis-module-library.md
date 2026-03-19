---
id: "2026-03-04_analysis-module-library"
title: "Implement doagent.analysis module with property-based submodules"
status: "In Progress"
priority: "High"
created: "2026-03-04"
last_updated: "2026-03-19"
category: "features"
related_cips:
- "0006"
- "0007"
- "0008"
- "0009"
owner: "Christian Cabrera"
dependencies:
- "2026-01-28_analysis-suite-demo"
- "2026-03-15_library-writes-run-metadata"
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
- Analysis is keyed by **run_id**; the analysis module resolves run_id via run metadata (see Design decision below) and uses `inspect()`-style access to records.
- Environment-agnostic: works with any DOAgent run output, not just gridworld.
- Extensible: new analyses added as functions in the appropriate property submodule.

## Alternatives Considered

- **Alternative A**: Keep analysis as standalone scripts in examples/ — users copy and modify. Rejected: not reusable, no library API.
- **Alternative B**: Single flat `doagent.analysis` module with all functions. Rejected: harder to discover, no clear grouping.
- **Alternative C**: Property-based submodules (selected). Rationale: aligns with CIPs 0006–0009, intuitive import (`from doagent.analysis import provenance`), clear extensibility.

## Design decision: run_id and resolution

- Analysis is keyed by **run_id** (the same identifier used for the run's output subfolder).
- The **library** writes **run metadata** in that output folder (including storage type and how to find records).
- The **analysis module** resolves run_id by reading that metadata and opening the right access point, then uses `inspect()`-style access to run analyses.
- **Persisted runs** (file, DB, stream): analysis can run after the run has finished.
- **In-memory runs**: no posterior analysis by run_id (data is ephemeral). Analysis only while the run is active, using the live Session. Output folder and metadata may exist, but resolving that run_id later yields "no data available."

## Run conventions (library owns)

The **library** creates run_id, the metadata file, and the folders (including `./output/`). So:
- **Library creates:** `./output/` (output base), `./output/<run_id>/` (run folder), `./output/<run_id>/records/` (for file-backed runs), and `./output/<run_id>/metadata.json`. Library generates run_id when a run is started with persisted storage.
- **Runners** do not create these; they supply scenario_name (and storage type, etc.) and receive run_id from the library. Analysis uses run_id and (by default) output_base `./output/` to resolve runs.

## Run metadata format

The **library** writes a single metadata file per run. The **analysis module** reads it to resolve run_id to an access point.

**Location:** `<output_base>/<run_id>/metadata.json` (filename is `metadata.json` only).

**Records:** Records for file-backed runs live in the `records/` subfolder: `<output_base>/<run_id>/records/` (e.g. `outcome.jsonl`, `trace.jsonl`, `agent_update.jsonl`).

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `run_id` | string | Yes | Same as the run's output subfolder name. |
| `scenario_name` | string | Yes | Name of the scenario (e.g. `"gridworld"`, `"push"`). |
| `storage_type` | string | Yes | `"file"` \| `"mongo"` \| `"memory"` \| `"stream"` (or future types). |
| `records_dir` | string | For file | Relative path to records from run folder; use `"records"` so records live in `<run_id>/records/`. |
| `config_ref` | string | For mongo/stream | Name of a **named file config** that holds secrets (e.g. connection URI). That file is not committed to git (e.g. in `.gitignore`); the metadata only stores the reference name. |
| `created_at` | string | No | ISO 8601 timestamp when the run was created. |
| `metadata_schema_version` | integer | Yes | Version of this metadata JSON structure. Start with `1`; bump when we add or change fields so the analysis module can support multiple formats. |

**Secrets:** For storage types that need connection details (mongo, stream), use a **named file config**: a separate file (e.g. `config/local.yaml` or `~/.doagent_secrets.json`) that is in `.gitignore`. The metadata only stores a reference (e.g. `config_ref: "local"`); the library and analysis resolve that name to the actual file and read credentials from it.

## Acceptance Criteria

### Provenance submodule (`doagent.analysis.provenance`)
- [ ] `walk_chain(record_id, run_id, max_depth, output_base=None)` — resolve run_id via metadata, then walk derived_from chain backwards, return structured chain
- [ ] `render_chain_tree(record_id, run_id, output_path, output_base=None)` — resolve run_id, produce tree diagram (PNG/PDF)
- [ ] Resolution: analysis reads run metadata from output folder (e.g. output_base/run_id), opens the appropriate access point, uses `inspect()` to get records

### Traceability submodule (`doagent.analysis.traceability`)
- [ ] `build_trace_graph(run_id, output_base=None)` — resolve run_id, return networkx MultiDiGraph from trace/outcome/agent_update records
- [ ] `get_traces_to(record_id, run_id, output_base=None)` / `get_traces_from(record_id, run_id, output_base=None)` — retrieval helpers
- [ ] `render_trace_graph(graph, output_path)` — export PNG/PDF/DOT (no run_id; operates on graph)
- [ ] Graph layout handles chain-like and branching structures

### Accountability submodule (`doagent.analysis.accountability`)
- [ ] `causal_attribution(run_id, output_base=None)` — resolve run_id, per-agent contribution from trace edges, return structured dict
- [ ] `render_attribution_charts(attribution, output_path)` — line chart, bar chart, effectiveness chart (no run_id)
- [ ] Attribution logic uses agent-specific observations (not first-agent-wins)

### Interpretability submodule (`doagent.analysis.interpretability`)
- [ ] `build_atomic_explanations(record_id, run_id, output_base=None)` — resolve run_id, build transition-level atomic explanations for a record
- [ ] Minimal initially; extensible for summarisation, aggregation in future

### Module structure
- [ ] `doagent.analysis` package with `__init__.py` re-exporting submodules
- [ ] Examples in `examples/analysis/` updated to use library (thin wrappers or CLI)
- [ ] README and API docs updated
- [ ] Unit tests for each submodule

## Implementation Notes

- Refactor existing `trace_graph.py`, `provenance_walker.py`, `causal_attribution.py` into library code; examples become thin CLI wrappers that call analysis with run_id (and output_base when needed).
- Analysis module owns run_id resolution: read run metadata from output folder (output_base/run_id or agreed convention), then open the right access point (file adapter, DB, etc.) and use `inspect()` to fetch records. Depends on library writing that metadata (separate task/CIP if not yet done).
- Preserve topology_comparison as example script (orchestrates runs + calls library); may add `compare_topologies()` helper later.
- Keep networkx, matplotlib as optional dependencies (analysis module imports them only when needed, or document in extras).

## Related

- **Requirements (WHAT the analysis module delivers):** REQ-0006 (interpretability), REQ-0007 (traceability), REQ-0008 (provenance), REQ-0009 (accountability). The analysis module is the user-facing way to obtain these properties from recorded runs.
- **CIPs (HOW):** 0006, 0007, 0008, 0009
- Depends on: 2026-01-28_analysis-suite-demo (completed), 2026-03-15_library-writes-run-metadata (library writes metadata.json; format defined in this task).
- Documentation: examples/analysis/README.md, README.md

## Progress Updates

### 2026-03-04
Task created. Analysis demo scripts validated the approach; this task promotes them into the library with property-based organisation.

### 2026-03-15
Design decision recorded: analysis keyed by run_id; library writes run metadata; analysis resolves via metadata and uses inspect(). In-memory: no posterior analysis. Backlog aligned: design principles, acceptance criteria (run_id, output_base), and implementation notes updated accordingly.

### 2026-03-15
Status set to In Progress. Proceeding per 5-stage workflow: implementation in small, reviewable slices; explain before acting, no unapproved changes.

### 2026-03-19
Interpretability API updated: replaced linked-record retrieval entry with `build_atomic_explanations(record_id, run_id, output_base=None)` as the user-facing method. Examples/notebooks/docs aligned to atomic explanations artefact output.
