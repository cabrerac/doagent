"""DOAgent core library.

The public API is Session, RunConfig, make_env, and RunReporter.
Use Session.from_config(config) for config-driven setup.
RunReporter is an optional helper for progress messages and run summaries.
"""

from .core.run_config import RunConfig
from .core.session import Session
from .env import make_env
from .reporting import RunReporter

__all__ = [
    "RunConfig",
    "RunReporter",
    "Session",
    "make_env",
]
