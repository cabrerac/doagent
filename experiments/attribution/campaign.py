"""Repeat the attribution measurements and write CSV and JSON.

A campaign folder contains a runs directory, cost.csv, accuracy.csv, and summary.json.
A cost repeat executes the team once under one capture condition.
It records elapsed time and the bytes left on disk.
An attribution repeat is one judge pass over packs from one execution.
The executions count is how many trajectories are judged.
Each CSV file is long format.
One row is one measurement.
The summary is derived from those rows.
"""

from __future__ import annotations

import csv
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from experiments._shared import EvaluationResult
from experiments.attribution.baselines import (
    OutputLogCollector,
    StepIOCollector,
)
from experiments.attribution.evaluate import (
    evaluate_attribution,
    evaluate_baseline_cost,
)
from experiments.attribution.judge import (
    JUDGE_METHODS,
    JUDGE_VIEWS,
    run_judges,
)
from experiments.attribution.manifest import config_hash, git_commit
from experiments.attribution.run import run_addition_team

CAPTURE_CONDITIONS = ("w", "t", "d0", "d1", "d2")

COST_FIELDS = (
    "condition",
    "repeat",
    "elapsed_seconds",
    "capture_bytes",
    "run_id",
    "run_path",
)

ACCURACY_FIELDS = (
    "execution",
    "run_id",
    "judge_pass",
    "method",
    "view",
    "predicted_who",
    "predicted_when",
    "gold_who",
    "gold_when",
    "who_match",
    "when_match",
    "both_match",
    "input_tokens",
    "output_tokens",
    "total_tokens",
)

LOOKUP_METHOD = "lookup"
LOOKUP_VIEW = "d2"


def _progress(message: str) -> None:
    """Write one progress line to stdout and flush it.

    Args:
        message:
            Line to show.
    """
    print(message, flush=True)


def new_campaign_dir(
    output_base: str | Path,
    *,
    stamp: Optional[str] = None,
) -> Path:
    """Create a campaign folder with its runs subfolder.

    Args:
        output_base:
            Parent directory for the campaign folder.
        stamp:
            Folder name suffix. The current UTC time is used when omitted.

    Returns:
        Path of the new campaign folder.
    """
    marker = stamp or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    campaign_dir = Path(output_base) / f"attribution_campaign_{marker}"
    (campaign_dir / "runs").mkdir(parents=True, exist_ok=True)
    return campaign_dir


def runs_base(campaign_dir: str | Path) -> str:
    """Return the folder that individual executions write into.

    Args:
        campaign_dir:
            Campaign folder.

    Returns:
        Path of the runs subfolder, as a string.
    """
    return str(Path(campaign_dir) / "runs")


def measure_capture_condition(
    query: Mapping[str, Any],
    plant: Mapping[str, Any],
    condition: str,
    *,
    output_base: str,
    capture_runner: Optional[Callable[..., EvaluationResult]] = None,
) -> EvaluationResult:
    """Execute and time one capture condition.

    W and T time a host loop and the collector pack.
    D0, D1, and D2 time a Session run at that logging level.

    Args:
        query:
            Task fields for this run.
        plant:
            Planted fault for this run.
        condition:
            One of w, t, d0, d1, or d2.
        output_base:
            Folder for that execution's files.
        capture_runner:
            Callable that times one condition.
            The addition-team measurement is used when this is omitted.

    Returns:
        Timed result with elapsed seconds and bytes on disk.

    Raises:
        ValueError:
            If condition is not a known capture name.
    """
    if capture_runner is not None:
        return capture_runner(
            dict(query),
            dict(plant),
            condition,
            output_base=output_base,
        )
    if condition in ("w", "t"):
        return evaluate_baseline_cost(
            dict(query),
            dict(plant),
            capture=condition,
            output_base=output_base,
        )
    if condition in ("d0", "d1", "d2"):
        return evaluate_attribution(
            dict(query),
            dict(plant),
            storage="file",
            output_base=output_base,
            logging_level=int(condition[1]),
        )
    raise ValueError(f"Unknown capture condition {condition!r}")


def run_cost_campaign(
    query: Mapping[str, Any],
    plant: Mapping[str, Any],
    *,
    campaign_dir: str | Path,
    repeats: int,
    conditions: Sequence[str] = CAPTURE_CONDITIONS,
    capture_runner: Optional[Callable[..., EvaluationResult]] = None,
) -> List[Dict[str, Any]]:
    """Execute every capture condition the requested number of times.

    Time includes writing the capture log.
    Bytes count that log as it sits on disk.

    Args:
        query:
            The numbers to add, as a and b.
        plant:
            Optional plant_wrong_sum and plant_accept_wrong.
        campaign_dir:
            Campaign folder.
        repeats:
            How many times to run each condition.
        conditions:
            Capture names to run. Defaults to w, t, d0, d1, and d2.
        capture_runner:
            Callable that times one condition.
            The addition-team measurement is used when this is omitted.

    Returns:
        One row per execution.

    Raises:
        ValueError:
            If repeats is less than 1.
    """
    if repeats < 1:
        raise ValueError("Cost repeats must be at least 1.")
    output_base = runs_base(campaign_dir)
    rows: List[Dict[str, Any]] = []
    _progress(
        f"Capture cost: {len(conditions)} conditions x {repeats} repeats"
    )
    for condition in conditions:
        for index in range(repeats):
            result = measure_capture_condition(
                query,
                plant,
                condition,
                output_base=output_base,
                capture_runner=capture_runner,
            )
            rows.append(
                {
                    "condition": condition,
                    "repeat": index + 1,
                    "elapsed_seconds": result.elapsed_seconds,
                    "capture_bytes": result.output_bytes,
                    "run_id": result.run_id or "",
                    "run_path": result.run_path or "",
                }
            )
        _progress(f"  {condition} {repeats}/{repeats}")
    return rows


def _judge_settings(judge: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Read judge settings from config, filling in defaults for missing keys.

    Args:
        judge:
            Optional judge block from the experiment config.

    Returns:
        Provider, model, temperature, methods, and views.
    """
    settings = dict(judge or {})
    return {
        "provider": str(settings.get("provider", "openai")),
        "model": str(settings.get("model", "gpt-4o")),
        "temperature": float(settings.get("temperature", 0.0)),
        "methods": tuple(settings.get("methods") or JUDGE_METHODS),
        "views": tuple(settings.get("views") or JUDGE_VIEWS),
    }


def _scored_row(
    *,
    execution: int,
    run_id: Optional[str],
    judge_pass: Any,
    method: str,
    view: str,
    entry: Mapping[str, Any],
    gold: Mapping[str, Any],
) -> Dict[str, Any]:
    """Turn one scored prediction into a CSV row.

    Match flags are written as 1 or 0.

    Args:
        execution:
            Execution index, starting at 1.
        run_id:
            Id of the stored run.
        judge_pass:
            Judge pass index, or an empty value for lookup.
        method:
            Prompting style or lookup.
        view:
            Evidence pack name.
        entry:
            Scored prediction with usage.
        gold:
            Gold who and when labels.

    Returns:
        One accuracy CSV row.
    """
    usage = entry.get("usage") or {}
    who_match = bool(entry.get("who_match"))
    when_match = bool(entry.get("when_match"))
    return {
        "execution": execution,
        "run_id": run_id or "",
        "judge_pass": judge_pass,
        "method": method,
        "view": view,
        "predicted_who": entry.get("who"),
        "predicted_when": entry.get("when"),
        "gold_who": gold.get("who"),
        "gold_when": gold.get("when"),
        "who_match": int(who_match),
        "when_match": int(when_match),
        "both_match": int(who_match and when_match),
        "input_tokens": int(usage.get("input_tokens", 0) or 0),
        "output_tokens": int(usage.get("output_tokens", 0) or 0),
        "total_tokens": int(usage.get("total_tokens", 0) or 0),
    }


def accuracy_rows_from_scores(
    scores: Mapping[str, Any],
    *,
    execution: int,
    run_id: Optional[str],
    judge_pass: int,
    include_lookup: bool = False,
) -> List[Dict[str, Any]]:
    """Flatten one scored judge pass into rows.

    Args:
        scores:
            Scores dict from one judge pass.
        execution:
            Execution index, starting at 1.
        run_id:
            Id of the stored run.
        judge_pass:
            Judge pass index.
        include_lookup:
            If true, also emit the lookup row for this execution.

    Returns:
        Accuracy rows for that pass.
    """
    gold = scores.get("gold") or {}
    rows: List[Dict[str, Any]] = []
    for method, views in (scores.get("judges") or {}).items():
        for view, entry in views.items():
            rows.append(
                _scored_row(
                    execution=execution,
                    run_id=run_id,
                    judge_pass=judge_pass,
                    method=method,
                    view=view,
                    entry=entry,
                    gold=gold,
                )
            )
    if include_lookup and scores.get("lookup"):
        rows.append(
            _scored_row(
                execution=execution,
                run_id=run_id,
                judge_pass="",
                method=LOOKUP_METHOD,
                view=LOOKUP_VIEW,
                entry=scores["lookup"],
                gold=gold,
            )
        )
    return rows


def run_accuracy_campaign(
    query: Mapping[str, Any],
    plant: Mapping[str, Any],
    *,
    campaign_dir: str | Path,
    executions: int,
    judge_passes: int,
    judge: Optional[Mapping[str, Any]] = None,
    judge_runner: Optional[Callable[..., Dict[str, Any]]] = None,
    team_runner: Optional[Callable[..., Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Run paired executions, then judge each one's stored packs repeatedly.

    Each execution writes D2 records and observe-only W and T packs.
    Each judge pass reads those packs from disk.

    Args:
        query:
            The numbers to add, as a and b.
        plant:
            Optional plant_wrong_sum and plant_accept_wrong.
        campaign_dir:
            Campaign folder.
        executions:
            How many paired trajectories to run.
        judge_passes:
            How many times to judge the packs of each execution.
        judge:
            Optional judge block from the experiment config.
        judge_runner:
            Optional callable used in place of the default judge.
        team_runner:
            Callable that runs one paired execution.
            The addition team is used when this is omitted.

    Returns:
        One accuracy row per judged view, method, and pass.

    Raises:
        ValueError:
            If executions or judge_passes is less than 1.
        RuntimeError:
            If an execution does not create a run folder.
    """
    if executions < 1:
        raise ValueError("Attribution executions must be at least 1.")
    if judge_passes < 1:
        raise ValueError("Judge passes must be at least 1.")
    runner = judge_runner or run_judges
    execute = team_runner or run_addition_team
    settings = _judge_settings(judge)
    output_base = runs_base(campaign_dir)
    rows: List[Dict[str, Any]] = []
    _progress(
        f"Attribution: {executions} execution(s), {judge_passes} judge pass(es)"
    )
    for execution in range(1, executions + 1):
        _progress(f"  execution {execution}/{executions}: running team")
        collectors = (OutputLogCollector(), StepIOCollector())
        result = execute(
            dict(query),
            dict(plant),
            storage="file",
            output_base=output_base,
            collectors=collectors,
        )
        session = result["session"]
        if not session.run_path:
            raise RuntimeError("Paired attribution run did not create a run folder.")
        analysis_dir = Path(session.run_path) / "analysis" / "attribution"
        for collector in collectors:
            collector.write(analysis_dir / collector.filename)
        _progress(f"  execution {execution}/{executions}: packs written")
        for judge_pass in range(1, judge_passes + 1):
            _progress(
                f"  judging pass {judge_pass}/{judge_passes}"
                f" (execution {execution})"
            )
            judged = runner(
                session.run_path,
                provider=settings["provider"],
                model=settings["model"],
                temperature=settings["temperature"],
                methods=settings["methods"],
                views=settings["views"],
                label=f"pass{judge_pass:02d}",
            )
            rows.extend(
                accuracy_rows_from_scores(
                    judged["scores"],
                    execution=execution,
                    run_id=session.run_id,
                    judge_pass=judge_pass,
                    include_lookup=judge_pass == 1,
                )
            )
    return rows


def _percentile(ordered: Sequence[float], fraction: float) -> float:
    """Return an interpolated percentile of an already sorted sequence.

    Args:
        ordered:
            Values sorted from low to high.
        fraction:
            Point on the unit interval, such as 0.10 or 0.90.

    Returns:
        The interpolated value at that fraction.
    """
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _spread(values: Sequence[float]) -> Dict[str, float]:
    """Summarise repeated measurements of one quantity.

    Args:
        values:
            Repeated measurements of the same quantity.

    Returns:
        Count, median, mean, min, max, 10th and 90th percentiles, and stdev.
    """
    ordered = sorted(float(value) for value in values)
    return {
        "n": len(ordered),
        "median": statistics.median(ordered),
        "mean": statistics.fmean(ordered),
        "min": ordered[0],
        "max": ordered[-1],
        "p10": _percentile(ordered, 0.10),
        "p90": _percentile(ordered, 0.90),
        "stdev": statistics.stdev(ordered) if len(ordered) > 1 else 0.0,
    }


def summarise_cost(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Aggregate cost rows by capture condition.

    Args:
        rows:
            Cost CSV rows.

    Returns:
        Elapsed time and capture bytes, summarised per condition.
    """
    grouped: Dict[str, List[Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["condition"]), []).append(row)
    return {
        condition: {
            "elapsed_seconds": _spread([item["elapsed_seconds"] for item in items]),
            "capture_bytes": _spread([item["capture_bytes"] for item in items]),
        }
        for condition, items in grouped.items()
    }


def summarise_accuracy(rows: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Aggregate accuracy rows by method and view.

    Args:
        rows:
            Accuracy CSV rows.

    Returns:
        Who, when, and both accuracy, plus token totals, per method and view.
    """
    grouped: Dict[str, Dict[str, List[Mapping[str, Any]]]] = {}
    for row in rows:
        method = str(row["method"])
        view = str(row["view"])
        grouped.setdefault(method, {}).setdefault(view, []).append(row)
    summary: Dict[str, Any] = {}
    for method, views in grouped.items():
        summary[method] = {}
        for view, items in views.items():
            count = len(items)
            summary[method][view] = {
                "n": count,
                "who_accuracy": sum(int(item["who_match"]) for item in items) / count,
                "when_accuracy": sum(int(item["when_match"]) for item in items) / count,
                "both_accuracy": sum(int(item["both_match"]) for item in items) / count,
                "total_tokens": _spread([item["total_tokens"] for item in items]),
            }
    return summary


def write_rows(
    path: str | Path,
    rows: Iterable[Mapping[str, Any]],
    fieldnames: Sequence[str],
) -> Path:
    """Write measurement rows as CSV, one row per measurement.

    Args:
        path:
            Destination file.
        rows:
            Measurement dicts.
        fieldnames:
            Column names, in order.

    Returns:
        Path of the written file.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return target


def update_summary(
    campaign_dir: str | Path,
    section: str,
    payload: Mapping[str, Any],
    *,
    config: Optional[Mapping[str, Any]] = None,
) -> Path:
    """Merge one section into summary.json, keeping sections already there.

    Args:
        campaign_dir:
            Campaign folder.
        section:
            Top-level key to write, such as cost or attribution.
        payload:
            Value stored under that key.
        config:
            Optional experiment config recorded beside the section.

    Returns:
        Path of the written summary file.
    """
    path = Path(campaign_dir) / "summary.json"
    summary: Dict[str, Any] = {}
    if path.is_file():
        summary = json.loads(path.read_text(encoding="utf-8"))
    summary.setdefault("campaign_id", Path(campaign_dir).name)
    summary.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    summary["git_commit"] = git_commit()
    if config is not None:
        summary["config"] = dict(config)
        summary["config_hash"] = config_hash(dict(config))
    summary[section] = dict(payload)
    path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return path
