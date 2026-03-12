"""DOAgent experiments: runners, reporters, and scenario wiring for evaluating the library.

Not part of the public API. For end-user demos see examples/.
"""

from .baseline import BaselineMetrics, measure_baseline, output_bytes_from_path, write_summary
from .environment import ParallelEnvWrapper, StepResult, ValidationEnv
from .reporting import RunReporter
from .multiprocess_interface import MultiProcessInterface
from .push import PushRunSummary, run_push_validation
from .gridworld import GridWorldRunSummary, run_gridworld_validation

# Re-export NoOpSharedData and PolicyRegistry from doagent.core for experiment scripts
# that need them (e.g. tests, example runners that haven't migrated to Session.from_config).
from doagent.core import NoOpSharedData  # noqa: F401
from doagent.core.policy import PolicyRegistry  # noqa: F401

__all__ = [
    "BaselineMetrics",
    "measure_baseline",
    "output_bytes_from_path",
    "write_summary",
    "ParallelEnvWrapper",
    "StepResult",
    "ValidationEnv",
    "RunReporter",
    "MultiProcessInterface",
    "PushRunSummary",
    "run_push_validation",
    "GridWorldRunSummary",
    "run_gridworld_validation",
    "NoOpSharedData",
    "PolicyRegistry",
]
