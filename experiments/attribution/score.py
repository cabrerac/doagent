"""Score attribution predictions against planted gold labels.

Lookup is reported beside the LLM judges, not as a fourth prompting style.
It has no judge-token cost.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def score_who_when(
    prediction: Optional[Dict[str, Any]],
    gold: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare one who/when prediction with gold labels."""
    predicted = prediction or {}
    return {
        "who": predicted.get("who"),
        "when": predicted.get("when"),
        "who_match": predicted.get("who") == gold.get("gold_who"),
        "when_match": predicted.get("when") == gold.get("gold_when"),
    }


def score_attribution_results(
    *,
    gold: Dict[str, Any],
    lookup: Optional[Dict[str, Any]],
    judges: Dict[str, Dict[str, Dict[str, Any]]],
) -> Dict[str, Any]:
    """Build the accuracy and token table for one judged run."""
    scored_judges: Dict[str, Dict[str, Any]] = {}
    for method, views in judges.items():
        scored_judges[method] = {}
        for view, result in views.items():
            usage = result.get("usage") or {}
            scored_judges[method][view] = {
                **score_who_when(result.get("prediction"), gold),
                "usage": {
                    "input_tokens": int(usage.get("input_tokens", 0) or 0),
                    "output_tokens": int(usage.get("output_tokens", 0) or 0),
                    "total_tokens": int(usage.get("total_tokens", 0) or 0),
                },
            }

    lookup_score = score_who_when(lookup, gold)
    lookup_score["usage"] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }
    return {
        "gold": {
            "who": gold.get("gold_who"),
            "when": gold.get("gold_when"),
        },
        "lookup": lookup_score,
        "judges": scored_judges,
    }
