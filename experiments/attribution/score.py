"""Score attribution predictions against gold labels.

Lookup is scored beside the judge methods.
Its token counts are zero.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def score_who_when(
    prediction: Optional[Dict[str, Any]],
    gold: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare one who and when prediction with the gold labels.

    Args:
        prediction:
            Predicted who and when.
            An empty prediction is used when this is omitted.
        gold:
            Gold labels with gold_who and gold_when.

    Returns:
        The predicted who and when, and whether each matches gold.
    """
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
    """Score every judge result and the lookup for one run.

    Args:
        gold:
            Gold labels with gold_who and gold_when.
        lookup:
            Lookup who and when.
            An empty prediction is used when this is omitted.
        judges:
            Judge results keyed by method, then by view.

    Returns:
        Gold who and when, the lookup score, and the scored judge results.
    """
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
