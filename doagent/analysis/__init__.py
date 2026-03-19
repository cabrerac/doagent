"""Analysis module: run_id-based analysis for provenance, traceability, accountability, interpretability.

Use the submodules for the property you need. **Choose analyses that fit your scenario** —
not every tool is relevant for every run:

  from doagent.analysis import traceability, provenance, accountability, interpretability

  traceability.build_trace_graph(run_id, output_base=None)   # any run: how did state evolve?
  provenance.walk_chain(record_id, run_id, ...)              # any run: why did this state happen?
  accountability.causal_attribution(run_id, ...)              # scenarios with discovery/contribution (e.g. gridworld)
  interpretability.build_atomic_explanations(record_id, run_id, ...)  # transition-level atomic units

- **Provenance** and **traceability**: generic; use for any recorded run.
- **Accountability** (causal attribution): best when the run has a clear notion of
  "who contributed what" (e.g. discovered cells, coverage). Less meaningful for
  scenarios that do not model discovery or contribution in the same way.
- **Interpretability**: use when you care about explanations for outcomes as
  transition-level atomic explanation units.

Resolution is internal: pass run_id (and optional output_base); the module resolves
via run metadata and uses inspect-style access to records.
"""

from . import accountability, interpretability, provenance, traceability

__all__ = [
    "accountability",
    "interpretability",
    "provenance",
    "traceability",
]
