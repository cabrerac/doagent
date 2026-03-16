# Examples

Minimal, file-backed runs that demonstrate the library: config, run loop, and analysis.

Run from the **repository root** so the `doagent` package is on the path:

```bash
python -m examples.gridworld_demo.gridworld_demo [config.yaml]
python -m examples.push_demo.push_demo
python -m examples.minimal_usage
```

Each demo uses the **public API** only: `Session`, `RunConfig`, `make_env`, `RunReporter`, and `doagent.analysis`.

## What each example does


| Example            | Description                                                                                                                                                                                                                |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **gridworld_demo** | Four agents explore a grid; shared data stores discovered cells. File-backed run, then analysis: provenance, traceability, **causal attribution** (fits discovery), interpretability.                                      |
| **push_demo**      | Two agents in a PettingZoo MPE push scenario. File-backed run, then analysis: provenance, traceability, interpretability (no attribution — push has no discovery semantics). Requires `pettingzoo[mpe]`, `mpe2`, `pygame`. |
| **minimal_usage**  | Smallest Session-based run (memory-backed) for quick sanity checks.                                                                                                                                                        |


After a file-backed run, output lives under `output/<run_id>/`: `records/`, `metadata.json`, and `analysis/<category>/` for artefacts. The demos call analysis with `write_output=True`, so the library writes PNG, PDF, and JSON into each category folder. **Use only the analysis tools that fit your scenario** (see main README “Analysis” and `doagent.analysis` package docstring).

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
- **Federated** — a hub aggregates and redistributes; set `hub_id` in session config. In the run loop, the hub typically calls `session.visible_records(hub_id, kind="agent_update")`, aggregates (e.g. via `build_shared_map`), then `session.record_update(hub_id, summary, payload_type="...")`.
  ```yaml
  topology:
    mode: "federated"
    hub_id: "hub"
  ```

Gridworld demo reads topology from `scenario.topology` in its YAML; see `gridworld_demo_config.yaml`.

### Storage

- **File-backed (for demos and analysis)** — use `shared_data.type: "file"` and set `scenario_name` and `output_base`. The library creates `output_base/<run_id>/`, `records/`, and `metadata.json`.
- **Mongo-backed** — use `shared_data.type: "mongo"` and set `scenario_name` and `output_base`; optionally `shared_data.uri` (default `mongodb://localhost:27017`). The library creates `output_base/<run_id>/` and `metadata.json` (with `mongo_uri` and `mongo_database`); records are stored in MongoDB. Run_id-based analysis resolves from metadata and reads from Mongo. Requires `pymongo`.
- **In-memory** — `shared_data.type: "memory"` for single-run experiments; no posterior analysis by `run_id` after the session ends.
- **NoOp** — `shared_data.type: "noop"` for baseline/dry runs (no persistence).

### Logging level

In `run_config`, set `logging_level` to 0, 1, or 2 to control how much is recorded (e.g. agent_update, outcome, trace, provenance). Level 2 enables full attribution for analysis.