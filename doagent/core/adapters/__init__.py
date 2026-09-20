"""Shared-data adapters: storage backends for DOAgent records.

All adapters implement the SharedDataAdapter protocol.
Use via Session.from_config({"shared_data": {"type": "memory"|"file"|"noop"}}) or import for direct use:

    from doagent.core.adapters import (
        FileSharedData,
        InMemorySharedData,
        NoOpSharedData,
    )
    # optional, needs pip install pymongo
    from doagent.core.adapters import MongoSharedData
"""

from .in_memory import InMemorySharedData
from .file import FileSharedData
from .noop import NoOpSharedData

try:
    from .mongo import MongoSharedData
except ImportError:
    MongoSharedData = None  # type: ignore[assignment,misc]

__all__ = [
    "InMemorySharedData",
    "FileSharedData",
    "NoOpSharedData",
    "MongoSharedData",
]
