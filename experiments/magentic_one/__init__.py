"""Export the Magentic-One team.

run_magentic_team runs the team on a Session.
run_direct_team passes each result to the next policy.
specialist_policy_factory wraps an on_messages agent as a Session policy.
build_specialists constructs the four AutoGen specialists.
FROZEN_QUERY and gold_record describe the frozen query and its labels.
"""

from experiments.magentic_one.direct import run_direct_team
from experiments.magentic_one.query import FROZEN_QUERY, gold_record
from experiments.magentic_one.specialists import (
    build_specialists,
    specialist_policy_factory,
)
from experiments.magentic_one.team import run_magentic_team

__all__ = [
    "FROZEN_QUERY",
    "build_specialists",
    "gold_record",
    "run_direct_team",
    "run_magentic_team",
    "specialist_policy_factory",
]
