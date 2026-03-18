# DOAgent

Data-Oriented Agents for accountable and interpretable multi-agent systems.

DOAgent is a Python library for building multi-agent systems where **shared data is the primary interface** between **decentralised agents** that cooperate in **open environments**. Every decision, state transition, and contribution can be recorded transparently so you get interpretability, traceability, and accountability without ad-hoc logging [1].

## Why DOAgent?

Agentic systems often lack visibility into *why* decisions were made, *who* contributed what, and *how* state evolved. DOAgent makes **data** the first-class citizen:

- **Shared data model** — agents communicate through records, not hidden channels  
- **Automatic recording** — wrap environment and agents once; full logs at the verbosity you choose  
- **Decentralisation** — centralised, peer-to-peer, or federated visibility of records  
- **Openness** — optional participation registry when agents join or leave  
- **Analysis** — provenance, trace graphs, causal attribution from stored runs  

## Install

Install from GitHub (recommended):

```bash
pip install git+https://github.com/cabrerac/doagent.git
```

From a local clone (development):

```bash
pip install -e /path/to/doagent
```

**Dependencies:** `pyyaml`, `matplotlib`, `networkx`, `pymongo`. Using **MongoDB** as storage requires a running server (default URI `mongodb://localhost:27017`).

In your project:

```python
from doagent import Session, make_env, RunReporter
from doagent.analysis import provenance, traceability, accountability, interpretability
```

## Run the demos

Demos are **in the repository**, not inside the pip package. They use file (or mongo) as the shared data model, then write analysis under `output/<run_id>/analysis/`.

- **Grid-world** — Four agents, shared map, optional participation. Config: `examples/gridworld_demo/gridworld_demo_config.yaml`. Mongo: set `storage: "mongo"` under `scenario` (server must be running).  
  Local: `python -m examples.gridworld_demo.gridworld_demo`
- **Push** — Two agents, PettingZoo MPE. Extra deps: `pip install pettingzoo[mpe] mpe2 pygame`.  
  Local: `python -m examples.push_demo.push_demo`

### Notebooks (Google Colab)

No clone needed: install cell pulls `doagent`, rest is self-contained. Open in Colab, run top to bottom. (New tab: right-click badge → **Open link in new tab**.)

| Notebook | Colab | What it does |
|----------|-------|--------------|
| 01_minimal_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/01_minimal_demo.ipynb) | Session + in-memory store, stub env, one step, inspect |
| 02_push_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/02_push_demo.ipynb) | File store, PettingZoo push, analysis |
| 03_gridworld_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/03_gridworld_demo.ipynb) | File store, grid + topology + participation, full analysis |

### Run demos locally (clone)

```bash
git clone https://github.com/cabrerac/doagent.git
cd doagent
pip install -e .
python -m examples.gridworld_demo.gridworld_demo
pip install pettingzoo[mpe] mpe2 pygame   # only for push
python -m examples.push_demo.push_demo
```

Extra options (topology, mongo, participation): [`examples/README.md`](examples/README.md). Notebook notes: [`notebooks/README.md`](notebooks/README.md).

**Next:** [Quick start code + checklist for your own environment →](guides/demos-and-custom-builds.md)

## DOA principles

DOAgent follows three ideas:

1. **Shared data** — One record store; logging levels control depth (outcomes → trace → provenance).  
2. **Decentralisation** — Topology decides which records each agent may read (`visible_peer` / federated hub).  
3. **Openness** — Optional registry: register when an agent joins, deregister when they leave.

Each principle is spelled out with **code snippets** here: **[guides/doa-principles.md](guides/doa-principles.md)**

## Analysis

After a **file-backed** or **mongo-backed** run you have `output_base/<run_id>/metadata.json` (and for file, `records/`). The `doagent.analysis` package reads that run by `run_id` — no access to agent internals. With `write_output=True`, artefacts go to `output_base/<run_id>/analysis/<category>/` (PNG, PDF, JSON).

Pick tools that match your scenario:

| Tool | Use when |
|------|----------|
| **Provenance** | You want the chain of records that led to an outcome (“why this state?”). |
| **Traceability** | You want how state evolved (“transition graph”). |
| **Accountability** | You have discovery/contribution semantics (e.g. who found which cells). Skip for push-like games without that. |
| **Interpretability** | You want explanations linked to outcomes (needs logging level ≥ 1 for explanations). |

Example after a file run:

```python
from doagent.analysis import provenance, traceability, accountability, interpretability

run_id = session.run_id
output_base = "output"

effective_id = provenance.render_chain_tree("last", run_id, output_base=output_base, write_output=True)
traceability.build_trace_graph(run_id, output_base=output_base, write_output=True)
accountability.causal_attribution(run_id, output_base=output_base, write_output=True)  # if discovery scenario
interpretability.get_explanations_for(effective_id or "last", run_id, output_base=output_base, write_output=True)
```

Gridworld demo runs all four; push demo runs provenance, traceability, interpretability only. Comparisons / baselines: `experiments/` (see `examples/README.md`).

## Project layout

High level: library code in `doagent/`, runnable demos in `examples/`, Colab in `notebooks/`, deeper contributor notes in `docs/`.

**Directory tree + public API table → [guides/layout-and-api.md](guides/layout-and-api.md)**

## Project management

[VibeSafe](https://github.com/lawrennd/vibesafe): `tenets/`, `requirements/`, `cip/`, `backlog/`. Status: `./whats-next`.

## References

[1] Christian Cabrera, Andrei Paleyes, Pierre Thodoroff, and Neil D. Lawrence. 2025. *Machine Learning Systems: A Survey from a Data-Oriented Perspective.* ACM Computing Surveys. [ACM](https://dl.acm.org/doi/10.1145/3769292)
