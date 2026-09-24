"""Run the log 36 question with a live WebSurfer.

From the repository root:

    python -m experiments.magentic_one.run_log36
    python -m experiments.magentic_one.run_log36 --observe

The orchestrator decides when to stop.
Gold who and when are left empty for later labeling.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict, Optional

from experiments.magentic_one.free_loop import run_free_team
from experiments.magentic_one.log36 import LOG36_QUERY, MAX_STALLS, MAX_TURNS
from experiments.magentic_one.run import load_yaml, proxy_chat_client


def main(argv: Optional[list[str]] = None) -> None:
    """Load the config, run the live loop, and print the written paths.

    Args:
        argv:
            Optional command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Log 36 on a Session, with a live WebSurfer"
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).with_name("log36.yaml")),
        help="YAML file with the question, the round cap, and the output folder",
    )
    parser.add_argument(
        "--observe",
        action="store_true",
        help="Attach observe-only W and T collectors on this run.",
    )
    parser.add_argument("--max-turns", type=int, default=None)
    args = parser.parse_args(argv)
    cfg = load_yaml(Path(args.config))
    query = cfg.get("query") or LOG36_QUERY
    collectors = _collectors(args.observe)
    client = proxy_chat_client(
        str(cfg.get("model") or "moonshotai/Kimi-K3"),
        str(cfg.get("base_url") or "") or None,
    )
    web = _web_surfer(client)
    try:
        result = run_free_team(
            query,
            model_client=client,
            web_surfer=web,
            collectors=collectors,
            max_turns=int(args.max_turns or cfg.get("max_turns") or MAX_TURNS),
            max_stalls=int(cfg.get("max_stalls") or MAX_STALLS),
            storage=str(cfg.get("storage") or "file"),
            output_base=str(cfg.get("output_base") or "./output"),
            logging_level=int((cfg.get("run_config") or {}).get("logging_level", 2)),
        )
        written = result.get("artifact_paths") or {}
    finally:
        closer = getattr(client, "close", None)
        if callable(closer):
            closer()
    for name, path in written.items():
        print(f"{name} written to {path}")


def _collectors(observe: bool) -> list[Any]:
    """Build the optional W and T collectors.

    Args:
        observe:
            True when the packs should be written.

    Returns:
        The collectors, or an empty list.
    """
    if not observe:
        return []
    from experiments.attribution.baselines import OutputLogCollector, StepIOCollector

    return [OutputLogCollector(), StepIOCollector()]


def _web_surfer(model_client: Any) -> Any:
    """Build one headless WebSurfer.

    Args:
        model_client:
            Proxy client shared with the orchestrator.

    Returns:
        The browser agent.

    Raises:
        ImportError:
            If the magentic-one extra is not installed.
    """
    try:
        from autogen_ext.agents.web_surfer import MultimodalWebSurfer
    except ImportError as exc:
        raise ImportError(
            "Install the magentic-one extra to construct WebSurfer."
        ) from exc
    return MultimodalWebSurfer("WebSurfer", model_client=model_client, headless=True)


if __name__ == "__main__":
    main()
