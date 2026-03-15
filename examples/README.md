# Examples

Minimal, file-backed runs that demonstrate the library: config, run loop, and analysis.

Run from the **repository root** so the `doagent` package is on the path:

```bash
python -m examples.gridworld_demo.gridworld_demo [config.yaml]
python -m examples.push_demo.push_demo
python -m examples.minimal_usage
```

Each demo uses the **public API** only: `Session`, `RunConfig`, `make_env`, `RunReporter`, and `doagent.analysis`. No imports from `doagent.core` or `doagent.records`.

## What each example does

| Example | Description |
|--------|-------------|
| **gridworld_demo** | Four agents explore a grid; shared data stores discovered cells. File-backed run, then analysis: provenance, traceability, **causal attribution** (fits discovery), interpretability. |
| **push_demo** | Two agents in a PettingZoo MPE push scenario. File-backed run, then analysis: provenance, traceability, interpretability (no attribution — push has no discovery semantics). Requires `pettingzoo[mpe]`, `mpe2`, `pygame`. |
| **minimal_usage** | Smallest Session-based run (memory-backed) for quick sanity checks. |

After a file-backed run, output lives under `output/<run_id>/` with `records/`, `metadata.json`, and any analysis artefacts. **Use only the analysis tools that fit your scenario** (see main README “Analysis” and `doagent.analysis` package docstring).

## Config alternatives

### Topology (who sees which records)

In your config, set `scenario.topology` (or the top-level `topology` key, depending on how the example reads it):

- **Centralised** — every agent sees all records.
  ```yaml
  topology:
    mode: "centralised"
  ```
- **Peer-to-peer** — each agent sees only records from listed peers.
  ```yaml
  topology:
    mode: "peer_to_peer"
    visibility:
      agent_0: ["agent_1", "agent_2"]
      agent_1: ["agent_0"]
      agent_2: ["agent_0"]
  ```
- **Federated** — a hub aggregates and redistributes; use `hub_id` in session config.

Gridworld demo reads topology from `scenario.topology` in its YAML; see `gridworld_demo_config.yaml`.

### Storage

- **File-backed (for demos and analysis)** — use `shared_data.type: "file"` and set `scenario_name` and `output_base`. The library creates `output_base/<run_id>/`, `records/`, and `metadata.json`.
- **In-memory** — `shared_data.type: "memory"` for single-run experiments; no posterior analysis by `run_id` after the session ends.
- **NoOp** — `shared_data.type: "noop"` for baseline/dry runs (no persistence).

### Logging level

In `run_config`, set `logging_level` to 0, 1, or 2 to control how much is recorded (e.g. agent_update, outcome, trace, provenance). Level 2 enables full attribution for analysis.

## Comparison and validation

For **comparisons** (e.g. baseline vs in-memory vs file, or different topologies), use the scripts under `experiments/`:

- `python -m experiments.run_gridworld_comparison [config.yaml]` — baseline, in-memory, and file-backed gridworld; writes a combined summary.
- `python -m experiments.run_push_comparison` — in-memory and file-backed push.
- `python -m experiments.run_topology_comparison [--output-dir output/topo_comparison]` — gridworld under centralised, peer_to_peer, and federated; uses `doagent.analysis` for trace graphs and causal attribution per run.
