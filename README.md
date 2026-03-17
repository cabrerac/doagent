# DOAgent

Data-Oriented Agents for accountable and interpretable multi-agent systems.

DOAgent is a Python library for building multi-agent systems where **shared data is the primary interface** between **decentralised agents** that cooperate in **open environments**. Every decision, state transition, and contribution is recorded transparently, providing interpretability, traceability, and accountability out of the box [1].

**In this document:** [Why DOAgent?](#why-doagent) · [Install](#install) · [Run the demos](#run-the-demos) · [Quick start](#quick-start) · [What gets recorded](#what-gets-recorded) · [Decentralisation](#decentralisation-topologies) · [Openness](#open-and-collaborative-environments) · [Analysis](#analysis) · [Implement your own scenario](#implement-your-own-scenario) · [Project layout](#project-layout) · [API reference](#api-reference)

## Why DOAgent?

Agentic systems often lack visibility into *why* decisions were made, *who* contributed what, and *how* state evolved. DOAgent addresses this by making data the first-class citizen:

- **Shared data model**: agents communicate through records, not hidden channels
- **Automatic recording**: wrap your environment and agents once, get full decision and state logs for free
- **Configurable decentralisation**: centralised, peer-to-peer, or federated topology
- **Open environments**: agents can dynamically join or leave, sharing resources and contributing to a live, evolving system
- **Built-in analysis**: trace graphs, provenance chains, and causal attribution from recorded data

## Install

Install the library from the repository so you can `import doagent` from your own project:

```bash
pip install git+https://github.com/cabrerac/doagent.git
```

From a local clone (e.g. for development):

```bash
pip install -e /path/to/doagent
```

Dependencies include `pyyaml`, `matplotlib`, `networkx`, and `pymongo`. For MongoDB storage, a MongoDB server must be running (default URI `mongodb://localhost:27017`).

## Run the demos

The demos show how to use DOAgent as a library. They are not installed with the package as they live in the repository.

- **Grid-world:** Four agents explore a grid; shared data stores discovered cells. Configurable via `examples/gridworld_demo/gridworld_demo_config.yaml`. To use MongoDB, set `storage: "mongo"` in the scenario section (MongoDB must be running).
- **Push:** Two agents in a PettingZoo MPE scenario. Requires `pettingzoo[mpe]`, `mpe2`, `pygame`.

Both demos use a session with file (or mongo) as the shared data model and then run analysis, writing outputs under `output/<run_id>/analysis/`.

### Colab notebooks (step-by-step, self-contained)

The **notebooks** in `notebooks/` are designed to run in Google Colab. Each notebook uses only the `doagent` library and code defined in the notebook—no repo clone required. Open in Colab and run cells in order. (To open a link in a new tab: right-click the badge → **Open link in new tab**.)

| Notebook | Open in Colab | Description |
|----------|---------------|-------------|
| 01_minimal_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/01_minimal_demo.ipynb) | Install → session → stub env → one step → inspect. |
| 02_push_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/02_push_demo.ipynb) | Install + PettingZoo → session with file as shared data model → push run → analysis. |
| 03_gridworld_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/03_gridworld_demo.ipynb) | Install → minimal grid env → session with file as shared data model → run with shared map → full analysis. |

See `notebooks/README.md` for details.

### Running demos locally

To run them, clone the repo, install the library, then run from the **repository root** so the demo scripts are on the path.

```bash
git clone https://github.com/cabrerac/doagent.git
cd doagent
pip install -e .
# Grid-world demo (no extra deps):
python -m examples.gridworld_demo.gridworld_demo
# Push demo (needs PettingZoo):
pip install pettingzoo[mpe] mpe2 pygame
python -m examples.push_demo.push_demo
```

## Using DOAgent in your own project

Install the library (`pip install git+https://github.com/cabrerac/doagent.git` or `pip install -e /path/to/doagent`). In your code: `from doagent import Session, make_env, RunReporter` and `from doagent.analysis import provenance, traceability, ...`. Implement your own environment and config.

## Quick start

The Session API is the primary entry point. You provide a config (environment, policies, where to store records); DOAgent handles all recording transparently.

```python
from doagent import Session, RunConfig, make_env

# 1. Build config: shared_data type, run_config, topology, policies
config = {
    "shared_data": {"type": "memory"},
    "run_config": {"logging_level": 2},
    "topology": {"mode": "centralised"},
    "policies": {"explore": my_policy_callable},
    # optional: "state_hash_fn": my_hash_fn
}

# 2. Create session; use your own environment or make_env(entry_point, **params)
session = Session.from_config(config)
env = session.wrap_env(my_env)  # or session.wrap_env(make_env("my_module:create_env", size=10))

# 3. Create agents (agent_configs: list of dicts with "id", "policy", "metadata")
agents = session.create_agents(agent_configs, goal="explore")

# 4. Run your loop — recording happens automatically
observations = env.reset(seed=42)
for round_id in range(1, rounds + 1):
    actions = {}
    for agent_id, agent in agents.items():
        result = agent.decide(observations[agent_id], round_id)
        actions[agent_id] = result["action"]
    step = env.step(actions)
    observations = step["observations"]
```

After the loop, use `session.inspect("agent_update")`, `session.inspect("trace")`, etc., or read from the configured store (e.g. file directory) to analyse decisions and state transitions.

## What gets recorded

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

## Decentralisation topologies

Control which agents see which records by setting `topology` in your config:

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

## Open and collaborative environments

In DOA, **openness** means the environment is not closed to a fixed set of agents: who participates can change over time, and the system records contributions from whoever acts, without assuming a fixed number of participants.

Agents can effectively “join” or “leave” from the environment’s point of view (e.g. when energy runs out or a condition is met), and DOAgent still attributes and traces only the contributions that actually occurred. Enable a **participation registry** with `participation: True` in config; then `session.participation_registry` supports `register(record)` and `deregister(agent_id)` so the library knows who is participating. The gridworld demo uses this with an optional energy model: agents leave when energy is depleted and rejoin when recharged; the run loop updates the registry on each leave/rejoin and only active agents decide and are included in the step. See the gridworld notebook and `examples/gridworld_demo` for the pattern.

## Analysis

After a **file-backed** or **mongo-backed** run, the library ensures `output_base/<run_id>/metadata.json` exists (for file: also `records/`; for mongo: records live in MongoDB, metadata holds `mongo_uri` and `mongo_database`). Use the `doagent.analysis` package to inspect that run by `run_id` — no access to agent internals needed. Analysis resolves the run from metadata (file adapter or Mongo adapter) and, with `write_output=True`, writes into `output_base/<run_id>/analysis/<category>/` (e.g. PNG and PDF for plots, JSON for interpretability).

**Use the analyses that fit your scenario.** Not every tool is relevant for every run:


| Tool                                    | When to use                                                                                                                                                        |
| --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Provenance**                          | Any run — "why did this state happen?" (chain of records leading to an outcome).                                                                                   |
| **Traceability**                        | Any run — "how did state evolve?" (graph of transitions).                                                                                                          |
| **Accountability** (causal attribution) | Scenarios with a clear notion of *contribution* or *discovery* (e.g. gridworld: who discovered which cells). Skip for scenarios that don't model that (e.g. push). |
| **Interpretability**                    | When you need decision or explanation records linked to outcomes.                                                                                                  |


```python
from doagent.analysis import provenance, traceability, accountability, interpretability

run_id = session.run_id  # after a file-backed run
output_base = "output"

# Write to output_base/run_id/analysis/<category>/ (PNG, PDF, JSON)
effective_id = provenance.render_chain_tree("last", run_id, output_base=output_base, write_output=True)
traceability.build_trace_graph(run_id, output_base=output_base, write_output=True)
# When your scenario has discovery/contribution (e.g. gridworld):
accountability.causal_attribution(run_id, output_base=output_base, write_output=True)
# Use same outcome id as provenance for explanations
interpretability.get_explanations_for(effective_id or "last", run_id, output_base=output_base, write_output=True)
```

The **demos** (see **Run the demos** above) use this pattern: gridworld_demo runs all four (it has discovery); push_demo runs provenance, traceability, and interpretability only (no attribution). For **comparisons** (e.g. baseline vs file, or multiple topologies), use the scripts under `experiments/` (see `examples/README.md`).

## Implement your own scenario

1. **Environment** — Provide a callable that returns an env-like object: `reset(seed)` → observations dict (per agent), `step(actions)` → next observations, rewards, dones. Or use `make_env(your_create_fn, **params)`.
2. **Config** — Build a dict with `shared_data` (e.g. `{"type": "file"}` or `{"type": "mongo", "uri": "mongodb://localhost:27017"}`; with `scenario_name` and `output_base` the library creates run_id and metadata), `run_config` (e.g. `logging_level: 2`), `topology`, and `policies` (name → callable).
3. **Session** — `session = Session.from_config(config)`. For file-backed runs with `scenario_name`, the library creates `output_base/<run_id>/`, `records/`, and `metadata.json`; use `session.run_id` and `session.run_path` after creation.
4. **Run loop** — `env = session.wrap_env(your_env, env_actor="your_env")`, `agents = session.create_agents(agent_configs, goal="…")`. Each round: get observations, call `agent.decide(obs, round_id, inputs={...})` for each agent, then `env.step(actions)`. Use `session.visible_records(agent_id, kind="agent_update")` if agents need shared context.
5. **Analysis** — For file-backed runs, use `doagent.analysis` with `run_id=session.run_id` and `output_base`; call each module with `write_output=True` to write into `output_base/<run_id>/analysis/<category>/`. See **Run the demos** and **Analysis** above, and `examples/README.md` for config options (topologies, storage, logging level).

Keep scenario logic and policies in your code; use only the public API (`Session`, `RunConfig`, `make_env`, `RunReporter`, `doagent.analysis`). See `examples/gridworld_demo` and `examples/push_demo` for full patterns.

## Project layout

```
doagent/             Library implementation
  core/              Session API, adapters, topology, record writing
  analysis/          run_id-based analysis (provenance, traceability, accountability, interpretability)
  records/           Record types (SimpleRecord, provenance, accountability)
  interface/         Abstract adapter contracts
experiments/         Comparison runners (baseline vs file, topology comparison), reporters, baselines
examples/
  gridworld_demo/    File-backed gridworld run + analysis showcase
  push_demo/         File-backed push scenario (PettingZoo) + analysis showcase
  minimal_usage.py   Minimal Session API example
  README.md         Config options and how to run examples vs experiments
tests/               Test suite
```

## API reference

**Primary API** — what user code should import (tests, demos, and experiments use only this surface):


| Import                | Purpose                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------ |
| `doagent.Session`     | Create session via `Session.from_config(config)`; wrap env, create agents, inspect records |
| `doagent.RunConfig`   | Logging level configuration (0, 1, or 2); can be part of config dict                       |
| `doagent.make_env`    | Build an environment from config (when using config-driven env)                            |
| `doagent.RunReporter` | Optional helper for run progress and final summary (e.g. in demos)                         |


Adapter, topology, and policies are configured via the config dict passed to `Session.from_config` (e.g. `shared_data.type`: `"memory"` | `"file"` | `"mongo"` | `"noop"`; `topology.mode`; `policies`). Do not import `doagent.core` or `doagent.records` in user-facing code.

**Demos** — end-to-end examples: see **Run the demos** above for commands (`minimal_usage`, `gridworld_demo`, `push_demo`).

## Project management

DOAgent uses [VibeSafe](https://github.com/lawrennd/vibesafe) for project management:

- `tenets/` — guiding principles
- `requirements/` — what the system must do
- `cip/` — code improvement plans (how to implement requirements)
- `backlog/` — task tracking

Run `./whats-next` to see current project status.

## References

[1] Christian Cabrera, Andrei Paleyes, Pierre Thodoroff, and Neil D. Lawrence. 2025. Machine Learning Systems: A Survey from a Data-Oriented Perspective. ACM Computing Surveys. [Available online](https://dl.acm.org/doi/10.1145/3769292)
