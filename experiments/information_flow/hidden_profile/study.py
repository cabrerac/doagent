"""Play Hidden Profile once and score the saved files.

Each selected deal is written under output/hidden_profile_YYYYMMDD_HHMMSS.
Session levels go through the DOAgent runner.
The MARBLE logs go through the MARBLE runner.
The score, the figures, and the campaign record are read back from those files.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from experiments.information_flow.hidden_profile.breakdown import plot_breakdown
from experiments.information_flow.hidden_profile.campaign import close_campaign
from experiments.information_flow.hidden_profile.recovery import plot_recovery
from experiments.information_flow.hidden_profile.curves import recover_saved_curves
from experiments.information_flow.hidden_profile.reference import reference_report
from experiments.information_flow.hidden_profile.rules import (
    DEFAULT_CONFIG,
    HiddenProfileConfig,
)
from experiments.information_flow.hidden_profile.run_doagent import run_session
from experiments.information_flow.hidden_profile.run_marble import run_marble
from experiments.information_flow.hidden_profile.score import score_saved

_STAMP = re.compile(r"^\d{8}_\d{6}$")


def new_study_dir(
    output_base: str | Path,
    *,
    stamp: str | None = None,
) -> Path:
    """Create one timestamped study folder.

    Args:
        output_base: Parent directory for the study folder.
        stamp: Folder name suffix.
            The current UTC time is used when this is omitted.

    Returns:
        Path of the new study folder.

    Raises:
        ValueError: The stamp is not a UTC timestamp.
        FileExistsError: That study folder already exists.
    """
    marker = stamp or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    if _STAMP.fullmatch(marker) is None:
        raise ValueError("stamp must look like YYYYMMDD_HHMMSS")
    folder = Path(output_base) / f"hidden_profile_{marker}"
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def run_study(
    output_base: str | Path = "output",
    *,
    stamp: str | None = None,
    deals: Sequence[int] | None = None,
    logging_levels: Sequence[int] = (0, 1, 2),
    config: HiddenProfileConfig = DEFAULT_CONFIG,
) -> Path:
    """Play the selected deals once and write the score and the figures.

    Args:
        output_base: Parent directory for the timestamped folder.
        stamp: Folder name suffix.
            The current UTC time is used when this is omitted.
        deals: Deal indexes to play.
            Every enumerated deal is played when this is omitted.
        logging_levels: Session logging levels to keep.
            Each level is 0, 1, or 2.
        config: Hidden profile configuration.

    Returns:
        Path of the study folder.

    Raises:
        ValueError: A deal index or a logging level is not valid.
        FileExistsError: That study folder already exists.
    """
    report = reference_report(config)
    indexes = selected_deals(len(report.deals), deals)
    levels = selected_levels(logging_levels)
    folder = new_study_dir(output_base, stamp=stamp)
    _write_settings(folder, indexes, levels, config)
    for index in indexes:
        allocation = dict(report.deals[index].allocation)
        deal_folder = folder / f"deal-{index}"
        for level in levels:
            run_session(
                index,
                level,
                deal_folder / f"D{level}",
                config,
                allocation,
            )
        run_marble(index, deal_folder / "marble", allocation=allocation)
    score_saved(folder, indexes, config, levels)
    recover_saved_curves(folder, indexes, config, levels)
    plot_breakdown(folder, config, indexes, levels)
    plot_recovery(folder, config, indexes, levels)
    close_campaign(folder, config, indexes, levels)
    return folder


def selected_deals(count: int, deals: Sequence[int] | None) -> tuple[int, ...]:
    """Return the deal indexes a study will play.

    Args:
        count: How many enumerated deals exist.
        deals: Requested indexes.
            Every index is returned when this is omitted.

    Returns:
        Deal indexes in the requested order.

    Raises:
        ValueError: An index is missing, repeated, or out of range.
    """
    if deals is None:
        return tuple(range(count))
    chosen = tuple(deals)
    if (
        not chosen
        or any(isinstance(index, bool) or not isinstance(index, int) for index in chosen)
        or any(index < 0 or index >= count for index in chosen)
        or len(set(chosen)) != len(chosen)
    ):
        raise ValueError("deals must be deal indexes")
    return chosen


def selected_levels(logging_levels: Sequence[int]) -> tuple[int, ...]:
    """Return the session levels a study will keep.

    Args:
        logging_levels: Requested levels.

    Returns:
        Levels 0, 1, and 2, in ascending order.

    Raises:
        ValueError: A level is missing, repeated, or not 0, 1, or 2.
    """
    chosen = tuple(logging_levels)
    if (
        not chosen
        or any(isinstance(level, bool) or level not in (0, 1, 2) for level in chosen)
        or len(set(chosen)) != len(chosen)
    ):
        raise ValueError("logging_level must be 0, 1, or 2")
    return tuple(sorted(chosen))


def _write_settings(
    folder: Path,
    deals: Sequence[int],
    logging_levels: Sequence[int],
    config: HiddenProfileConfig,
) -> None:
    """Write the settings used for this study folder."""
    payload = {
        "stamp": folder.name.removeprefix("hidden_profile_"),
        "deals": list(deals),
        "logging_levels": list(logging_levels),
        "agents": list(config.agents),
        "horizon": config.horizon,
        "options": list(config.options),
    }
    (folder / "study.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
