# DOAgent

Data-Oriented Agents for accountable multi-agent systems.

DOAgent is a Python library for building multi-agent systems where **shared data is the primary interface** between agents. Every decision, state transition, and contribution is recorded transparently — giving you interpretability, traceability, and accountability out of the box [1].

## Why DOAgent?

Agentic systems often lack visibility into *why* decisions were made, *who* contributed what, and *how* state evolved. DOAgent addresses this by making data the first-class citizen:

- **Shared data model** — agents communicate through records, not hidden channels
- **Automatic recording** — wrap your environment and agents once, get full decision and state logs for free
- **Configurable coordination** — centralised, peer-to-peer, or federated topology
- **Built-in analysis** — trace graphs, provenance chains, and causal attribution from recorded data

## Install

```bash
pip install -r requirements.txt
```

Core dependencies: `pyyaml`. For analysis: `matplotlib`, `networkx`. For the PettingZoo validation scenario: `pettingzoo[mpe]`, `mpe2`, `pygame`.

## Quick start

The Session API is the primary entry point. You provide the environment and the policies; DOAgent handles all recording transparently.

```python
from doagent import Session, RunConfig
from doagent.core import InMemorySharedData, FileSharedData

# 1. Choose where records go
shared_data = InMemorySharedData()          # or FileSharedData("output/records")

# 2. Create a session (logging level 2 = full provenance and accountability)
session = Session(shared_data, RunConfig(logging_level=2))

# 3. Wrap your environment
env = session.wrap_env(my_env, env_actor="my_env")

# 4. Create agents from policies
agents = session.create_agents(configs, registry, goal="explore")

# 5. Run your loop — recording happens automatically
observations = env.reset(seed=42)
for round_id in range(1, rounds + 1):
    actions = {}
    for agent_id, agent in agents.items():
        result = agent.decide(observations[agent_id], round_id)
        actions[agent_id] = result["action"]
    step = env.step(actions)
    observations = step["observations"]
```

After the loop, `shared_data` contains all records: agent decisions, environment outcomes, and trace links connecting them.

## What gets recorded

DOAgent records three kinds of data at configurable verbosity:

| Logging level | Records | Use case |
|:---:|---|---|
| **0** | `agent_update` + `outcome` | Lightweight: just decisions and states |
| **1** | + `trace` + `explanation` | Linked state transitions with decision rationale |
| **2** | + `provenance` + `accountability` | Full attribution: who created what, from which sources |

Records are stored as JSONL (one file per kind) via adapters:

- `InMemorySharedData` — fast, no I/O, good for experiments
- `FileSharedData(path)` — persists to disk as `trace.jsonl`, `outcome.jsonl`, `agent_update.jsonl`
- `MongoSharedData(collection)` — MongoDB-backed (requires `pymongo`)

## Coordination topologies

Control which agents see which records:

```python
from doagent.core import Topology, TopologyConfig

# All agents see all records
session = Session(shared_data, topology=TopologyConfig(mode=Topology.CENTRALISED))

# Each agent sees only its own records and designated peers
session = Session(shared_data,
    topology=TopologyConfig(mode=Topology.PEER_TO_PEER),
    visibility={"agent_0": ["agent_1"], "agent_1": ["agent_2"]},
)

# Agents see only hub-authored records; hub sees everything
session = Session(shared_data,
    topology=TopologyConfig(mode=Topology.FEDERATED),
    hub_id="hub",
)
```

Within the run loop, `session.visible_records(agent_id, kind="agent_update")` returns only the records that agent is allowed to see.

## Analysis tools

After a run, use the analysis scripts to visualise and understand what happened. All analysis is derived from the recorded data — no access to agent internals needed.

```bash
# Trace graph: state transitions coloured by agent
python examples/analysis/trace_graph.py output/my_run/records

# Provenance walker: "why did this state happen?"
python examples/analysis/provenance_walker.py output/my_run/records last --depth 4

# Causal attribution: who discovered what, and how effectively
python examples/analysis/causal_attribution.py output/my_run/records

# Topology comparison: same agents, 3 coordination modes, side-by-side
python examples/analysis/topology_comparison.py --run
```

Each script produces PNG/PDF charts and console summaries. See `examples/analysis/README.md` for details.

## Run the demos

### Grid-world mapping (dependency-free)

Four agents explore a grid with partial observations, sharing discovered cells via the shared data model. No external dependencies beyond the library.

```bash
python -m examples.gridworld_demo.gridworld_demo
```

Configurable via YAML. Edit `examples/gridworld_demo/gridworld_demo_config.yaml` to change grid size, topology, agent policies, energy model, and more.

### Simple push (PettingZoo)

A multi-agent push scenario using PettingZoo's MPE environments.

```bash
pip install pettingzoo[mpe] mpe2 pygame
python -m examples.push_demo.push_demo
```

Both demos produce output directories with JSONL records, summary JSON, and metrics ready for the analysis tools above.

## Run the tests

```bash
python -m unittest -v
```

## Project layout

```
doagent/             Library implementation
  core/              Session API, adapters, topology, record writing
  records/          Record types (SimpleRecord, provenance, accountability)
  interface/         Abstract adapter contracts
experiments/         Runners, reporters, baselines (research use, not public API)
examples/
  analysis/          Trace graph, provenance walker, causal attribution
  push_demo/         End-to-end push scenario (PettingZoo)
  gridworld_demo/    End-to-end gridworld scenario
  minimal_usage.py   Minimal Session API example
tests/               Test suite
```

## API reference

**Primary API** — what user code should import:

| Import | Purpose |
|---|---|
| `doagent.Session` | Central entry point: wrap env, create agents, run |
| `doagent.RunConfig` | Logging level configuration (0, 1, or 2) |
| `doagent.InMemorySharedData` | In-memory shared data adapter |
| `doagent.core.FileSharedData` | File-backed adapter (JSONL per record kind) |
| `doagent.core.MongoSharedData` | MongoDB adapter (optional) |
| `doagent.core.TopologyConfig` | Coordination topology configuration |
| `doagent.core.Topology` | Topology modes: CENTRALISED, PEER_TO_PEER, FEDERATED |
| `doagent.core.PolicyRegistry` | Register and create agent policies (e.g. for Session.from_config) |
| `doagent.records.SimpleRecord` | The record envelope type |

**Demos** — end-to-end examples:

```bash
python -m examples.minimal_usage              # Minimal Session.from_config run
python -m examples.gridworld_demo.gridworld_demo   # Grid-world mapping
python -m examples.push_demo.push_demo             # Push (PettingZoo)
```
```

## Project management

DOAgent uses [VibeSafe](https://github.com/lawrennd/vibesafe) for project management:

- `tenets/` — guiding principles
- `requirements/` — what the system must do
- `cip/` — code improvement plans (how to implement requirements)
- `backlog/` — task tracking

Run `./whats-next` to see current project status.

## References

[1] Christian Cabrera, Andrei Paleyes, Pierre Thodoroff, and Neil D. Lawrence. 2025. Machine Learning Systems: A Survey from a Data-Oriented Perspective. ACM Computing Surveys. [Available online](https://dl.acm.org/doi/10.1145/3769292)
