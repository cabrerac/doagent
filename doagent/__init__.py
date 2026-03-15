"""DOAgent core library.

Public API: Session, RunConfig, make_env, RunReporter. Use Session.from_config(config)
for config-driven setup. RunReporter is an optional helper for progress and run summaries.
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
