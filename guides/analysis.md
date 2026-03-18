# Analysis

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

The **demos** use this pattern: gridworld_demo runs all four (it has discovery); push_demo runs provenance, traceability, and interpretability only (no attribution). For **comparisons** (e.g. baseline vs file, or multiple topologies), use the scripts under `experiments/` (see `examples/README.md`).
