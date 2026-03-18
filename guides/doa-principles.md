# DOA principles: shared data, decentralisation, openness

These are the three pillars of the Data-Oriented Agents (DOA) perspective as embodied in DOAgent.

## Shared data as a first-class citizen

Agents coordinate through **records** in a shared store—not through hidden side channels. Every decision and state transition can be logged at a chosen verbosity. That is what makes traceability, provenance, and accountability possible without instrumenting each agent by hand.

DOAgent records three kinds of data at configurable verbosity:

| Logging level | Records                           | Use case                                               |
| ------------- | --------------------------------- | ------------------------------------------------------ |
| **0**         | `agent_update` + `outcome`        | Lightweight: just decisions and states                 |
| **1**         | + `trace` + `explanation`         | Linked state transitions with decision rationale       |
| **2**         | + `provenance` + `accountability` | Full attribution: who created what, from which sources |

Records are stored via the adapter selected in config (`shared_data.type`):

- `"memory"` — in-memory, single-run, good for tests and experiments
- `"file"` — persists to a directory (JSONL per record kind)
- `"mongo"` — persists to MongoDB (one collection per record kind); default URI `mongodb://localhost:27017`. With `scenario_name`, the library creates `output_base/<run_id>/` and `metadata.json` so run_id-based analysis works. Requires `pymongo` and a running MongoDB server.
- `"noop"` — no persistence (e.g. for dry runs)

## Decentralisation

Not every agent needs to see every record. **Topology** controls visibility: centralised (all see all), peer-to-peer (each agent sees only listed peers), or federated (hub aggregates and redistributes).

```python
config = {
    "shared_data": {"type": "memory"},
    "run_config": {"logging_level": 1},
    "topology": {"mode": "centralised"},  # all agents see all records
}
# Or: "topology": {"mode": "peer_to_peer", "visibility": {"agent_0": ["agent_1"], ...}}
# Or: "topology": {"mode": "federated", "hub_id": "hub"}
session = Session.from_config(config)
```

Within the run loop, `session.visible_records(agent_id, kind="agent_update")` returns only the records that agent is allowed to see.

YAML examples: [`examples/README.md`](../examples/README.md) (topology section).

## Openness

The participant set is not fixed: agents can join or leave over time, and the system still attributes only the contributions that actually occurred.

Enable a **participation registry** with `participation: True` in config (or pass a `participation_registry` instance). Then `session.participation_registry` supports `register(record)` and `deregister(agent_id)` so the library knows who is currently participating.

The gridworld demo uses this with an optional energy model: agents leave when energy is depleted and rejoin when recharged; the run loop updates the registry on each leave/rejoin. See the gridworld notebook and `examples/gridworld_demo`.

Next: [Analysis](analysis.md)
