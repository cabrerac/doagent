# DOAgent notebooks

Step-by-step Colab-ready notebooks that use only the `doagent` library and code defined in each notebook. No need to clone the repo; click **Open in Colab** to run in Google Colab. (To open in a new tab: right-click the badge → **Open link in new tab**.)

| Notebook | Open in Colab | Description |
|----------|---------------|-------------|
| 01_minimal_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/01_minimal_demo.ipynb) | Install doagent → session with in-memory as shared data model → stub env and noop policy → one step → inspect records. |
| 02_push_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/02_push_demo.ipynb) | Install doagent + PettingZoo → session with file as shared data model → push env and heuristic policies → run loop → provenance, traceability, interpretability. |
| 03_gridworld_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/03_gridworld_demo.ipynb) | Install doagent → minimal grid env and random policy → session with file as shared data model → run loop with shared map → full analysis (including causal attribution). |

**How to run:** Click **Open in Colab** above (or open the notebook from GitHub in [Colab](https://colab.research.google.com/)). Run cells in order. The first cell installs the library from the repository.

**Config alignment:** Push and gridworld notebooks use the same parameters as the local examples (`examples/push_demo/`, `examples/gridworld_demo/`, `gridworld_demo_config.yaml`) so behaviour matches between Colab and local runs. The gridworld notebook demonstrates **decentralisation** (peer-to-peer topology) and **openness** (join/leave records + `visible_participants`). The run loop matches the local demo: `decision_context(..., summarise=build_shared_map)` for the shared map, and `visible_participants` passed into `decide`.
