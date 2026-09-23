"""Run the Magentic-One team and write gold, collector packs, and session views.

From the repository root:

    python -m experiments.magentic_one.run
    python -m experiments.magentic_one.run --observe

A live invocation builds the four AutoGen specialists.
Tests can pass a stand-in map instead.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Iterable, Optional

from experiments.attribution.baselines.protocol import StepCollector
from experiments.attribution.projections import write_attribution_artifacts
from experiments._shared import EvaluationResult, output_bytes_from_path
from experiments.magentic_one.query import FROZEN_QUERY
from experiments.magentic_one.specialists import build_specialists
from experiments.magentic_one.team import run_magentic_team


def load_yaml(path: Path) -> Dict[str, Any]:
    """Load a mapping from a YAML file.

    Args:
        path:
            YAML file to read.

    Returns:
        The mapping stored in the file.

    Raises:
        ImportError:
            If PyYAML is not installed.
        ValueError:
            If the file does not contain a mapping.
    """
    try:
        import yaml
    except ImportError as exc:
        raise ImportError("PyYAML is required to load config.yaml") from exc
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return data


def run_recorded(
    query: Dict[str, Any] | None = None,
    plant: Dict[str, Any] | None = None,
    collectors: Iterable[StepCollector] = (),
    specialists: Dict[str, Any] | None = None,
    *,
    storage: str = "file",
    output_base: str = "./output",
    logging_level: int = 2,
) -> Dict[str, Any]:
    """Run the team and write gold, packs, and session views when a run folder exists.

    Args:
        query:
            Query id and text.
            The frozen capital query is used when this is omitted.
        plant:
            Optional wrong_fact.
            The mode must be accept_last.
        collectors:
            Observers notified after each decision.
        specialists:
            Long-lived agents keyed by agent id.
            Stand-in policies are used when this is omitted.
        storage:
            Either memory or file.
        output_base:
            Root folder for file-backed runs.
        logging_level:
            Session recording level, 0, 1, or 2.

    Returns:
        The team result, plus artifact_paths for files written under the run folder.
    """
    watchers = tuple(collectors)
    result = run_magentic_team(
        query,
        plant,
        watchers,
        specialists,
        storage=storage,
        output_base=output_base,
        logging_level=logging_level,
    )
    written: Dict[str, str] = {}
    run_path = result["session"].run_path
    if run_path:
        root = Path(run_path)
        gold_path = root / "gold.json"
        gold_path.write_text(
            json.dumps(result["gold"], indent=2) + "\n",
            encoding="utf-8",
        )
        written["gold"] = str(gold_path)
        analysis = root / "analysis" / "attribution"
        for collector in watchers:
            written[collector.name] = collector.write(analysis / collector.filename)
        written.update(write_attribution_artifacts(result["session"], root))
    result["artifact_paths"] = written
    return result


def measure_magentic_capture(
    query: Dict[str, Any],
    plant: Dict[str, Any],
    condition: str,
    *,
    output_base: str,
) -> EvaluationResult:
    """Time one Magentic-One capture condition.

    W and T time the direct host and one collector pack.
    D0, D1, and D2 time a Session run at that logging level.
    The stand-in specialists run in either case.

    Args:
        query:
            Query id and text.
        plant:
            Planted wrong_fact.
            The mode must be accept_last.
        condition:
            One of w, t, d0, d1, or d2.
        output_base:
            Folder for that execution's files.

    Returns:
        Elapsed time, bytes on disk, and the run path.

    Raises:
        ValueError:
            If condition is not a known capture name.
    """
    if condition in ("w", "t"):
        return _measure_direct_capture(query, plant, condition, output_base)
    if condition in ("d0", "d1", "d2"):
        return _measure_session_capture(query, plant, condition, output_base)
    raise ValueError(f"Unknown capture condition {condition!r}")


def _measure_direct_capture(
    query: Dict[str, Any],
    plant: Dict[str, Any],
    condition: str,
    output_base: str,
) -> EvaluationResult:
    """Time the direct host and one collector pack.

    Args:
        query:
            Query id and text.
        plant:
            Planted wrong_fact.
        condition:
            Either w or t.
        output_base:
            Folder for that execution's files.

    Returns:
        Elapsed time and the size of the written pack.
    """
    from datetime import datetime, timezone

    from experiments.attribution.baselines import OutputLogCollector, StepIOCollector
    from experiments.magentic_one.direct import run_direct_team

    collector = OutputLogCollector() if condition == "w" else StepIOCollector()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    run_dir = Path(output_base) / f"magentic_{condition}_cost_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    pack_path = run_dir / collector.filename
    started = perf_counter()
    result = run_direct_team(query, plant, collectors=(collector,))
    collector.write(pack_path)
    elapsed = perf_counter() - started
    gold_path = run_dir / "gold.json"
    gold_path.write_text(
        json.dumps(result["gold"], indent=2) + "\n",
        encoding="utf-8",
    )
    return EvaluationResult(
        condition={"scenario": "magentic_one", "capture": condition},
        task_metrics={
            "gold_who": result["gold"].get("gold_who"),
            "gold_when": result["gold"].get("gold_when"),
        },
        elapsed_seconds=elapsed,
        output_bytes=pack_path.stat().st_size,
        run_id=None,
        run_path=str(run_dir),
    )


def _measure_session_capture(
    query: Dict[str, Any],
    plant: Dict[str, Any],
    condition: str,
    output_base: str,
) -> EvaluationResult:
    """Time a Session run at one logging level.

    Args:
        query:
            Query id and text.
        plant:
            Planted wrong_fact.
        condition:
            One of d0, d1, or d2.
        output_base:
            Folder for that execution's files.

    Returns:
        Elapsed time and the size of the records folder.
    """
    started = perf_counter()
    result = run_recorded(
        query,
        plant,
        storage="file",
        output_base=output_base,
        logging_level=int(condition[1]),
    )
    elapsed = perf_counter() - started
    session = result["session"]
    records_path = None
    if session.run_path:
        records_path = Path(session.run_path) / "records"
    return EvaluationResult(
        condition={
            "scenario": "magentic_one",
            "capture": condition,
            "logging_level": int(condition[1]),
        },
        task_metrics={
            "gold_who": result["gold"].get("gold_who"),
            "gold_when": result["gold"].get("gold_when"),
        },
        elapsed_seconds=elapsed,
        output_bytes=output_bytes_from_path(records_path),
        run_id=session.run_id,
        run_path=str(session.run_path) if session.run_path else None,
    )


def live_specialists(model: str) -> Dict[str, Any]:
    """Build the four AutoGen specialists for one live run.

    Args:
        model:
            OpenAI model name passed to the shared client.

    Returns:
        Specialists keyed by agent id.

    Raises:
        ImportError:
            If the magentic-one packages are not installed.
        RuntimeError:
            If no OpenAI API key is available after loading .env.
    """
    from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
    from autogen_ext.models.openai import OpenAIChatCompletionClient

    from examples._shared.env_file import load_dotenv

    load_dotenv()
    client = OpenAIChatCompletionClient(model=model, api_key=_openai_api_key())
    executor = LocalCommandLineCodeExecutor()
    return build_specialists(client, executor)


def _openai_api_key() -> str:
    """Return the OpenAI key from the process environment.

    Returns:
        The value of DOAGENT_OPENAI_API_KEY, or OPENAI_API_KEY when that is absent.

    Raises:
        RuntimeError:
            If neither variable is set.
    """
    key = os.environ.get("DOAGENT_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError(
            "No OpenAI API key found. Set OPENAI_API_KEY or DOAGENT_OPENAI_API_KEY."
        )
    return key


def main(argv: Optional[list[str]] = None) -> None:
    """Load the config, run the live team, and print the written paths.

    Args:
        argv:
            Optional command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Magentic-One team on a Session, with accept-last gold"
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).with_name("config.yaml")),
        help="YAML file with the query, the plant, and the output folder",
    )
    parser.add_argument("--storage", choices=("file", "memory"), default=None)
    parser.add_argument(
        "--observe",
        action="store_true",
        help="Attach observe-only W and T collectors on this run.",
    )
    args = parser.parse_args(argv)
    cfg = load_yaml(Path(args.config))
    collectors: list[StepCollector] = []
    if args.observe:
        from experiments.attribution.baselines import (
            OutputLogCollector,
            StepIOCollector,
        )

        collectors = [OutputLogCollector(), StepIOCollector()]
    logging_level = int((cfg.get("run_config") or {}).get("logging_level", 2))
    result = run_recorded(
        cfg.get("query") or FROZEN_QUERY,
        cfg.get("plant") or {},
        collectors,
        live_specialists(str(cfg.get("model", "gpt-4o"))),
        storage=args.storage or str(cfg.get("storage", "file")),
        output_base=str(cfg.get("output_base", "./output")),
        logging_level=logging_level,
    )
    for name, path in result["artifact_paths"].items():
        print(f"{name} written to {path}")


if __name__ == "__main__":
    main()
