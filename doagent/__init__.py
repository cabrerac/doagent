"""DOAgent core library.

User-facing API: Session, RunConfig, make_env. Use Session.from_config(config)
for config-driven setup; adapters and record types are internal.
"""

from .core import InMemorySharedData
from .core.run_config import RunConfig
from .core.session import Session
from .env import make_env

__all__ = [
    "InMemorySharedData",
    "RunConfig",
    "Session",
    "make_env",
]
