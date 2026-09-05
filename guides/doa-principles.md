# DOA principles in DOAgent

Three pillars: **data first**, **decentralisation**, **openness**. Each section has a short idea and a minimal code snippet.

---

## 1. Data as a first-class citizen

Agents coordinate through **records** in one shared data model (not hidden channels). You choose how much is logged; the library writes outcomes, traces, and optional provenance/accountability.

**Logging level** (in `run_config`):

| Level | What is recorded |
| ----- | ---------------- |
| 0 | `agent_update`, `outcome` |
| 1 | + `trace`, `explanation` |
| 2 | + `provenance`, `accountability` |

**Snippet — config and storage type**

```python
config = {
    "shared_data": {"type": "file"},
    "scenario_name": "my_run",
    "output_base": "output",
    "run_config": {"logging_level": 2},
    "topology": {"mode": "centralised"},
    "policies": {"my_policy": policy_factory},
}
session = Session.from_config(config)
# session.run_id → folder output/<run_id>/ with records/ + metadata.json
```

`shared_data.type`: `"memory"` (single process), `"file"` (JSONL per kind), `"mongo"` (needs server), `"noop"` (no persist).

---

## 2. Decentralisation

Agents are autonomous and communicate with others based on their topology, which controls who sees which records: everyone sees everything (centralised), or each agent sees only listed peers (peer-to-peer), or a hub aggregates (federated).

In peer-to-peer, `visibility` in config is the graph for agents **named there**. Join/leave
update it. An agent **not** in that file is linked both ways to everyone currently in.
Pass `topology.on_membership_change` to use a different rule.

**Snippet — centralised vs peer-to-peer**

```python
# All agents see all agent_update records
config = {
    "shared_data": {"type": "memory"},
    "run_config": {"logging_level": 1},
    "topology": {"mode": "centralised"},
    "policies": {...},
}

# agent_0 only sees records from agent_1 and agent_2
config = {
    "shared_data": {"type": "memory"},
    "topology": {
        "mode": "peer_to_peer",
        "visibility": {
            "agent_0": ["agent_1", "agent_2"],
            "agent_1": ["agent_0"],
        },
    },
    "policies": {...},
}
session = Session.from_config(config)

# In the loop: only records this agent may see
records = session.visible_records("agent_0", kind="agent_update")
# Or shape them for decide (kinds, last N, optional summarise function):
context = session.decision_context("agent_0", kinds="agent_update", last_n=10)
```

YAML examples for gridworld: [`examples/README.md`](../examples/README.md).

---

## 3. Openness

Agents can **join and leave**. Join/leave are records in the shared store. Who an agent can *see* as present uses the
**same topology filter** as other records (`visible_participants`). In federated mode the hub writes extra records
so leaves can see membership. Default: a roster snapshot. Replace with `topology.on_hub_membership` (for example
`relay_join_leave_as_hub`). In peer-to-peer the default membership hook updates who can see whom.

**Snippet — enable registry and register/deregister**

```python
config = {
    "shared_data": {"type": "file"},
    "scenario_name": "gridworld",
    "output_base": "output",
    "run_config": {"logging_level": 2},
    "topology": {"mode": "peer_to_peer", "visibility": {...}},
    "policies": {...},
    "participation": True,  # session gets an in-memory registry
}
session = Session.from_config(config)

session.register_participant("agent_0", capabilities=["map"])
who = session.visible_participants("agent_0")  # topology-filtered current members
# ... agent leaves ...
session.deregister_participant("agent_0")
# ... agent rejoins ...
session.register_participant("agent_0", capabilities=["map"])
```

Working example: `examples/gridworld_demo` (energy model + registry), gridworld Colab notebook.
