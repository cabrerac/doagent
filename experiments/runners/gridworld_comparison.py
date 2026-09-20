"""Compare gridworld storage conditions with one measured run per condition."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys

from examples.gridworld.session import load_config
from experiments._shared import write_summary
from experiments.gridworld.evaluate import evaluate_gridworld


def main() -> None:
    """Run NoOp, memory, and file conditions with all other settings fixed."""
    root = Path(__file__).resolve().parents[2]
    config_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else root / "examples" / "gridworld" / "config.yaml"
    )
    config = load_config(config_path)
    results = {
        storage: evaluate_gridworld(config, storage=storage)
        for storage in ("noop", "memory", "file")
    }
    file_result = results["file"]
    if not file_result.run_path:
        raise RuntimeError("File condition did not create a run folder.")
    summary_path = (
        Path(file_result.run_path) / "gridworld_comparison_summary.json"
    )
    write_summary(
        summary_path,
        {"runs": {key: asdict(value) for key, value in results.items()}},
    )
    print(f"Comparison summary written to {summary_path}")


if __name__ == "__main__":
    main()
