# Getting started: install, demos, quick start

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

For library-only use in another project: `from doagent import Session, make_env, RunReporter` and `from doagent.analysis import provenance, traceability, …`.

## Run the demos

The demos show how to use DOAgent as a library. They are not installed with the package; they live in the repository.

- **Grid-world:** Four agents explore a grid; shared data stores discovered cells. Configurable via `examples/gridworld_demo/gridworld_demo_config.yaml`. To use MongoDB, set `storage: "mongo"` in the scenario section (MongoDB must be running).
- **Push:** Two agents in a PettingZoo MPE scenario. Requires `pettingzoo[mpe]`, `mpe2`, `pygame`.

Both demos use a session with file (or mongo) as the shared data model and then run analysis, writing outputs under `output/<run_id>/analysis/`.

### Colab notebooks (step-by-step, self-contained)

The **notebooks** in `notebooks/` are designed to run in Google Colab. Each notebook uses only the `doagent` library and code defined in the notebook—no repo clone required. (To open a link in a new tab: right-click the badge → **Open link in new tab**.)

| Notebook | Open in Colab | Description |
|----------|---------------|-------------|
| 01_minimal_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/01_minimal_demo.ipynb) | Install → session → stub env → one step → inspect. |
| 02_push_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/02_push_demo.ipynb) | Install + PettingZoo → session with file as shared data model → push run → analysis. |
| 03_gridworld_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/03_gridworld_demo.ipynb) | Install → minimal grid env → session with file as shared data model → run with shared map → full analysis. |

See [`notebooks/README.md`](../notebooks/README.md) for details.

### Running demos locally

Clone the repo, install the library, then run from the **repository root**:

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

Config options (topology, storage, participation): see [`examples/README.md`](../examples/README.md).

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

Next: [Implement your own environment](implement-your-environment.md) · [DOA principles](doa-principles.md) · [Analysis](analysis.md)
