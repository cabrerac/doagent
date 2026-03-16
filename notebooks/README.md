# DOAgent notebooks

Step-by-step Colab-ready notebooks that use only the `doagent` library and code defined in each notebook. No need to clone the repo; click **Open in Colab** to run in Google Colab. (To open in a new tab: right-click the badge → **Open link in new tab**.)

| Notebook | Open in Colab | Description |
|----------|---------------|-------------|
| 01_minimal_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/01_minimal_demo.ipynb) | Install doagent → in-memory session → stub env and noop policy → one step → inspect records. |
| 02_push_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/02_push_demo.ipynb) | Install doagent + PettingZoo → file-backed session → push env and heuristic policies → run loop → provenance, traceability, interpretability. |
| 03_gridworld_demo | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/cabrerac/doagent/blob/main/notebooks/03_gridworld_demo.ipynb) | Install doagent → minimal grid env and random policy → file-backed session → run loop with shared map → full analysis (including causal attribution). |

**How to run:** Click **Open in Colab** above (or open the notebook from GitHub in [Colab](https://colab.research.google.com/)). Run cells in order. The first cell installs the library from the repository.
