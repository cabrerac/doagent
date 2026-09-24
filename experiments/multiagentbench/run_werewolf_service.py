"""Run the published Werewolf game as a service system.

The game code, roles, and prompts come from the MARBLE checkout.
Agents act only on events addressed to them.
Both sides use one university model.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import types
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import yaml

from examples._shared.llm_client import PROXY_BASE_URL, proxy_api_key
from experiments.multiagentbench.recover import compare, logs_for_phases, write_gap
from experiments.multiagentbench.truth import read_truth, write_truth
from experiments.multiagentbench.werewolf_truth import day_phase, night_phase

MARBLE_ROOT = Path(__file__).resolve().parent / "MARBLE"
PUBLISHED_CONFIG = (
    MARBLE_ROOT
    / "marble"
    / "configs"
    / "test_config"
    / "werewolf_config"
    / "werewolf_config.yaml"
)
SERVICE_MODEL = "Qwen/Qwen3.8-27B-FP8"


def main(argv: Optional[list[str]] = None) -> None:
    """Load their Werewolf config, point it at the proxy, and start one game.

    Args:
        argv:
            Optional command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Published Werewolf, service messaging, university model"
    )
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--name", default="werewolf_service")
    args = parser.parse_args(argv)
    if args.rounds < 1:
        raise ValueError("Rounds must be at least 1.")
    config_path = _write_service_config()
    WerewolfEnv = _load_werewolf_env()
    from marble.agent.werewolf_agent import WerewolfAgent

    _install_call_retry(WerewolfAgent)

    previous = Path.cwd()
    os.chdir(MARBLE_ROOT)
    try:
        for index in range(args.rounds):
            game_name = args.name if args.rounds == 1 else f"{args.name}_{index + 1}"
            env = WerewolfEnv(name=game_name, config_path=str(config_path))
            _attach_truth(env)
            print(f"Starting game: {game_name}", flush=True)
            try:
                env.start()
            finally:
                _write_game_gap(env)
    finally:
        os.chdir(previous)


def call_with_retry(
    operation: Callable[[], Any],
    attempts: int = 5,
    pause: Callable[[float], None] = time.sleep,
    base_delay: float = 20,
) -> Any:
    """Call operation again after a failure.

    Args:
        operation: The model call to attempt.
        attempts: How many times to try before raising.
        pause: Wait function used between attempts.
        base_delay: Seconds to wait after the first failure.
            Later waits double, up to 60 seconds.

    Returns:
        The value returned by operation.

    Raises:
        Exception: The last failure, after every attempt has failed.
    """
    delay = base_delay
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            if attempt == attempts:
                raise
            print(
                f"Model call failed ({attempt}/{attempts}): {exc} Waiting {delay}s.",
                flush=True,
            )
            pause(delay)
            delay = min(delay * 2, 60)
    raise RuntimeError("model call was not attempted")


def _install_call_retry(agent_cls: Any) -> None:
    """Retry the agent's model call after its own attempts are exhausted.

    Args:
        agent_cls: Agent class whose model method should be wrapped.
    """
    original = agent_cls.gpt_tool_call

    def gpt_tool_call(self: Any, messages: Any, tools: Any) -> Any:
        return call_with_retry(lambda: original(self, messages, tools))

    agent_cls.gpt_tool_call = gpt_tool_call


def _attach_truth(env: Any) -> None:
    """Write a truth phase after each night and each day.

    Args:
        env: A constructed Werewolf environment.
    """
    document: Dict[str, Any] = {"phases": []}
    path = Path(env.shared_memory_path).with_name("truth.json")
    original_night = env.night
    original_day = env.day

    def night() -> None:
        original_night()
        document["phases"].append(night_phase(env.shared_memory))
        write_truth(path, document)

    def day() -> None:
        original_day()
        document["phases"].append(day_phase(env.shared_memory))
        write_truth(path, document)

    env.night = night
    env.day = day


def _write_game_gap(env: Any) -> None:
    """Score the finished phases from the participant logs.

    Args:
        env: The Werewolf environment for this game.
    """
    directory = Path(env.shared_memory_path).parent
    truth_path = directory / "truth.json"
    if not truth_path.is_file():
        return
    truth = read_truth(truth_path)
    gaps = compare(truth, logs_for_phases(directory, truth["phases"]))
    write_gap(directory / "gap.json", gaps)
    print(
        f"entropy_gap={gaps['entropy_gap']} modularity_gap={gaps['modularity_gap']}",
        flush=True,
    )


def _write_service_config() -> Path:
    """Copy their yaml and set the university model on both sides.

    Returns:
        Path of the generated config, next to the MARBLE checkout.

    Raises:
        FileNotFoundError:
            If the MARBLE checkout or their yaml is missing.
    """
    if not PUBLISHED_CONFIG.is_file():
        raise FileNotFoundError(
            "MARBLE Werewolf config is missing. "
            "Clone https://github.com/ulab-uiuc/MARBLE into "
            f"{MARBLE_ROOT}."
        )
    published = yaml.safe_load(PUBLISHED_CONFIG.read_text(encoding="utf-8"))
    key = proxy_api_key()
    base_url = PROXY_BASE_URL.rstrip("/") + "/v1"
    for side in ("villager_config", "werewolf_config"):
        block: Dict[str, Any] = dict(published.get(side) or {})
        block["base_url"] = base_url
        block["api_key"] = key
        block["model_name"] = SERVICE_MODEL
        published[side] = block
    published["openai_api_key"] = key
    published["system_prompt_path"] = (
        "marble/agent/werewolf_prompts/system_prompt.yaml"
    )
    out = MARBLE_ROOT / "werewolf_service.generated.yaml"
    out.write_text(yaml.safe_dump(published, sort_keys=False), encoding="utf-8")
    return out


def _load_werewolf_env() -> Any:
    """Import the Werewolf environment class.

    Returns:
        The WerewolfEnv class.

    Raises:
        FileNotFoundError:
            If the checkout is missing.
    """
    if not MARBLE_ROOT.is_dir():
        raise FileNotFoundError(
            f"MARBLE checkout not found at {MARBLE_ROOT}."
        )
    root = str(MARBLE_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    _register_package("marble", MARBLE_ROOT / "marble")
    _register_package("marble.agent", MARBLE_ROOT / "marble" / "agent")
    _register_package("marble.utils", MARBLE_ROOT / "marble" / "utils")
    _register_package(
        "marble.environments", MARBLE_ROOT / "marble" / "environments"
    )
    from marble.environments.werewolf_env import WerewolfEnv

    return WerewolfEnv


def _register_package(name: str, path: Path) -> None:
    """Register one package so its init file is not executed.

    Args:
        name:
            Dotted module name.
        path:
            Directory that holds the package.
    """
    if name in sys.modules:
        return
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    module.__package__ = name
    sys.modules[name] = module


if __name__ == "__main__":
    main()
