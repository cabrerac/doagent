"""Grid-world policy factories for the gridworld demo.

This is example code, not part of the doagent library. It contains
heuristic and LLM-based policies for the grid-world mapping scenario.
"""

from __future__ import annotations

import json
import random
from typing import Any, Dict, Iterable, Tuple

from examples.llm_policy import llm_decide_factory


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
        return {"choice": {"status": "act", "action": action}}

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
            return {"choice": {"status": "act", "action": 0}}
        unknown_cells = [
            (ux, uy)
            for ux in range(width)
            for uy in range(height)
            if (ux, uy) not in known
        ]
        if not unknown_cells:
            return {"choice": {"status": "act", "action": 0}}
        nearest = min(
            unknown_cells,
            key=lambda cell: abs(cell[0] - x) + abs(cell[1] - y),
        )
        action = _move_towards((x, y), nearest)
        if action == 0:
            action = rng.choice([1, 2, 3, 4])
        return {"choice": {"status": "act", "action": action}}

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
            return {"choice": {"status": "act", "action": 0, "bid": 0.0}}
        nearest = min(
            unknown_cells,
            key=lambda cell: abs(cell[0] - x) + abs(cell[1] - y),
        )
        distance = abs(nearest[0] - x) + abs(nearest[1] - y)
        action = _move_towards((x, y), nearest)
        if action == 0:
            action = rng.choice([1, 2, 3, 4])
        bid = 1.0 / (distance + 1.0)
        return {"choice": {"status": "act", "action": action, "bid": bid}}

    return decide


def _build_gridworld_prompt(
    inputs: Any,
    action_space: Dict[int, str],
    goal: str,
) -> str:
    """Build a gridworld-specific user prompt for the LLM.

    ``inputs`` is the full request inputs dict, typically containing
    ``observation`` (from env) and ``shared_map`` (aggregated from records).
    """
    observation = inputs.get("observation", inputs)
    shared_map = inputs.get("shared_map", {})

    pos = observation.get("position", {})
    x, y = int(pos.get("x", 0)), int(pos.get("y", 0))
    cells = observation.get("cells", [])
    w = int(observation.get("width", 0))
    h = int(observation.get("height", 0))

    known: set = set()
    for c in shared_map.get("cells", []):
        cx, cy = c.get("x"), c.get("y")
        if cx is not None and cy is not None:
            known.add((int(cx), int(cy)))
    for c in cells:
        cx, cy = c.get("x"), c.get("y")
        if cx is not None and cy is not None:
            known.add((int(cx), int(cy)))

    total_cells = w * h if w and h else 0
    known_count = len(known)
    remaining = total_cells - known_count if total_cells else "?"

    wall_info = []
    if x <= 0:
        wall_info.append("left (wall)")
    if x >= w - 1:
        wall_info.append("right (wall)")
    if y <= 0:
        wall_info.append("up (wall)")
    if y >= h - 1:
        wall_info.append("down (wall)")

    neighbors = [
        ("left",  x - 1, y),
        ("right", x + 1, y),
        ("down",  x, y + 1),
        ("up",    x, y - 1),
    ]
    unexplored_dirs = []
    explored_dirs = []
    blocked_dirs = []
    for name, nx, ny in neighbors:
        if nx < 0 or ny < 0 or (w and nx >= w) or (h and ny >= h):
            blocked_dirs.append(name)
        elif (nx, ny) not in known:
            unexplored_dirs.append(name)
        else:
            explored_dirs.append(name)

    visible_summary = []
    for c in cells:
        tag = " LANDMARK" if c.get("value") == "landmark" else ""
        visible_summary.append(f"({c.get('x')},{c.get('y')}{tag})")

    actions_desc = "\n".join(f"  {k}: {v}" for k, v in sorted(action_space.items()))

    parts = [
        f"Goal: {goal}",
        "",
        f"Grid size: {w} x {h} (coordinates 0..{w-1} horizontal, 0..{h-1} vertical).",
        f"Your position: ({x}, {y}).",
        f"Cells visible now: {', '.join(visible_summary)}.",
        f"Total explored by all agents: {known_count}/{total_cells} — {remaining} cells left.",
    ]

    if wall_info:
        parts.append(f"Walls adjacent: {', '.join(wall_info)}.")
    if blocked_dirs:
        parts.append(f"Blocked directions (wall): {', '.join(blocked_dirs)}.")
    if unexplored_dirs:
        parts.append(f"Unexplored neighbor directions: {', '.join(unexplored_dirs)} — prefer these!")
    if explored_dirs:
        parts.append(f"Already explored directions: {', '.join(explored_dirs)}.")

    parts += [
        "",
        f"Available actions:\n{actions_desc}",
        "",
        "Strategy: move toward unexplored areas. Avoid walls and already-explored "
        "directions when possible. If all neighbors are explored, pick the direction "
        "most likely to lead to distant unexplored cells.",
        "Respond with JSON only.",
    ]

    return "\n".join(parts)


_GRIDWORLD_ACTION_SPACE: Dict[int, str] = {
    0: "stay",
    1: "left",
    2: "right",
    3: "down",
    4: "up",
}


def llm_explore_policy(params: Dict[str, Any]):
    """LLM-based exploration policy for the grid-world."""
    merged_params = {
        "action_space": _GRIDWORLD_ACTION_SPACE,
        "confidence_threshold": float(params.get("confidence_threshold", 0.3)),
        "build_prompt": _build_gridworld_prompt,
        **params,
    }
    if "action_space" not in params:
        merged_params["action_space"] = _GRIDWORLD_ACTION_SPACE
    return llm_decide_factory(merged_params)


def register_gridworld_policies(registry) -> None:
    """Register all gridworld policies on a PolicyRegistry."""
    registry.register("grid_random", random_explore_policy)
    registry.register("grid_frontier", frontier_explore_policy)
    registry.register("grid_auction_frontier", auction_frontier_policy)
    registry.register("grid_llm", llm_explore_policy)
