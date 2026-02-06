"""Plot reward series and action counts from a validation summary."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Dict, List
import csv


def _load_summary(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _plot_reward_series(
    series: List[Dict[str, float]],
    output_pdf: Path,
    output_png: Path,
) -> None:
    import matplotlib.pyplot as plt

    if not series:
        print("No reward series data to plot.")
        return
    agents = sorted({agent for item in series for agent in item.keys()})
    xs = list(range(1, len(series) + 1))
    for agent in agents:
        ys = [item.get(agent, 0.0) for item in series]
        plt.plot(xs, ys, label=agent)
    plt.xlabel("Round")
    plt.ylabel("Reward")
    plt.title("Reward per Round")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_pdf, format="pdf")
    plt.savefig(output_png, format="png", dpi=150)
    plt.close()


def _plot_action_counts(
    action_counts: Dict[str, Dict[str, int]],
    output_pdf: Path,
    output_png: Path,
) -> None:
    import matplotlib.pyplot as plt

    if not action_counts:
        print("No action count data to plot.")
        return
    agents = sorted(action_counts.keys())
    action_keys = sorted(
        {action for counts in action_counts.values() for action in counts.keys()},
        key=int,
    )
    width = 0.8 / max(len(agents), 1)
    xs = list(range(len(action_keys)))
    for idx, agent in enumerate(agents):
        counts = [action_counts[agent].get(action, 0) for action in action_keys]
        offset = (idx - (len(agents) - 1) / 2) * width
        plt.bar([x + offset for x in xs], counts, width=width, label=agent)
    plt.xticks(xs, action_keys)
    plt.xlabel("Action")
    plt.ylabel("Count")
    plt.title("Action Counts")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_pdf, format="pdf")
    plt.savefig(output_png, format="png", dpi=150)
    plt.close()


def _write_reward_series_csv(
    path: Path,
    series: List[Dict[str, float]],
    series_every: int,
) -> None:
    if not series:
        return
    agents = sorted({agent for item in series for agent in item.keys()})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["round"] + agents)
        for idx, item in enumerate(series, start=1):
            round_id = idx * max(series_every, 1)
            row = [round_id] + [item.get(agent, 0.0) for agent in agents]
            writer.writerow(row)


def _write_action_counts_csv(
    path: Path,
    action_counts: Dict[str, Dict[str, int]],
) -> None:
    if not action_counts:
        return
    agents = sorted(action_counts.keys())
    action_keys = sorted(
        {action for counts in action_counts.values() for action in counts.keys()},
        key=int,
    )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["action"] + agents)
        for action in action_keys:
            row = [action] + [action_counts[agent].get(action, 0) for agent in agents]
            writer.writerow(row)


def _plot_entropy(
    entropies: Dict[str, Dict[str, float]],
    output_pdf: Path,
    output_png: Path,
) -> None:
    import matplotlib.pyplot as plt

    if not entropies:
        print("No entropy data to plot.")
        return
    agents = sorted(entropies.keys())
    raw_values = [entropies[agent].get("raw", 0.0) for agent in agents]
    norm_values = [entropies[agent].get("normalized", 0.0) for agent in agents]
    xs = list(range(len(agents)))
    width = 0.35
    plt.bar([x - width / 2 for x in xs], raw_values, width=width, label="raw")
    plt.bar([x + width / 2 for x in xs], norm_values, width=width, label="normalized")
    plt.xticks(xs, agents)
    plt.xlabel("Agent")
    plt.ylabel("Entropy")
    plt.title("Action Entropy")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_pdf, format="pdf")
    plt.savefig(output_png, format="png", dpi=150)
    plt.close()


def _write_entropy_csv(
    path: Path,
    entropies: Dict[str, Dict[str, float]],
) -> None:
    if not entropies:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["agent", "raw", "normalized"])
        for agent in sorted(entropies.keys()):
            writer.writerow(
                [
                    agent,
                    entropies[agent].get("raw", 0.0),
                    entropies[agent].get("normalized", 0.0),
                ]
            )


def main() -> None:
    if len(sys.argv) > 1:
        summary_path = Path(sys.argv[1])
    else:
        summary_path = Path("output") / "push_validation_summary.json"
    if not summary_path.exists():
        print(
            "Summary file not found. Provide a path to a summary JSON."
        )
        return
    summary = _load_summary(summary_path)
    runs = summary.get("runs", {})
    if "in_memory" not in runs:
        print("No run metrics found in summary.")
        return
    run = runs["in_memory"]
    reward_series = run.get("reward_series", [])
    action_counts = run.get("action_counts", {})
    entropies = run.get("action_entropy", {})
    output_dir = summary_path.parent
    _plot_reward_series(
        reward_series,
        output_dir / "reward_series.pdf",
        output_dir / "reward_series.png",
    )
    _plot_action_counts(
        action_counts,
        output_dir / "action_counts.pdf",
        output_dir / "action_counts.png",
    )
    _plot_entropy(
        entropies,
        output_dir / "action_entropy.pdf",
        output_dir / "action_entropy.png",
    )
    _write_reward_series_csv(
        output_dir / "reward_series.csv",
        reward_series,
        int(run.get("series_every", 1)),
    )
    _write_action_counts_csv(
        output_dir / "action_counts.csv",
        action_counts,
    )
    _write_entropy_csv(
        output_dir / "action_entropy.csv",
        entropies,
    )
    print(f"Wrote CSV files to {output_dir}")


if __name__ == "__main__":
    main()
