"""Grid-world policy factories for validation scenarios."""

from __future__ import annotations

import random
from typing import Any, Dict, Iterable, Tuple


def _move_towards(src: Tuple[int, int], dst: Tuple[int, int]) -> int:
    dx = dst[0] - src[0]
    dy = dst[1] - src[1]
    if dx == 0 and dy == 0:
        return 0
    if abs(dx) >= abs(dy):
        return 2 if dx > 0 else 1
    return 3 if dy > 0 else 4


def _neighbors(pos: Tuple[int, int]) -> Iterable[Tuple[int, int, int]]:
    x, y = pos
    return [
        (x - 1, y, 1),
        (x + 1, y, 2),
        (x, y + 1, 3),
        (x, y - 1, 4),
    ]


def _known_cells(shared_map: Dict[str, Any]) -> set[Tuple[int, int]]:
    return {
        (cell.get("x"), cell.get("y"))
        for cell in shared_map.get("cells", [])
        if cell.get("x") is not None and cell.get("y") is not None
    }


def _grid_bounds(observation: Dict[str, Any]) -> Tuple[int, int]:
    width = observation.get("width")
    height = observation.get("height")
    if width is None or height is None:
        return (0, 0)
    return (int(width), int(height))


def random_explore_policy(params: Dict[str, Any]):
    """Random walk with bias toward unknown neighbors."""
    seed = int(params.get("seed", 0))
    rng = random.Random(seed)

    def decide(request):
        obs = request.get("inputs", {}).get("observation", {})
        shared_map = request.get("inputs", {}).get("shared_map", {})
        pos = obs.get("position", {})
        x, y = int(pos.get("x", 0)), int(pos.get("y", 0))
        width, height = _grid_bounds(obs)
        known = _known_cells(shared_map)
        unknown_actions = []
        valid_actions = []
        for nx, ny, action in _neighbors((x, y)):
            if width and height:
                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    continue
            valid_actions.append(action)
            if (nx, ny) not in known:
                unknown_actions.append(action)
        if unknown_actions:
            action = rng.choice(unknown_actions)
        elif valid_actions:
            action = rng.choice(valid_actions)
        else:
            action = 0
        return {"decision": {"action": action}}

    return decide


def frontier_explore_policy(params: Dict[str, Any]):
    """Move toward nearest unknown cell based on shared map."""
    seed = int(params.get("seed", 0))
    rng = random.Random(seed)

    def decide(request):
        obs = request.get("inputs", {}).get("observation", {})
        shared_map = request.get("inputs", {}).get("shared_map", {})
        pos = obs.get("position", {})
        x, y = int(pos.get("x", 0)), int(pos.get("y", 0))
        width, height = _grid_bounds(obs)
        known = _known_cells(shared_map)
        if width == 0 or height == 0:
            return {"decision": {"action": 0}}
        unknown_cells = [
            (ux, uy)
            for ux in range(width)
            for uy in range(height)
            if (ux, uy) not in known
        ]
        if not unknown_cells:
            return {"decision": {"action": 0}}
        nearest = min(
            unknown_cells,
            key=lambda cell: abs(cell[0] - x) + abs(cell[1] - y),
        )
        action = _move_towards((x, y), nearest)
        if action == 0:
            action = rng.choice([1, 2, 3, 4])
        return {"decision": {"action": action}}

    return decide


def auction_frontier_policy(params: Dict[str, Any]):
    """Auction stub: frontier move with a bid based on distance."""
    seed = int(params.get("seed", 0))
    rng = random.Random(seed)

    def decide(request):
        obs = request.get("inputs", {}).get("observation", {})
        shared_map = request.get("inputs", {}).get("shared_map", {})
        pos = obs.get("position", {})
        x, y = int(pos.get("x", 0)), int(pos.get("y", 0))
        width, height = _grid_bounds(obs)
        known = _known_cells(shared_map)
        unknown_cells = [
            (ux, uy)
            for ux in range(width)
            for uy in range(height)
            if (ux, uy) not in known
        ]
        if not unknown_cells:
            return {"decision": {"action": 0, "bid": 0.0}}
        nearest = min(
            unknown_cells,
            key=lambda cell: abs(cell[0] - x) + abs(cell[1] - y),
        )
        distance = abs(nearest[0] - x) + abs(nearest[1] - y)
        action = _move_towards((x, y), nearest)
        if action == 0:
            action = rng.choice([1, 2, 3, 4])
        bid = 1.0 / (distance + 1.0)
        return {"decision": {"action": action, "bid": bid}}

    return decide


def register_gridworld_policies(registry) -> None:
    registry.register("grid_random", random_explore_policy)
    registry.register("grid_frontier", frontier_explore_policy)
    registry.register("grid_auction_frontier", auction_frontier_policy)
