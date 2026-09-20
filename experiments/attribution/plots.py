"""Draw the attribution experiment figures from the campaign CSV files.

From the repository root:

    python -m experiments.attribution.plots output/attribution_campaign_<stamp>

Figures go to the plots folder of the campaign.
PNG is for viewing.
PDF is for papers.
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from experiments.attribution.campaign import (
    LOOKUP_METHOD,
    summarise_accuracy,
    summarise_cost,
)

FIGURE_FORMATS = ("png", "pdf")

COST_NUMERIC = ("elapsed_seconds", "capture_bytes", "repeat")
ACCURACY_NUMERIC = (
    "who_match",
    "when_match",
    "both_match",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "execution",
)
CONDITION_ORDER = ("w", "t", "d0", "d1", "d2")
METHOD_ORDER = ("all_at_once", "step_by_step", "binary_search")
PACK_LABELS = {
    "w": "Who&When",
    "t": "TraceElephant",
    "d0": "DOAgent (level 0)",
    "d1": "DOAgent (level 1)",
    "d2": "DOAgent (level 2)",
}
PACK_SHORT = {
    "w": "W",
    "t": "T",
    "d0": "D0",
    "d1": "D1",
    "d2": "D2",
}
METHOD_LABELS = {
    "all_at_once": "All-at-once",
    "step_by_step": "Step-by-step",
    "binary_search": "Binary search",
    "lookup": "Lookup",
}


def _pack_label(name: str) -> str:
    """Return the paper name for one evidence pack.

    Args:
        name:
            Short pack id, such as w or d2.

    Returns:
        The display name used on bar charts.
    """
    return PACK_LABELS.get(name, name)


def _pack_short(name: str) -> str:
    """Return the short mark for one evidence pack.

    Args:
        name:
            Short pack id, such as w or d2.

    Returns:
        The compact mark used on scatter plots.
    """
    return PACK_SHORT.get(name, name.upper())


def _method_label(name: str) -> str:
    """Return the paper name for one judging method.

    Args:
        name:
            Stored method id.

    Returns:
        The display name used in legends.
    """
    return METHOD_LABELS.get(name, name.replace("_", " "))


def _method_order(names: Iterable[str]) -> List[str]:
    """Order judging methods as in Who&When, with lookup last.

    Args:
        names:
            Method names present in the data.

    Returns:
        Those names in a stable display order.
    """
    present = set(names)
    known = [name for name in METHOD_ORDER if name in present]
    extras = sorted(present - set(known) - {LOOKUP_METHOD})
    if LOOKUP_METHOD in present:
        extras.append(LOOKUP_METHOD)
    return known + extras


def _figure(width: float, height: float, panels: int = 1):
    """Create a figure that can be saved without a display.

    Type is a serif face close to the paper text.

    Args:
        width:
            Figure width in inches.
        height:
            Figure height in inches.
        panels:
            Number of side-by-side axes.

    Returns:
        The pyplot module and a figure with its axes.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "figure.titlesize": 12,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    return plt, plt.subplots(1, panels, figsize=(width, height))


def _save(
    plt,
    figure,
    output_path: str | Path,
    formats: Sequence[str],
) -> Dict[str, str]:
    """Write one figure in each requested format and close it.

    The extension of output_path is replaced.
    One base name produces one file per format.

    Args:
        plt:
            The pyplot module used to close the figure.
        figure:
            Figure to save.
        output_path:
            Base path. The suffix is replaced for each format.
        formats:
            File suffixes to write, such as png and pdf.

    Returns:
        Written path for each format.
    """
    base = Path(output_path).with_suffix("")
    base.parent.mkdir(parents=True, exist_ok=True)
    written: Dict[str, str] = {}
    for suffix in formats:
        path = base.with_suffix(f".{suffix}")
        figure.savefig(path, dpi=200, bbox_inches="tight")
        written[suffix] = str(path)
    plt.close(figure)
    return written


def load_rows(
    path: str | Path,
    numeric_fields: Sequence[str],
) -> List[Dict[str, Any]]:
    """Read one CSV, converting the measurement columns to numbers.

    Args:
        path:
            CSV file to read.
        numeric_fields:
            Column names to convert to int or float.

    Returns:
        One dict per row.
    """
    rows: List[Dict[str, Any]] = []
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for raw in csv.DictReader(handle):
            row: Dict[str, Any] = dict(raw)
            for field in numeric_fields:
                value = row.get(field)
                if value in (None, ""):
                    continue
                row[field] = float(value) if "." in str(value) else int(value)
            rows.append(row)
    return rows


def _ordered(names: Iterable[str]) -> List[str]:
    """Order evidence packs as Who&When, TraceElephant, then DOAgent logging levels.

    Args:
        names:
            Condition names present in the data.

    Returns:
        Those names in a stable display order.
    """
    present = list(names)
    known = [name for name in CONDITION_ORDER if name in present]
    return known + sorted(set(present) - set(known))


def render_capture_cost(
    rows: Sequence[Mapping[str, Any]],
    output_path: str | Path,
    *,
    formats: Sequence[str] = FIGURE_FORMATS,
) -> Dict[str, str]:
    """Draw capture time and capture size on disk for every evidence pack.

    Time is a strip of repeats with a median mark.
    Size is a bar at the median.

    Args:
        rows:
            Cost CSV rows.
        output_path:
            Base path for the written files.
        formats:
            File suffixes to write.

    Returns:
        Written path for each format.
    """
    summary = summarise_cost(rows)
    conditions = _ordered(summary)
    labels = [_pack_label(name) for name in conditions]
    sizes = [summary[name]["capture_bytes"]["median"] for name in conditions]
    times_ms: Dict[str, List[float]] = {name: [] for name in conditions}
    for row in rows:
        name = str(row["condition"])
        if name in times_ms:
            times_ms[name].append(float(row["elapsed_seconds"]) * 1000)

    plt, (figure, axes) = _figure(10.0, 4.0, panels=2)
    time_axis, size_axis = axes
    rng = random.Random(0)
    for index, name in enumerate(conditions):
        samples = times_ms[name]
        offsets = [index + rng.uniform(-0.12, 0.12) for _ in samples]
        time_axis.scatter(offsets, samples, color="#4c72b0", s=28, zorder=3)
        if samples:
            time_axis.hlines(
                statistics.median(samples),
                index - 0.22,
                index + 0.22,
                colors="#2a4d7a",
                linewidth=2,
                zorder=4,
            )
    time_axis.set_xticks(range(len(conditions)))
    time_axis.set_xticklabels(labels)
    time_axis.set_ylabel("Time (ms)")
    time_axis.set_title("Wall-clock time")
    size_axis.bar(labels, sizes, color="#dd8452")
    size_axis.set_ylabel("Size (bytes)")
    size_axis.set_title("Log size on disk")
    for axis in (time_axis, size_axis):
        axis.grid(axis="y", alpha=0.3)
        axis.set_axisbelow(True)
        axis.tick_params(axis="x", labelrotation=15)
    figure.suptitle("Capture cost of evidence packs")
    figure.tight_layout()
    return _save(plt, figure, output_path, formats)


def render_attribution_accuracy(
    rows: Sequence[Mapping[str, Any]],
    output_path: str | Path,
    *,
    formats: Sequence[str] = FIGURE_FORMATS,
) -> Dict[str, str]:
    """Draw who and when accuracy for every judging method and view.

    Lookup on D appears as its own group beside the judging methods.

    Args:
        rows:
            Accuracy CSV rows.
        output_path:
            Base path for the written files.
        formats:
            File suffixes to write.

    Returns:
        Written path for each format.
    """
    summary = summarise_accuracy(rows)
    methods = _method_order(summary)
    views = _ordered({view for views in summary.values() for view in views})
    titles = {
        "who_accuracy": "Agent-level accuracy",
        "when_accuracy": "Step-level accuracy",
    }

    plt, (figure, axes) = _figure(11.0, 4.5, panels=2)
    width = 0.8 / max(len(methods), 1)
    for panel, metric in zip(axes, ("who_accuracy", "when_accuracy")):
        for index, method in enumerate(methods):
            offsets = [
                position + index * width - 0.4 + width / 2
                for position in range(len(views))
            ]
            values = [
                summary[method].get(view, {}).get(metric, 0.0) for view in views
            ]
            panel.bar(offsets, values, width=width, label=_method_label(method))
        panel.set_xticks(range(len(views)))
        panel.set_xticklabels([_pack_label(view) for view in views])
        panel.set_ylim(0.0, 1.05)
        panel.set_ylabel("Accuracy")
        panel.set_title(titles[metric])
        panel.grid(axis="y", alpha=0.3)
        panel.set_axisbelow(True)
        panel.tick_params(axis="x", labelrotation=15)
    axes[0].legend()
    figure.suptitle("Failure attribution by evidence pack")
    figure.tight_layout()
    return _save(plt, figure, output_path, formats)


def render_tokens_against_accuracy(
    rows: Sequence[Mapping[str, Any]],
    output_path: str | Path,
    *,
    formats: Sequence[str] = FIGURE_FORMATS,
) -> Dict[str, str]:
    """Plot judge tokens against agent-level and step-level accuracy.

    Lookup is plotted at zero tokens.

    Args:
        rows:
            Accuracy CSV rows.
        output_path:
            Base path for the written files.
        formats:
            File suffixes to write.

    Returns:
        Written path for each format.
    """
    summary = summarise_accuracy(rows)
    plt, (figure, axes) = _figure(11.0, 4.5, panels=2)
    markers = ("o", "s", "^", "D", "v", "P")
    metrics = (
        ("who_accuracy", "Agent-level accuracy"),
        ("when_accuracy", "Step-level accuracy"),
    )
    for axis, (metric, ylabel) in zip(axes, metrics):
        for index, method in enumerate(_method_order(summary)):
            tokens = []
            accuracy = []
            for view in _ordered(summary[method]):
                stats = summary[method][view]
                tokens.append(stats["total_tokens"]["median"])
                accuracy.append(stats[metric])
                axis.annotate(
                    _pack_short(view),
                    (tokens[-1], accuracy[-1]),
                    textcoords="offset points",
                    xytext=(6, 4),
                    fontsize=8,
                )
            axis.scatter(
                tokens,
                accuracy,
                label=_method_label(method),
                marker=markers[index % len(markers)],
                s=60,
            )
        axis.set_xlabel("Judge tokens (median per pass)")
        axis.set_ylabel(ylabel)
        axis.set_ylim(-0.05, 1.05)
        axis.grid(alpha=0.3)
        axis.set_axisbelow(True)
    axes[0].legend()
    figure.suptitle("Attribution quality against cost (tokens)")
    figure.tight_layout()
    return _save(plt, figure, output_path, formats)


def render_campaign(
    campaign_dir: str | Path,
    *,
    formats: Sequence[str] = FIGURE_FORMATS,
) -> Dict[str, Dict[str, str]]:
    """Draw every figure the campaign has data for.

    Args:
        campaign_dir:
            Campaign folder that holds cost.csv and accuracy.csv.
        formats:
            File suffixes to write.

    Returns:
        Written paths keyed by figure name, then by format.
    """
    campaign = Path(campaign_dir)
    plots_dir = campaign / "plots"
    written: Dict[str, Dict[str, str]] = {}

    cost_csv = campaign / "cost.csv"
    if cost_csv.is_file():
        rows = load_rows(cost_csv, COST_NUMERIC)
        if rows:
            written["capture_cost"] = render_capture_cost(
                rows,
                plots_dir / "capture_cost",
                formats=formats,
            )

    accuracy_csv = campaign / "accuracy.csv"
    if accuracy_csv.is_file():
        rows = load_rows(accuracy_csv, ACCURACY_NUMERIC)
        if rows:
            written["attribution_accuracy"] = render_attribution_accuracy(
                rows,
                plots_dir / "attribution_accuracy",
                formats=formats,
            )
            written["tokens_against_accuracy"] = render_tokens_against_accuracy(
                rows,
                plots_dir / "tokens_against_accuracy",
                formats=formats,
            )
    return written


def main(argv: Optional[list[str]] = None) -> None:
    """Draw the figures for one campaign folder.

    Args:
        argv:
            Optional command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Plot attribution campaign results from their CSV files"
    )
    parser.add_argument(
        "campaign_dir",
        help="Path to output/attribution_campaign_<stamp>",
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        default=list(FIGURE_FORMATS),
        help="File formats to write. Default: png pdf.",
    )
    args = parser.parse_args(argv)
    written = render_campaign(args.campaign_dir, formats=args.formats)
    if not written:
        print("No cost.csv or accuracy.csv found in that campaign folder.")
        return
    for name, paths in written.items():
        for suffix, path in paths.items():
            print(f"{name} ({suffix}) -> {path}")


if __name__ == "__main__":
    main()
