"""Analysis module: run_id-based analysis for provenance, traceability, accountability, interpretability.

Use the submodules for the property you need:

  from doagent.analysis import traceability, provenance, accountability, interpretability

  traceability.build_trace_graph(run_id, output_base=None)
  provenance.walk_chain(record_id, run_id, ...)
  accountability.causal_attribution(run_id, ...)
  interpretability.get_explanations_for(record_id, run_id, ...)

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
