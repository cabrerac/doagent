"""Run the attribution experiments as repeated campaigns.

Capture cost runs W, T, D0, D1, and D2.
Each run records elapsed time and the bytes left on disk.
Attribution runs one or more paired executions.
Each execution writes D2 records and observe-only W and T packs.
Judges then score those stored packs.

Both tables write long-format CSV and aggregated JSON into one campaign folder.
Figures are drawn into the plots folder when the chosen tables finish.

From the repository root:

    python -m experiments.runners.attribution_comparison
    python -m experiments.runners.attribution_comparison --table accuracy
    python -m experiments.runners.attribution_comparison --table both
    python -m experiments.runners.attribution_comparison --cost-repeats 3
    python -m experiments.runners.attribution_comparison --judge-passes 1
    python -m experiments.runners.attribution_comparison --campaign <folder>

Repeat counts come from the config.
Command-line options override those counts.
The cost table runs offline.
The attribution table calls the judge model.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from experiments.attribution.campaign import (
    ACCURACY_FIELDS,
    COST_FIELDS,
    new_campaign_dir,
    run_accuracy_campaign,
    run_cost_campaign,
    summarise_accuracy,
    summarise_cost,
    update_summary,
    write_rows,
)
from experiments.attribution.judge import run_judges
from experiments.attribution.plots import render_campaign
from experiments.attribution.run import load_yaml

DEFAULT_REPEATS = {"cost": 10, "executions": 1, "judge": 10}


def _config_path(explicit: Optional[str]) -> Path:
    """Return the experiment config path.

    Args:
        explicit:
            Config path given on the command line.
            The attribution config is used when this is omitted.

    Returns:
        Path of the YAML file to load.
    """
    root = Path(__file__).resolve().parents[2]
    if explicit:
        return Path(explicit)
    return root / "experiments" / "attribution" / "config.yaml"


def _repeat_counts(config: Mapping[str, Any]) -> Dict[str, int]:
    """Read the repeat counts from the config.

    Args:
        config:
            Experiment config mapping.

    Returns:
        Cost repeats, paired executions, and judge passes.
    """
    configured = config.get("repeats") or {}
    return {
        key: int(configured.get(key, default))
        for key, default in DEFAULT_REPEATS.items()
    }


def _provenance(config: Mapping[str, Any], repeats: Mapping[str, int]) -> Dict[str, Any]:
    """Collect the settings stored beside the results.

    Args:
        config:
            Experiment config mapping.
        repeats:
            Repeat counts used for this campaign.

    Returns:
        Query, plant, repeats, and judge settings.
    """
    return {
        "query": config.get("query"),
        "plant": config.get("plant") or {},
        "repeats": dict(repeats),
        "judge": config.get("judge") or {},
    }


def capture_cost_table(
    config: Mapping[str, Any],
    *,
    campaign_dir: Path,
    repeats: int,
    capture_runner: Optional[Any] = None,
) -> Path:
    """Time every capture condition and write cost.csv.

    Args:
        config:
            Experiment config mapping.
        campaign_dir:
            Campaign folder.
        repeats:
            How many times to run each condition.
        capture_runner:
            Callable that times one condition.
            The addition-team measurement is used when this is omitted.

    Returns:
        Path of the written CSV file.
    """
    rows = run_cost_campaign(
        config["query"],
        config.get("plant") or {},
        campaign_dir=campaign_dir,
        repeats=repeats,
        capture_runner=capture_runner,
    )
    csv_path = write_rows(campaign_dir / "cost.csv", rows, COST_FIELDS)
    summary = summarise_cost(rows)
    update_summary(
        campaign_dir,
        "capture_cost",
        {"repeats": repeats, "conditions": summary},
        config=_provenance(config, _repeat_counts(config)),
    )
    print(f"Capture cost: {len(rows)} executions -> {csv_path}", flush=True)
    for condition, stats in summary.items():
        seconds = stats["elapsed_seconds"]
        print(
            f"  {condition:<3} median {seconds['median'] * 1000:8.2f} ms"
            f"  (min {seconds['min'] * 1000:.2f}, max {seconds['max'] * 1000:.2f})"
            f"  {stats['capture_bytes']['median']:.0f} bytes",
            flush=True,
        )
    return csv_path


def attribution_table(
    config: Mapping[str, Any],
    *,
    campaign_dir: Path,
    executions: int,
    judge_passes: int,
    team_runner: Optional[Any] = None,
) -> Path:
    """Judge paired executions and write accuracy.csv.

    Args:
        config:
            Experiment config mapping.
        campaign_dir:
            Campaign folder.
        executions:
            How many paired trajectories to run.
        judge_passes:
            How many times to judge each execution.
        team_runner:
            Callable that runs one paired execution.
            The addition team is used when this is omitted.

    Returns:
        Path of the written CSV file.
    """
    rows = run_accuracy_campaign(
        config["query"],
        config.get("plant") or {},
        campaign_dir=campaign_dir,
        executions=executions,
        judge_passes=judge_passes,
        judge=config.get("judge"),
        judge_runner=run_judges,
        team_runner=team_runner,
    )
    csv_path = write_rows(campaign_dir / "accuracy.csv", rows, ACCURACY_FIELDS)
    summary = summarise_accuracy(rows)
    update_summary(
        campaign_dir,
        "attribution",
        {
            "executions": executions,
            "judge_passes": judge_passes,
            "methods": summary,
        },
        config=_provenance(config, _repeat_counts(config)),
    )
    print(f"Attribution: {len(rows)} scored rows -> {csv_path}", flush=True)
    for method, views in summary.items():
        for view, stats in views.items():
            print(
                f"  {method:<14} {view:<3} who {stats['who_accuracy']:.2f}"
                f"  when {stats['when_accuracy']:.2f}"
                f"  tokens {stats['total_tokens']['median']:.0f}"
                f"  (n={stats['n']})",
                flush=True,
            )
    return csv_path


def _runners_for_team(team: str):
    """Return the cost and paired runners for one team.

    Args:
        team:
            Either addition or magentic_one.

    Returns:
        A capture runner and a paired-execution runner.
        Both are None for the addition team, which keeps the campaign defaults.

    Raises:
        ValueError:
            If team is unknown.
    """
    if team == "addition":
        return None, None
    if team == "magentic_one":
        from experiments.magentic_one.run import measure_magentic_capture, run_recorded

        return measure_magentic_capture, run_recorded
    raise ValueError(f"Unknown team {team!r}")


def main(argv: Optional[list[str]] = None) -> None:
    """Produce the cost table, the attribution table, or both.

    Figures are written when the chosen tables finish.

    Args:
        argv:
            Optional command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run the attribution experiments. "
            "The cost table repeats executions. "
            "The attribution table repeats judge passes over stored packs."
        )
    )
    parser.add_argument(
        "--table",
        choices=("cost", "accuracy", "both"),
        default="cost",
        help="Which table to produce. The default is the cost table.",
    )
    parser.add_argument(
        "--cost-repeats",
        type=int,
        default=None,
        help="Override repeats.cost from the config.",
    )
    parser.add_argument(
        "--executions",
        type=int,
        default=None,
        help="Override repeats.executions from the config.",
    )
    parser.add_argument(
        "--judge-passes",
        type=int,
        default=None,
        help="Override repeats.judge from the config.",
    )
    parser.add_argument(
        "--team",
        choices=("addition", "magentic_one"),
        default="addition",
        help="Team to run. addition is the default. magentic_one uses the stand-in specialists.",
    )
    parser.add_argument(
        "--campaign",
        default=None,
        help="Existing campaign folder to add results to.",
    )
    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        help="Optional YAML config (query, plant, repeats, judge, output_base).",
    )
    args = parser.parse_args(argv)

    config = load_yaml(_config_path(args.config))
    repeats = _repeat_counts(config)
    output_base = str(config.get("output_base", "./output"))
    capture_runner, team_runner = _runners_for_team(args.team)
    campaign_dir = (
        Path(args.campaign) if args.campaign else new_campaign_dir(output_base)
    )
    (campaign_dir / "runs").mkdir(parents=True, exist_ok=True)

    if args.table in {"cost", "both"}:
        capture_cost_table(
            config,
            campaign_dir=campaign_dir,
            repeats=args.cost_repeats or repeats["cost"],
            capture_runner=capture_runner,
        )
    if args.table in {"accuracy", "both"}:
        attribution_table(
            config,
            campaign_dir=campaign_dir,
            executions=args.executions or repeats["executions"],
            judge_passes=args.judge_passes or repeats["judge"],
            team_runner=team_runner,
        )
    written = render_campaign(campaign_dir)
    if written:
        print("Figures:", flush=True)
        for name, paths in written.items():
            for suffix, path in paths.items():
                print(f"  {name} ({suffix}) -> {path}", flush=True)
    print(f"Campaign folder: {campaign_dir}", flush=True)


if __name__ == "__main__":
    main()
