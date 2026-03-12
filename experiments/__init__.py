"""DOAgent experiments: runners, reporters, and scenario wiring for evaluating the library.

Not part of the public API. For end-user demos see examples/.
Runners accept a Session (from doagent.Session.from_config) and use only the public API;
they do not accept adapters or PolicyRegistry.
MultiProcessInterface (multiprocess_interface module) is internal and not re-exported.
"""

from .baseline import BaselineMetrics, measure_baseline, output_bytes_from_path, write_summary
from .environment import ParallelEnvWrapper, StepResult, ValidationEnv
from .reporting import RunReporter
from .push import PushRunSummary, run_push_validation
from .gridworld import GridWorldRunSummary, run_gridworld_validation

__all__ = [
    "BaselineMetrics",
    "measure_baseline",
    "output_bytes_from_path",
    "write_summary",
    "ParallelEnvWrapper",
    "StepResult",
    "ValidationEnv",
    "RunReporter",
    "PushRunSummary",
    "run_push_validation",
    "GridWorldRunSummary",
    "run_gridworld_validation",
]
