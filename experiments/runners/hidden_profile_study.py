"""Run the Hidden Profile study into one timestamped folder.

From the repository root:

    python -m experiments.runners.hidden_profile_study
    python -m experiments.runners.hidden_profile_study --deals 0
    python -m experiments.runners.hidden_profile_study --logging-level 1
    python -m experiments.runners.hidden_profile_study --output-base output

Each run writes output/hidden_profile_YYYYMMDD_HHMMSS.
The episode runners play each selected deal once.
The score and the figures are then drawn from those files.
A later run leaves the earlier folder in place.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from experiments.information_flow.hidden_profile.study import run_study


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Play the study and print the folder.

    Args:
        argv: Optional command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Run the Hidden Profile study into one timestamped folder."
    )
    parser.add_argument(
        "--output-base",
        type=Path,
        default=Path("output"),
        help="Parent directory. The default is output.",
    )
    parser.add_argument(
        "--deals",
        default=None,
        help="Comma-separated deal indexes. The default is every deal.",
    )
    parser.add_argument(
        "--logging-level",
        action="append",
        type=int,
        dest="logging_levels",
        help="Session level to keep. Repeat for more than one. The default is 0, 1, and 2.",
    )
    parser.add_argument(
        "--stamp",
        default=None,
        help="Folder timestamp YYYYMMDD_HHMMSS. The current UTC time is the default.",
    )
    args = parser.parse_args(argv)
    deals = None
    if args.deals is not None:
        deals = tuple(int(item) for item in args.deals.split(",") if item != "")
    levels = tuple(args.logging_levels) if args.logging_levels else (0, 1, 2)
    folder = run_study(
        args.output_base,
        stamp=args.stamp,
        deals=deals,
        logging_levels=levels,
    )
    print(f"Study folder: {folder}", flush=True)


if __name__ == "__main__":
    main()
