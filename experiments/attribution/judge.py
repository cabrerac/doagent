"""GPT-4o failure-attribution judges for W, T, and D views.

The three prompting styles are all-at-once, step-by-step, and binary search.
The question is when the failure becomes inevitable.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from doagent.analysis.views import decision_steps
from examples._shared.llm_client import (
    LLMClient,
    LLMResponse,
    create_llm_client,
)
from experiments.attribution.score import score_attribution_results


SYSTEM_PROMPT = (
    "You diagnose failed multi-agent runs. "
    "The team is an orchestrator, a solver, and a checker. "
    "Name the agent accountable for the failed outcome and the step of that decision. "
    "The decisive step is the earliest point at which the failure becomes inevitable. "
    "An earlier mistake is not decisive if a later agent is still expected to recover. "
    "The failure becomes decisive when that recovery is missed. "
    "Return JSON only."
)


def _parse_json(text: str) -> Dict[str, Any]:
    """Parse a JSON object from model text.

    Args:
        text:
            Model output, optionally wrapped in a Markdown code fence.

    Returns:
        The parsed object.

    Raises:
        ValueError:
            If the text is not a JSON object.
    """
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
    """Call the judge model and parse its JSON reply.

    Args:
        client:
            Callable that returns text and token usage.
        model:
            Judge model name.
        temperature:
            Sampling temperature.
        instruction:
            User prompt for this call.

    Returns:
        The parsed reply and a dict that records the raw call.
    """
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
    """Serialize only task fields that are safe to show the judge.

    Args:
        task:
            Task dict, which may contain extra keys.

    Returns:
        JSON text with a, b, and correct when those keys are present.
    """
    allowed = {
        key: task[key]
        for key in ("a", "b", "correct")
        if key in task
    }
    return json.dumps(allowed, sort_keys=True)


D_VIEWS = frozenset({"d", "d0", "d1", "d2"})
JUDGE_VIEWS = ("w", "t", "d0", "d1", "d2")
JUDGE_METHODS = ("all_at_once", "step_by_step", "binary_search")
D_VIEW_LEVELS = {"d": 2, "d0": 0, "d1": 1, "d2": 2}


def _evidence_for_view(view: str, evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return the step list the judge should see for one view.

    D views are projected into compact steps.

    Args:
        view:
            Evidence pack name.
        evidence:
            Stored pack contents.

    Returns:
        Step dicts ready to send to a judge method.
    """
    if view in D_VIEWS:
        return decision_steps(evidence, level=D_VIEW_LEVELS[view])
    return list(evidence)


def _steps(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort evidence steps by their step index.

    Args:
        evidence:
            Step dicts that already have a step field.

    Returns:
        The same steps, ordered by step.
    """
    return sorted(evidence, key=lambda item: item.get("step", 0))


def _all_at_once(
    client: LLMClient,
    *,
    task: Dict[str, Any],
    evidence: List[Dict[str, Any]],
    model: str,
    temperature: float,
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Judge the full evidence list in one call.

    Args:
        client:
            Callable that returns text and token usage.
        task:
            Task fields shown in the prompt.
        evidence:
            Full step list.
        model:
            Judge model name.
        temperature:
            Sampling temperature.

    Returns:
        The prediction and the list of recorded calls.
    """
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
    """Judge steps in order and stop at the first inevitable failure.

    Args:
        client:
            Callable that returns text and token usage.
        task:
            Task fields shown in the prompt.
        steps:
            Step list in time order.
        model:
            Judge model name.
        temperature:
            Sampling temperature.

    Returns:
        The prediction and the list of recorded calls.
    """
    calls: List[Dict[str, Any]] = []
    for step in steps:
        instruction = (
            f"Task: {_task_text(task)}\n"
            f"Current step:\n{json.dumps(step, indent=2)}\n"
            "Decide whether the failure becomes inevitable at this step. "
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
        "reason": "No inevitable failure identified.",
    }, calls


def _binary_search(
    client: LLMClient,
    *,
    task: Dict[str, Any],
    steps: List[Dict[str, Any]],
    model: str,
    temperature: float,
) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Narrow the step list by halves, then judge the remaining step.

    Args:
        client:
            Callable that returns text and token usage.
        task:
            Task fields shown in the prompt.
        steps:
            Step list in time order.
        model:
            Judge model name.
        temperature:
            Sampling temperature.

    Returns:
        The prediction and the list of recorded calls.
    """
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
            "Choose which half contains the step where the failure becomes inevitable. "
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
        f"Candidate step:\n{json.dumps(candidates[0], indent=2)}\n"
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
    """Judge one W, T, or D view and return the prediction plus token usage.

    Args:
        method:
            Prompting style.
        view:
            Evidence pack name.
        task:
            Task fields shown in the prompt.
        evidence:
            Stored pack contents.
        client:
            Callable that returns text and token usage.
        model:
            Judge model name.
        temperature:
            Sampling temperature.

    Returns:
        Prediction, usage totals, and the recorded calls.

    Raises:
        ValueError:
            If the method or view is unknown.
    """
    if view not in {"w", "t", *D_VIEWS}:
        raise ValueError(f"Unknown view: {view!r}")
    packed = _evidence_for_view(view, evidence)
    if method == "all_at_once":
        prediction, calls = _all_at_once(
            client,
            task=task,
            evidence=packed,
            model=model,
            temperature=temperature,
        )
    elif method == "step_by_step":
        prediction, calls = _step_by_step(
            client,
            task=task,
            steps=_steps(packed),
            model=model,
            temperature=temperature,
        )
    elif method == "binary_search":
        prediction, calls = _binary_search(
            client,
            task=task,
            steps=_steps(packed),
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
    """Load the stored pack file for one judged view.

    Args:
        artifact_dir:
            Folder that holds the pack files.
        view:
            Evidence pack name.

    Returns:
        The JSON list stored for that view.

    Raises:
        ValueError:
            If the file exists but is not a JSON list.
        FileNotFoundError:
            If no pack file for that view is present.
    """
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
    methods: Iterable[str] = JUDGE_METHODS,
    views: Iterable[str] = JUDGE_VIEWS,
    label: str | None = None,
) -> Dict[str, Any]:
    """Judge the evidence packs of one persisted run and score them against gold.

    Args:
        run_path:
            Folder holding gold.json and analysis/attribution/.
        provider:
            Judge provider name.
        model:
            Judge model name.
        temperature:
            Sampling temperature recorded with every call.
        methods:
            Prompting styles to run. Defaults to all three.
        views:
            Evidence packs to judge. Defaults to W, T, D0, D1, and D2.
        label:
            Suffix for the written files.
            Repeated passes over one execution use it so no pass overwrites another.

    Returns:
        The raw predictions with token usage, the scores against gold, and the paths of the two written files.
    """
    selected_methods = tuple(methods)
    selected_views = tuple(views)
    unknown_methods = [item for item in selected_methods if item not in JUDGE_METHODS]
    if unknown_methods:
        raise ValueError(f"Unknown judging methods: {unknown_methods}")
    unknown_views = [item for item in selected_views if item not in VIEW_FILES]
    if unknown_views:
        raise ValueError(f"Unknown judged views: {unknown_views}")

    run_dir = Path(run_path)
    artifact_dir = run_dir / "analysis" / "attribution"
    gold = json.loads((run_dir / "gold.json").read_text(encoding="utf-8"))
    task = dict(gold.get("query") or {})
    client = create_llm_client(provider=provider)
    results: Dict[str, Any] = {}
    for method in selected_methods:
        results[method] = {}
        for view in selected_views:
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
    suffix = f"_{label}" if label else ""
    judges_path = artifact_dir / f"judges{suffix}.json"
    judges_path.write_text(
        json.dumps(results, indent=2) + "\n",
        encoding="utf-8",
    )
    scores_path = artifact_dir / f"scores{suffix}.json"
    scores_path.write_text(
        json.dumps(scores, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "judges": results,
        "scores": scores,
        "paths": {"judges": str(judges_path), "scores": str(scores_path)},
    }


def main(argv: List[str] | None = None) -> None:
    """Run the configured judges for a persisted attribution run.

    Args:
        argv:
            Optional command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Judge an attribution run")
    parser.add_argument("run_path", help="Path to output/<run_id>")
    parser.add_argument("--provider", default="openai")
    parser.add_argument("--model", default="gpt-4o")
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument(
        "--methods",
        nargs="+",
        default=list(JUDGE_METHODS),
        help="Prompting styles to run. Fewer methods cost fewer tokens.",
    )
    parser.add_argument(
        "--views",
        nargs="+",
        default=list(JUDGE_VIEWS),
        help="Evidence packs to judge.",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="Suffix for the written files, so repeated passes are all kept.",
    )
    args = parser.parse_args(argv)
    run_judges(
        args.run_path,
        provider=args.provider,
        model=args.model,
        temperature=args.temperature,
        methods=args.methods,
        views=args.views,
        label=args.label,
    )


if __name__ == "__main__":
    main()
