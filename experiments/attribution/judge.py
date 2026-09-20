"""GPT-4o failure-attribution judges for W, T, and D views.

The implementation follows the three prompt-access patterns studied by
Who&When: all-at-once, step-by-step, and binary search. Attribution labels are
never included in prompts. They are loaded only by downstream scoring code.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from examples._shared.llm_client import (
    LLMClient,
    LLMResponse,
    create_llm_client,
)
from experiments.attribution.score import score_attribution_results


SYSTEM_PROMPT = (
    "You diagnose failed multi-agent runs. Identify the agent responsible "
    "for the decisive error and the earliest step where correcting that "
    "error would change the failed outcome. Return JSON only."
)


def _parse_json(text: str) -> Dict[str, Any]:
    """Parse a JSON object, accepting an optional Markdown code fence."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(
            lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        )
        if cleaned.lstrip().startswith("json"):
            cleaned = cleaned.lstrip()[4:].lstrip()
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("Judge response must be a JSON object.")
    return value


def _call(
    client: LLMClient,
    *,
    model: str,
    temperature: float,
    instruction: str,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    response: LLMResponse = client(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ],
    )
    parsed = _parse_json(response.text)
    call = response.to_dict()
    call["parsed"] = parsed
    return parsed, call


def _task_text(task: Dict[str, Any]) -> str:
    """Serialize only task information that is safe to show the judge."""
    allowed = {
        key: task[key]
        for key in ("a", "b", "correct")
        if key in task
    }
    return json.dumps(allowed, sort_keys=True)


def _d_steps(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Group native D records around scored decision rounds."""
    records_list = list(records)
    rounds: Dict[int, List[Dict[str, Any]]] = {}
    for record in records_list:
        payload = record.get("payload") or {}
        decision = payload.get("decision") or {}
        request = decision.get("request") or {}
        context = request.get("context") or {}
        round_id = context.get("round")
        if isinstance(round_id, int):
            rounds.setdefault(round_id, []).append(record)
            continue
        payload_round = payload.get("round")
        if isinstance(payload_round, int):
            rounds.setdefault(payload_round, []).append(record)
    return [
        {"step": round_id, "records": rounds[round_id]}
        for round_id in sorted(rounds)
    ]


D_VIEWS = frozenset({"d", "d0", "d1", "d2"})
JUDGE_VIEWS = ("w", "t", "d0", "d1", "d2")


def _steps(view: str, evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if view in D_VIEWS:
        return _d_steps(evidence)
    return sorted(evidence, key=lambda item: item.get("step", 0))


def _all_at_once(
    client: LLMClient,
    *,
    task: Dict[str, Any],
    evidence: List[Dict[str, Any]],
    model: str,
    temperature: float,
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    instruction = (
        f"Task: {_task_text(task)}\n"
        f"Complete failure evidence:\n{json.dumps(evidence, indent=2)}\n"
        'Return {"who": string, "when": integer, "reason": string}.'
    )
    prediction, call = _call(
        client,
        model=model,
        temperature=temperature,
        instruction=instruction,
    )
    return prediction, [call]


def _step_by_step(
    client: LLMClient,
    *,
    task: Dict[str, Any],
    steps: List[Dict[str, Any]],
    model: str,
    temperature: float,
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    calls: List[Dict[str, Any]] = []
    for step in steps:
        instruction = (
            f"Task: {_task_text(task)}\n"
            f"Current step:\n{json.dumps(step, indent=2)}\n"
            "Decide whether the decisive failure occurs in this step. "
            'Return {"failure_found": boolean, "who": string or null, '
            '"when": integer or null, "reason": string}.'
        )
        parsed, call = _call(
            client,
            model=model,
            temperature=temperature,
            instruction=instruction,
        )
        calls.append(call)
        if parsed.get("failure_found") is True:
            return {
                "who": parsed.get("who"),
                "when": parsed.get("when"),
                "reason": parsed.get("reason", ""),
            }, calls
    return {
        "who": None,
        "when": None,
        "reason": "No decisive failure identified.",
    }, calls


def _binary_search(
    client: LLMClient,
    *,
    task: Dict[str, Any],
    steps: List[Dict[str, Any]],
    model: str,
    temperature: float,
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    calls: List[Dict[str, Any]] = []
    candidates = list(steps)
    if not candidates:
        return {"who": None, "when": None, "reason": "No steps."}, calls

    while len(candidates) > 1:
        midpoint = (len(candidates) + 1) // 2
        lower = candidates[:midpoint]
        upper = candidates[midpoint:]
        instruction = (
            f"Task: {_task_text(task)}\n"
            f"Lower half:\n{json.dumps(lower, indent=2)}\n"
            f"Upper half:\n{json.dumps(upper, indent=2)}\n"
            "Choose which half contains the decisive failure. "
            'Return {"half": "lower" or "upper", "reason": string}.'
        )
        parsed, call = _call(
            client,
            model=model,
            temperature=temperature,
            instruction=instruction,
        )
        calls.append(call)
        half = parsed.get("half")
        if half not in {"lower", "upper"}:
            raise ValueError("Binary judge must choose lower or upper.")
        candidates = lower if half == "lower" else upper

    instruction = (
        f"Task: {_task_text(task)}\n"
        f"Candidate decisive step:\n{json.dumps(candidates[0], indent=2)}\n"
        'Return {"who": string, "when": integer, "reason": string}.'
    )
    prediction, call = _call(
        client,
        model=model,
        temperature=temperature,
        instruction=instruction,
    )
    calls.append(call)
    return prediction, calls


def judge_view(
    *,
    method: str,
    view: str,
    task: Dict[str, Any],
    evidence: List[Dict[str, Any]],
    client: LLMClient,
    model: str = "gpt-4o",
    temperature: float = 0.0,
) -> Dict[str, Any]:
    """Judge one W, T, or D view and return prediction plus token metadata."""
    if view not in {"w", "t", *D_VIEWS}:
        raise ValueError(f"Unknown view: {view!r}")
    if method == "all_at_once":
        prediction, calls = _all_at_once(
            client,
            task=task,
            evidence=evidence,
            model=model,
            temperature=temperature,
        )
    elif method == "step_by_step":
        prediction, calls = _step_by_step(
            client,
            task=task,
            steps=_steps(view, evidence),
            model=model,
            temperature=temperature,
        )
    elif method == "binary_search":
        prediction, calls = _binary_search(
            client,
            task=task,
            steps=_steps(view, evidence),
            model=model,
            temperature=temperature,
        )
    else:
        raise ValueError(f"Unknown judging method: {method!r}")

    usage = {
        key: sum(int(call["usage"].get(key, 0)) for call in calls)
        for key in ("input_tokens", "output_tokens", "total_tokens")
    }
    return {
        "method": method,
        "view": view,
        "prediction": prediction,
        "model": model,
        "temperature": temperature,
        "usage": usage,
        "calls": calls,
    }


VIEW_FILES = {
    "w": ("who_when.json",),
    "t": ("trace_elephant.json",),
    "d0": ("d0.json",),
    "d1": ("d1.json",),
    "d2": ("d2.json",),
}


def _load_view(artifact_dir: Path, view: str) -> List[Dict[str, Any]]:
    """Load the collector pack or D-level file for one judged view."""
    for name in VIEW_FILES[view]:
        path = artifact_dir / name
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, list):
                raise ValueError(f"{path} must contain a JSON list.")
            return payload
    raise FileNotFoundError(
        f"No {view} evidence under {artifact_dir} (tried {VIEW_FILES[view]})."
    )


def run_judges(
    run_path: str | Path,
    *,
    provider: str = "openai",
    model: str = "gpt-4o",
    temperature: float = 0.0,
) -> Dict[str, Any]:
    """Run all three methods over W, T, D0, D1, and D2 from one persisted run."""
    run_dir = Path(run_path)
    artifact_dir = run_dir / "analysis" / "attribution"
    gold = json.loads((run_dir / "gold.json").read_text(encoding="utf-8"))
    task = dict(gold.get("query") or {})
    client = create_llm_client(provider=provider)
    results: Dict[str, Any] = {}
    for method in ("all_at_once", "step_by_step", "binary_search"):
        results[method] = {}
        for view in JUDGE_VIEWS:
            evidence = _load_view(artifact_dir, view)
            results[method][view] = judge_view(
                method=method,
                view=view,
                task=task,
                evidence=evidence,
                client=client,
                model=model,
                temperature=temperature,
            )
    lookup_path = artifact_dir / "lookup.json"
    lookup = None
    if lookup_path.exists():
        lookup = json.loads(lookup_path.read_text(encoding="utf-8"))
    scores = score_attribution_results(
        gold=gold,
        lookup=lookup,
        judges=results,
    )
    output_path = artifact_dir / "judges.json"
    output_path.write_text(
        json.dumps(results, indent=2) + "\n",
        encoding="utf-8",
    )
    scores_path = artifact_dir / "scores.json"
    scores_path.write_text(
        json.dumps(scores, indent=2) + "\n",
        encoding="utf-8",
    )
    return results


def main(argv: List[str] | None = None) -> None:
    """Run the configured judges for a persisted attribution run."""
    parser = argparse.ArgumentParser(description="Judge an attribution run")
    parser.add_argument("run_path", help="Path to output/<run_id>")
    parser.add_argument("--provider", default="openai")
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--temperature", type=float, default=0.0)
    args = parser.parse_args(argv)
    run_judges(
        args.run_path,
        provider=args.provider,
        model=args.model,
        temperature=args.temperature,
    )


if __name__ == "__main__":
    main()
