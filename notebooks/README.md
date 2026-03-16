# DOAgent notebooks

Step-by-step Colab-ready notebooks that use only the `doagent` library and code defined in each notebook. No need to clone the repo; run in Google Colab.

| Notebook | Description |
|----------|-------------|
| [01_minimal_demo.ipynb](01_minimal_demo.ipynb) | Install doagent → in-memory session → stub env and noop policy → one step → inspect records. |
| [02_push_demo.ipynb](02_push_demo.ipynb) | Install doagent + PettingZoo → file-backed session → push env and heuristic policies → run loop → provenance, traceability, interpretability. |
| [03_gridworld_demo.ipynb](03_gridworld_demo.ipynb) | Install doagent → minimal grid env and random policy → file-backed session → run loop with shared map → full analysis (including causal attribution). |

**How to run:** Open a notebook in [Google Colab](https://colab.research.google.com/) (e.g. upload from the repo or open from GitHub). Run cells in order. The first cell installs the library from the repository.
