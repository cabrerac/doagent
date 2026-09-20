"""Compare push storage conditions with one measured run per condition."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from experiments._shared import write_summary
from experiments.push.evaluate import evaluate_push


def main() -> None:
    """Run memory and file conditions with the same seed and policies."""
    results = {
        storage: evaluate_push(storage=storage)
        for storage in ("memory", "file")
    }
    file_result = results["file"]
    if not file_result.run_path:
        raise RuntimeError("File condition did not create a run folder.")
    summary_path = Path(file_result.run_path) / "push_comparison_summary.json"
    write_summary(
        summary_path,
        {"runs": {key: asdict(value) for key, value in results.items()}},
    )
    print(f"Comparison summary written to {summary_path}")


if __name__ == "__main__":
    main()
