# DOAgent

Data-Oriented Agents for accountable and interpretable multi-agent systems.

DOAgent is a Python library for building multi-agent systems where **shared data is the primary interface** between **decentralised agents** that cooperate in **open environments**. Every decision, state transition, and contribution is recorded transparently, providing interpretability, traceability, and accountability out of the box [1].

**Guides:** [Getting started](guides/getting-started.md) · [Implement your environment](guides/implement-your-environment.md) · [DOA principles](guides/doa-principles.md) · [Analysis](guides/analysis.md) · [API & layout](guides/reference.md) · [Examples config](examples/README.md) · [Notebooks](notebooks/README.md)

## Why DOAgent?

Agentic systems often lack visibility into *why* decisions were made, *who* contributed what, and *how* state evolved. DOAgent addresses this by making data the first-class citizen:

- **Shared data model**: agents communicate through records, not hidden channels
- **Automatic recording**: wrap your environment and agents once, get full decision and state logs for free
- **Configurable decentralisation**: centralised, peer-to-peer, or federated topology
- **Open environments**: agents can dynamically join or leave; participation can be tracked via the session registry
- **Built-in analysis**: trace graphs, provenance chains, and causal attribution from recorded data

## Install

```bash
pip install git+https://github.com/cabrerac/doagent.git
```

Development from a clone: `pip install -e /path/to/doagent`. Dependencies include `pyyaml`, `matplotlib`, `networkx`, `pymongo` (MongoDB optional; default URI `mongodb://localhost:27017`).

**More:** [Install & dependencies](guides/getting-started.md#install)

## Run the demos

Demos live in the repo (not in the pip package). **Grid-world** (`examples/gridworld_demo`) — four agents, shared map, optional participation registry. **Push** (`examples/push_demo`) — PettingZoo MPE; needs `pettingzoo[mpe]`, `mpe2`, `pygame`. **Colab notebooks** in `notebooks/` — step-by-step, no clone required.

**More:** [Demos, Colab table, local commands](guides/getting-started.md#run-the-demos) · [`examples/README.md`](examples/README.md) · [`notebooks/README.md`](notebooks/README.md)

## Quick start

```python
from doagent import Session, RunConfig, make_env

config = {
    "shared_data": {"type": "memory"},
    "run_config": {"logging_level": 2},
    "topology": {"mode": "centralised"},
    "policies": {"explore": my_policy_callable},
}
session = Session.from_config(config)
env = session.wrap_env(my_env)
agents = session.create_agents(agent_configs, goal="explore")

observations = env.reset(seed=42)
for round_id in range(1, rounds + 1):
    actions = {aid: agents[aid].decide(observations[aid], round_id)["action"] for aid in agents}
    step = env.step(actions)
    observations = step["observations"]
```

After the loop: `session.inspect("agent_update")`, `session.inspect("trace")`, etc.

**More:** [Full quick start](guides/getting-started.md#quick-start)

## Implement your own environment

Provide an env with `reset` / `step`, build `Session.from_config` with `shared_data`, `topology`, `policies`, wrap with `session.wrap_env`, create agents, run your loop. Use `session.visible_records` when agents need peer context; use `doagent.analysis` after file-backed runs.

**More:** [Step-by-step checklist](guides/implement-your-environment.md)

## Shared data as a first-class citizen

Recording is automatic once you wrap the env and agents. Logging levels control how much is stored (outcomes only vs trace, provenance, accountability). Storage backends: memory, file, mongo, noop.

**More:** [Logging levels & adapters](guides/doa-principles.md#shared-data-as-a-first-class-citizen)

## Decentralisation

Topology modes restrict which records each agent sees (centralised, peer-to-peer with visibility map, federated with hub).

**More:** [Topology & `visible_records`](guides/doa-principles.md#decentralisation)

## Openness

Who participates can change. Set `participation: True` (or pass a registry) and use `session.participation_registry.register` / `deregister` when agents join or leave. Gridworld demo shows this with an energy model.

**More:** [Participation registry](guides/doa-principles.md#openness)

## Analysis

Run tools: provenance, traceability, accountability, interpretability. Writes under `output/<run_id>/analysis/` when `write_output=True`. The implemented tools are examples of the analysis DOAgent enables.

**More:** [When to use each tool + code](guides/analysis.md)

## API reference

| Import | Purpose |
|--------|---------|
| `doagent.Session` | `Session.from_config`, wrap env, create agents, inspect |
| `doagent.RunConfig` | Logging level (part of config) |
| `doagent.make_env` | Config-driven env factory |
| `doagent.RunReporter` | Optional run progress / summary |

**More:** [Full API table & ParticipationRecord](guides/reference.md#primary-api)

## Project layout

Library under `doagent/`; examples under `examples/`; user guides under `guides/`; architecture notes under `docs/`; experiments under `experiments/`.

**More:** [Directory tree](guides/reference.md#project-layout)

---

## Project management

DOAgent uses [VibeSafe](https://github.com/lawrennd/vibesafe): `tenets/`, `requirements/`, `cip/`, `backlog/`. Run `./whats-next` for status.

## References

[1] Christian Cabrera, Andrei Paleyes, Pierre Thodoroff, and Neil D. Lawrence. 2025. Machine Learning Systems: A Survey from a Data-Oriented Perspective. ACM Computing Surveys. [Available online](https://dl.acm.org/doi/10.1145/3769292)
