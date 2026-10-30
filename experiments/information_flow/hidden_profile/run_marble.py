"""Run Hidden Profile through MARBLE agents and an engine."""

from __future__ import annotations

import argparse
import json
import logging
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

import yaml

from experiments.information_flow.hidden_profile.access import component_names
from experiments.information_flow.hidden_profile.marble_support import prepare_marble

prepare_marble()

from marble.configs.config import Config

from experiments.information_flow.hidden_profile.marble_engine import (
    HiddenProfileEngine,
)
from experiments.information_flow.hidden_profile.rules import HiddenProfileRules
from experiments.information_flow.hidden_profile.service_trace import TRACE_NAME

CONFIG_PATH = Path(__file__).resolve().parent / "hidden_profile_config.yaml"
OUTPUT_BASE = Path(__file__).resolve().parent / "hidden_profile_marble_runs"
_CLOCK = re.compile(r"^\[[^\]]*\]")


def run_marble(
    seed: int = 0,
    output_base: str | Path | None = None,
    config_path: str | Path | None = None,
    allocation: Mapping[str, Sequence[str]] | None = None,
    condition: str | None = None,
    names: str | Sequence[str] | None = None,
) -> HiddenProfileRules:
    """Load the MARBLE config, play one episode, and write the chosen view.

    With no view, every component log is written and the structured file is written beside them.
    S1 writes one named log.
    Sk writes the named logs.
    Sall writes every component log.
    Sstructured writes only the structured file.

    Args:
        seed: Integer seed for the private-fact deal.
        output_base: Directory that receives the log files.
        config_path: MARBLE configuration file.
            Defaults to the reference config beside this module.
        allocation: Optional private-fact ids already assigned to each agent.
            When provided, the seed only labels the episode.
        condition: Recording view.
            None writes every component log and the structured file.
        names: Log file names for S1 or Sk.

    Returns:
        The rules object that played the episode.

    Raises:
        ValueError: The view or the name list is not valid.
    """
    folder = Path(output_base) if output_base is not None else OUTPUT_BASE
    folder.mkdir(parents=True, exist_ok=True)
    selected, write_trace = _view_files(condition, names)
    document = yaml.safe_load(Path(config_path or CONFIG_PATH).read_text(encoding="utf-8"))
    engine = HiddenProfileEngine(Config(document))
    log_dir = folder / "logs"
    handlers = _attach_logs(engine, log_dir, selected)
    trace_path = log_dir / TRACE_NAME if write_trace else None
    try:
        engine.start(seed, allocation, trace_path)
    finally:
        _detach_logs(handlers)
    return engine.environment.rules


def log_body(path: str | Path) -> str:
    """Return one component log with the leading clock removed from each line.

    Args:
        path: Path of one component log.

    Returns:
        The log text without the clock at the start of each line.
    """
    lines = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        lines.append(_CLOCK.sub("", line, count=1))
    return "\n".join(lines)


def trace_body(path: str | Path) -> tuple[dict[str, object], ...]:
    """Return structured lines with the clock removed.

    Args:
        path: Path of the structured trace.

    Returns:
        One mapping per line, without the timestamp.
    """
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        row = json.loads(line)
        row.pop("timestamp", None)
        rows.append(row)
    return tuple(rows)


def _view_files(
    condition: str | None,
    names: str | Sequence[str] | None,
) -> tuple[tuple[str, ...] | None, bool]:
    """Return the log names to write, and whether to write the structured file."""
    if condition is None:
        if names is not None:
            raise ValueError("names need a recording condition")
        return None, True
    if condition == "Sstructured":
        if names is not None:
            raise ValueError("Sstructured takes no names")
        return (), True
    return component_names(condition, names), False


def _attach_logs(
    engine: HiddenProfileEngine,
    log_dir: Path,
    names: tuple[str, ...] | None,
) -> list[tuple[logging.Logger, logging.Handler]]:
    """Give each selected component a log file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    loggers = [engine.logger, engine.environment.logger]
    loggers.extend(agent.logger for agent in engine.agents)
    attached = []
    for logger in loggers:
        filename = f"{logger.name}.log"
        if names is not None and filename not in names:
            continue
        path = log_dir / filename
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
        )
        logger.addHandler(handler)
        attached.append((logger, handler))
    return attached


def _detach_logs(
    attached: list[tuple[logging.Logger, logging.Handler]],
) -> None:
    """Close the log files opened for one run."""
    for logger, handler in attached:
        logger.removeHandler(handler)
        handler.close()


def main() -> None:
    """Run one episode from the command line."""
    parser = argparse.ArgumentParser(description="Run Hidden Profile through MARBLE.")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output-base", type=Path, default=OUTPUT_BASE)
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--condition", default=None)
    parser.add_argument("--log", action="append", dest="names")
    args = parser.parse_args()
    run_marble(args.seed, args.output_base, args.config, condition=args.condition, names=args.names)


if __name__ == "__main__":
    main()
