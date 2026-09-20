"""Posterior analysis of recorded runs, addressed by run_id.

Each property has its own submodule.
Pick the analyses that fit the run.

    from doagent.analysis import (
        accountability,
        interpretability,
        provenance,
        traceability,
        views,
    )

    traceability.build_trace_graph(run_id, output_base=None)
    provenance.walk_chain(record_id, run_id)
    accountability.causal_attribution(run_id)
    interpretability.build_atomic_explanations(record_id, run_id)
    views.decision_steps(records, level=2)

Provenance and traceability apply to any recorded run.
Accountability suits runs that model who contributed what.
Interpretability explains outcomes as transition-level units.
Views project stored records into compact step lists.

Pass a run_id and an optional output_base.
The module resolves the run through its metadata.
"""

from . import accountability, interpretability, provenance, traceability, views

__all__ = [
    "accountability",
    "interpretability",
    "provenance",
    "traceability",
    "views",
]
