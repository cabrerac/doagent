"""Evaluate one addition-team capture condition and measure that same run."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Dict

from experiments._shared import EvaluationResult, output_bytes_from_path
from experiments.attribution.baselines import (
    OutputLogCollector,
    StepIOCollector,
    run_direct_team,
)
from experiments.attribution.manifest import build_run_manifest, write_run_manifest
from experiments.attribution.projections import lookup_planted_failure
from experiments.attribution.run import run_addition_team


def evaluate_attribution(
    query: Dict[str, Any],
    plant: Dict[str, Any],
    *,
    storage: str,
    output_base: str = "./output",
    logging_level: int = 2,
) -> EvaluationResult:
    """Run and time one live capture at a logging level.

    Args:
        query:
            The numbers to add, as a and b.
        plant:
            Optional plant_wrong_sum and plant_accept_wrong.
        storage:
            Storage name, such as memory or file.
        output_base:
            Root folder for the run.
        logging_level:
            Session recording level, 0, 1, or 2.

    Returns:
        Elapsed time, record bytes, gold labels, and the lookup result.
    """
    started = perf_counter()
    result = run_addition_team(
        query,
        plant,
        storage=storage,
        output_base=output_base,
        logging_level=logging_level,
        write_eval_artifacts=False,
    )
    elapsed = perf_counter() - started
    session = result["session"]
    gold = result["gold"]
    records_path = None
    if session.run_path:
        records_path = Path(session.run_path) / "records"
        gold_path = Path(session.run_path) / "gold.json"
        gold_path.write_text(json.dumps(gold, indent=2) + "\n", encoding="utf-8")
        gold["gold_path"] = str(gold_path)
        write_run_manifest(
            session.run_path,
            build_run_manifest(
                run_id=session.run_id,
                storage=storage,
                query=query,
                plant=plant,
                logging_level=logging_level,
                output_base=output_base,
            ),
        )
    lookup = lookup_planted_failure(session.inspect("agent_update")) or {}
    return EvaluationResult(
        condition={
            "scenario": "attribution",
            "capture": f"d{logging_level}",
            "storage": storage,
            "logging_level": logging_level,
            "query": query,
            "plant": plant,
        },
        task_metrics={
            "gold_who": gold.get("gold_who"),
            "gold_when": gold.get("gold_when"),
            "lookup_who": lookup.get("who"),
            "lookup_when": lookup.get("when"),
        },
        elapsed_seconds=elapsed,
        output_bytes=output_bytes_from_path(records_path),
        run_id=session.run_id,
        run_path=str(session.run_path) if session.run_path else None,
    )


def evaluate_baseline_cost(
    query: Dict[str, Any],
    plant: Dict[str, Any],
    *,
    capture: str,
    output_base: str = "./output",
) -> EvaluationResult:
    """Time the direct host loop and the write of one collector pack.

    Args:
        query:
            The numbers to add, as a and b.
        plant:
            Optional plant_wrong_sum and plant_accept_wrong.
        capture:
            Either w or t.
        output_base:
            Root folder for the run.

    Returns:
        Elapsed time, pack bytes, and the gold labels.

    Raises:
        ValueError:
            If capture is outside w and t.
    """
    if capture == "w":
        collector = OutputLogCollector()
    elif capture == "t":
        collector = StepIOCollector()
    else:
        raise ValueError(f"Unknown baseline capture {capture!r}")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    run_dir = Path(output_base) / f"attribution_{capture}_cost_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    pack_path = run_dir / collector.filename
    started = perf_counter()
    result = run_direct_team(query, plant, collectors=(collector,))
    collector.write(pack_path)
    elapsed = perf_counter() - started
    gold = result["gold"]
    (run_dir / "gold.json").write_text(
        json.dumps(gold, indent=2) + "\n",
        encoding="utf-8",
    )
    return EvaluationResult(
        condition={
            "scenario": "attribution",
            "capture": capture,
            "storage": "direct",
            "query": query,
            "plant": plant,
        },
        task_metrics={
            "gold_who": gold.get("gold_who"),
            "gold_when": gold.get("gold_when"),
            "solver_value": result["solver_value"],
        },
        elapsed_seconds=elapsed,
        output_bytes=pack_path.stat().st_size,
        run_id=None,
        run_path=str(run_dir),
    )
