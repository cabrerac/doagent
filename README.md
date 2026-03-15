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

# 3. Create agents (policies come from config)
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

| Logging level | Records | Use case |
|:---:|---|---|
| **0** | `agent_update` + `outcome` | Lightweight: just decisions and states |
| **1** | + `trace` + `explanation` | Linked state transitions with decision rationale |
| **2** | + `provenance` + `accountability` | Full attribution: who created what, from which sources |

Records are stored via the adapter selected in config (`shared_data.type`):

- `"memory"` — in-memory, single-run, good for tests and experiments
- `"file"` — persists to a directory (JSONL per record kind)
- `"noop"` — no persistence (e.g. for dry runs)

## Coordination topologies

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

## Analysis

After a **file-backed** run, the library writes `output/<run_id>/` (with `records/` and `metadata.json`). Use the `doagent.analysis` package to inspect that run by `run_id` — no access to agent internals needed.

**Use the analyses that fit your scenario.** Not every tool is relevant for every run:

| Tool | When to use |
|------|--------------|
| **Provenance** | Any run — "why did this state happen?" (chain of records leading to an outcome). |
| **Traceability** | Any run — "how did state evolve?" (graph of transitions). |
| **Accountability** (causal attribution) | Scenarios with a clear notion of *contribution* or *discovery* (e.g. gridworld: who discovered which cells). Skip for scenarios that don't model that (e.g. push). |
| **Interpretability** | When you need decision or explanation records linked to outcomes. |

```python
from doagent.analysis import provenance, traceability, accountability, interpretability

run_id = "gridworld_run_20260315_120000_abc12345"  # or session.run_id after a run
output_base = "output"

# Generic: any run
chain = provenance.walk_chain("last", run_id, output_base=output_base)
provenance.render_chain_tree("last", run_id, "provenance_tree.png", output_base=output_base)
G = traceability.build_trace_graph(run_id, output_base=output_base)
traceability.render_trace_graph(G, "trace_graph.png")

# When your scenario has discovery/contribution (e.g. gridworld)
attr = accountability.causal_attribution(run_id, output_base=output_base)
accountability.render_attribution_charts(attr, "attribution/")

# When you have explanation records
explanations = interpretability.get_explanations_for(record_id, run_id, output_base=output_base)
```

The **demos** show the pattern: gridworld_demo runs all four (it has discovery); push_demo runs provenance, traceability, and interpretability only (no attribution). For **comparisons** (e.g. baseline vs file, or multiple topologies), use the scripts under `experiments/` (see `examples/README.md`).

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

Both demos run a single file-backed scenario and then run analysis (provenance, traceability, accountability, interpretability), writing charts and summaries into the run output folder.

## Implement your own scenario

1. **Environment** — Provide a callable that returns an env-like object: `reset(seed)` → observations dict (per agent), `step(actions)` → next observations, rewards, dones. Or use `make_env(your_create_fn, **params)`.
2. **Config** — Build a dict with `shared_data` (e.g. `{"type": "file"}` plus `scenario_name` and `output_base` for file runs), `run_config` (e.g. `logging_level: 2`), `topology`, and `policies` (name → callable).
3. **Session** — `session = Session.from_config(config)`. For file-backed runs with `scenario_name`, the library creates `output_base/<run_id>/`, `records/`, and `metadata.json`; use `session.run_id` and `session.run_path` after creation.
4. **Run loop** — `env = session.wrap_env(your_env, env_actor="your_env")`, `agents = session.create_agents(agent_configs, goal="…")`. Each round: get observations, call `agent.decide(obs, round_id, inputs={...})` for each agent, then `env.step(actions)`. Use `session.visible_records(agent_id, kind="agent_update")` if agents need shared context.
5. **Analysis** — For file-backed runs, use `doagent.analysis` with `run_id=session.run_id` and `output_base` to run provenance, traceability, accountability, and interpretability on the recorded data.

Keep scenario logic and policies in your code; use only the public API (`Session`, `RunConfig`, `make_env`, `RunReporter`, `doagent.analysis`). See `examples/gridworld_demo` and `examples/push_demo` for full patterns, and `examples/README.md` for config options (topologies, storage, logging level).

## Run the tests

```bash
python -m unittest -v
```

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

| Import | Purpose |
|---|---|
| `doagent.Session` | Create session via `Session.from_config(config)`; wrap env, create agents, inspect records |
| `doagent.RunConfig` | Logging level configuration (0, 1, or 2); can be part of config dict |
| `doagent.make_env` | Build an environment from config (when using config-driven env) |
| `doagent.RunReporter` | Optional helper for run progress and final summary (e.g. in demos) |

Adapter, topology, and policies are configured via the config dict passed to `Session.from_config` (e.g. `shared_data.type`: `"memory"` | `"file"` | `"noop"`; `topology.mode`; `policies`). Do not import `doagent.core` or `doagent.records` in user-facing code.

**Demos** — end-to-end examples:

```bash
python -m examples.minimal_usage              # Minimal Session.from_config run
python -m examples.gridworld_demo.gridworld_demo   # Grid-world mapping
python -m examples.push_demo.push_demo             # Push (PettingZoo)
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
