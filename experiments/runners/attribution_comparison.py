"""Compare capture cost and paired judge accuracy."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from experiments._shared import write_summary
from experiments.attribution.baselines import (
    OutputLogCollector,
    StepIOCollector,
)
from experiments.attribution.evaluate import (
    evaluate_attribution,
    evaluate_baseline_cost,
)
from experiments.attribution.judge import run_judges
from experiments.attribution.run import load_yaml, run_addition_team


def _config_path(explicit: str | None) -> Path:
    root = Path(__file__).resolve().parents[2]
    if explicit:
        return Path(explicit)
    return root / "experiments" / "attribution" / "config.yaml"


def run_capture_cost(
    query: dict,
    plant: dict,
    output_base: str,
) -> Path:
    """Time W, T, and live D0/D1/D2. Do not call judges."""
    results = {
        "w": evaluate_baseline_cost(
            query,
            plant,
            capture="w",
            output_base=output_base,
        ),
        "t": evaluate_baseline_cost(
            query,
            plant,
            capture="t",
            output_base=output_base,
        ),
    }
    for level in (0, 1, 2):
        results[f"d{level}"] = evaluate_attribution(
            query,
            plant,
            storage="file",
            output_base=output_base,
            logging_level=level,
        )
    file_result = results["d2"]
    if not file_result.run_path:
        raise RuntimeError("D2 condition did not create a run folder.")
    summary_path = Path(file_result.run_path) / "attribution_capture_cost.json"
    write_summary(
        summary_path,
        {"runs": {key: asdict(value) for key, value in results.items()}},
    )
    print(f"Capture-cost summary written to {summary_path}")
    return summary_path


def run_attribution_accuracy(
    query: dict,
    plant: dict,
    output_base: str,
) -> Path:
    """Run one paired D2+W+T execution, project D0/D1, then judge five views."""
    collectors = (OutputLogCollector(), StepIOCollector())
    result = run_addition_team(
        query,
        plant,
        storage="file",
        output_base=output_base,
        collectors=collectors,
    )
    session = result["session"]
    if not session.run_path:
        raise RuntimeError("Paired attribution run did not create a run folder.")
    analysis = Path(session.run_path) / "analysis" / "attribution"
    for collector in collectors:
        collector.write(analysis / collector.filename)
    run_judges(session.run_path)
    scores_path = analysis / "scores.json"
    print(f"Attribution scores written to {scores_path}")
    return scores_path


def main(argv: list[str] | None = None) -> None:
    """Run the cost table, the accuracy table, or both in sequence."""
    parser = argparse.ArgumentParser(
        description=(
            "Attribution comparison. Cost is unpaired and offline. "
            "Accuracy is a later paired run plus judges."
        )
    )
    parser.add_argument(
        "--table",
        choices=("cost", "accuracy", "both"),
        default="cost",
        help="Which table to produce. Default: cost (no API key).",
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        help="Optional YAML config (query, plant, output_base).",
    )
    args = parser.parse_args(argv)
    config = load_yaml(_config_path(args.config))
    query = config["query"]
    plant = config.get("plant") or {}
    output_base = str(config.get("output_base", "./output"))
    if args.table in {"cost", "both"}:
        run_capture_cost(query, plant, output_base)
    if args.table in {"accuracy", "both"}:
        run_attribution_accuracy(query, plant, output_base)


if __name__ == "__main__":
    main()
