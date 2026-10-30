"""Load the MARBLE base classes without the model client."""

from __future__ import annotations

import importlib.util
import logging
import sys
import types
from pathlib import Path

MARBLE_ROOT = Path(__file__).resolve().parents[2] / "multiagentbench" / "MARBLE"
PACKAGE_ROOT = MARBLE_ROOT / "marble"
_READY = False


def prepare_marble() -> None:
    """Put the MARBLE checkout on the import path and load its base classes.

    The agent module imports a model client and every bundled environment.
    This loader supplies the base environment and the base agent only.
    The vendored engine module is left unloaded because its evaluator file does not parse.
    A language model is not called.
    """
    global _READY
    if _READY:
        return
    root = str(MARBLE_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    _stub_model_imports()
    _package("marble", PACKAGE_ROOT)
    environments = _package("marble.environments", PACKAGE_ROOT / "environments")
    base_env = _load(
        "marble.environments.base_env",
        PACKAGE_ROOT / "environments" / "base_env.py",
    )
    environments.BaseEnvironment = base_env.BaseEnvironment
    for name in (
        "CodingEnvironment",
        "DBEnvironment",
        "MinecraftEnvironment",
        "ResearchEnvironment",
        "WebEnvironment",
        "WorldSimulationEnvironment",
    ):
        setattr(environments, name, type(name, (base_env.BaseEnvironment,), {}))
    _package("marble.utils", PACKAGE_ROOT / "utils")
    logger_module = _load("marble.utils.logger", PACKAGE_ROOT / "utils" / "logger.py")
    logger_module.get_logger = _stream_logger
    _package("marble.memory", PACKAGE_ROOT / "memory")
    _load("marble.memory.base_memory", PACKAGE_ROOT / "memory" / "base_memory.py")
    _load("marble.memory.shared_memory", PACKAGE_ROOT / "memory" / "shared_memory.py")
    memory = sys.modules["marble.memory"]
    memory.BaseMemory = sys.modules["marble.memory.base_memory"].BaseMemory
    memory.SharedMemory = sys.modules["marble.memory.shared_memory"].SharedMemory
    _package("marble.llms", PACKAGE_ROOT / "llms")
    _load("marble.llms.error_handler", PACKAGE_ROOT / "llms" / "error_handler.py")
    _load("marble.llms.model_prompting", PACKAGE_ROOT / "llms" / "model_prompting.py")
    _package("marble.agent", PACKAGE_ROOT / "agent")
    _load("marble.agent.base_agent", PACKAGE_ROOT / "agent" / "base_agent.py")
    agent_pkg = sys.modules["marble.agent"]
    agent_pkg.BaseAgent = sys.modules["marble.agent.base_agent"].BaseAgent
    _package("marble.configs", PACKAGE_ROOT / "configs")
    _load("marble.configs.config", PACKAGE_ROOT / "configs" / "config.py")
    _package("marble.graph", PACKAGE_ROOT / "graph")
    _load("marble.graph.agent_graph", PACKAGE_ROOT / "graph" / "agent_graph.py")
    _READY = True


def _stream_logger(name: str) -> logging.Logger:
    """Return a logger that writes to the console.

    Args:
        name: Logger name.

    Returns:
        Logger with one console handler.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
        )
        logger.addHandler(handler)
    logger.propagate = False
    return logger


def _package(name: str, path: Path) -> types.ModuleType:
    """Register one package without running its init module."""
    if name in sys.modules:
        return sys.modules[name]
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    module.__package__ = name
    sys.modules[name] = module
    return module


def _load(name: str, path: Path) -> types.ModuleType:
    """Load one module from a file and register it."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _stub_model_imports() -> None:
    """Provide the model-client names the base agent imports."""
    if "litellm" in sys.modules:
        return
    try:
        import litellm  # noqa: F401
        return
    except ImportError:
        pass
    litellm = types.ModuleType("litellm")
    utils = types.ModuleType("litellm.utils")

    def token_counter(*_args: object, **_kwargs: object) -> int:
        """Return zero tokens."""
        return 0

    def trim_messages(messages: object, *_args: object, **_kwargs: object) -> object:
        """Return the messages unchanged."""
        return messages

    utils.token_counter = token_counter
    utils.trim_messages = trim_messages
    litellm.utils = utils
    litellm.token_counter = token_counter
    litellm.completion = lambda **_kwargs: None
    types_mod = types.ModuleType("litellm.types")
    types_utils = types.ModuleType("litellm.types.utils")

    class Message:
        """Stand in for a model message."""

    types_utils.Message = Message
    types_mod.utils = types_utils
    sys.modules["litellm"] = litellm
    sys.modules["litellm.utils"] = utils
    sys.modules["litellm.types"] = types_mod
    sys.modules["litellm.types.utils"] = types_utils

    if "beartype" not in sys.modules:
        try:
            import beartype  # noqa: F401
        except ImportError:
            import typing

            beartype = types.ModuleType("beartype")
            beartype.beartype = lambda wrapped: wrapped
            beartype_typing = types.ModuleType("beartype.typing")
            for typing_name in dir(typing):
                if typing_name.startswith("_"):
                    continue
                setattr(beartype_typing, typing_name, getattr(typing, typing_name))
            beartype.typing = beartype_typing
            sys.modules["beartype"] = beartype
            sys.modules["beartype.typing"] = beartype_typing

    if "pydantic" not in sys.modules:
        try:
            import pydantic  # noqa: F401
        except ImportError:
            pydantic = types.ModuleType("pydantic")

            class BaseModel:
                """Stand in for a data model."""

            pydantic.BaseModel = BaseModel
            sys.modules["pydantic"] = pydantic
    if "ruamel" not in sys.modules:
        try:
            import ruamel.yaml  # noqa: F401
        except ImportError:
            ruamel = types.ModuleType("ruamel")
            ruamel_yaml = types.ModuleType("ruamel.yaml")

            class YAML:
                """Stand in for a YAML loader."""

            ruamel_yaml.YAML = YAML
            ruamel.yaml = ruamel_yaml
            sys.modules["ruamel"] = ruamel
            sys.modules["ruamel.yaml"] = ruamel_yaml
