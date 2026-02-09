"""Lightweight grid-world environment for validation scenarios."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Dict, Iterable, List, Tuple

from .environment import StepResult, ValidationEnv


@dataclass(frozen=True)
class GridCell:
    """Serializable grid cell descriptor."""

    x: int
    y: int
    value: str


class GridWorldEnv(ValidationEnv):
    """Dependency-free grid-world with partial observations."""

    def __init__(
        self,
        *,
        width: int,
        height: int,
        agent_ids: List[str],
        landmarks: int = 2,
        observation_radius: int = 1,
        max_cycles: int = 25,
        seed: int | None = None,
    ) -> None:
        self._width = width
        self._height = height
        self._agent_ids = list(agent_ids)
        self._landmarks = landmarks
        self._observation_radius = observation_radius
        self._max_cycles = max_cycles
        self._rng = random.Random(seed)
        self._positions: Dict[str, Tuple[int, int]] = {}
        self._landmark_positions: List[Tuple[int, int]] = []
        self._discovered: set[Tuple[int, int]] = set()
        self._step_count = 0

    @property
    def agents(self) -> Iterable[str]:
        return list(self._agent_ids)

    def reset(self, *, seed: int | None = None) -> Dict[str, Any]:
        if seed is not None:
            self._rng.seed(seed)
        self._step_count = 0
        self._positions = {
            agent_id: self._random_position() for agent_id in self._agent_ids
        }
        self._landmark_positions = [
            self._random_position() for _ in range(self._landmarks)
        ]
        self._discovered.clear()
        observations = {agent_id: self._observe(agent_id) for agent_id in self._agent_ids}
        for obs in observations.values():
            for cell in obs["cells"]:
                self._discovered.add((cell["x"], cell["y"]))
        return observations

    def step(self, actions: Dict[str, Any]) -> StepResult:
        self._step_count += 1
        for agent_id, action in actions.items():
            if agent_id not in self._positions:
                continue
            self._positions[agent_id] = self._move(self._positions[agent_id], action)

        observations = {agent_id: self._observe(agent_id) for agent_id in self._agent_ids}
        rewards: Dict[str, float] = {}
        for agent_id, obs in observations.items():
            newly_discovered = 0
            for cell in obs["cells"]:
                coord = (cell["x"], cell["y"])
                if coord not in self._discovered:
                    newly_discovered += 1
                    self._discovered.add(coord)
            rewards[agent_id] = float(newly_discovered)

        done = self._step_count >= self._max_cycles
        terminations = {agent_id: done for agent_id in self._agent_ids}
        truncations = {agent_id: False for agent_id in self._agent_ids}
        infos = {agent_id: {} for agent_id in self._agent_ids}
        return StepResult(
            observations=observations,
            rewards=rewards,
            terminations=terminations,
            truncations=truncations,
            infos=infos,
        )

    def render(self) -> None:
        return None

    def _random_position(self) -> Tuple[int, int]:
        return (
            self._rng.randrange(self._width),
            self._rng.randrange(self._height),
        )

    def _move(self, position: Tuple[int, int], action: Any) -> Tuple[int, int]:
        x, y = position
        if action == 1:
            x -= 1
        elif action == 2:
            x += 1
        elif action == 3:
            y += 1
        elif action == 4:
            y -= 1
        x = max(0, min(self._width - 1, x))
        y = max(0, min(self._height - 1, y))
        return (x, y)

    def _observe(self, agent_id: str) -> Dict[str, Any]:
        x, y = self._positions[agent_id]
        cells: List[Dict[str, Any]] = []
        for dx in range(-self._observation_radius, self._observation_radius + 1):
            for dy in range(-self._observation_radius, self._observation_radius + 1):
                cx = x + dx
                cy = y + dy
                if cx < 0 or cy < 0 or cx >= self._width or cy >= self._height:
                    continue
                value = "landmark" if (cx, cy) in self._landmark_positions else "empty"
                cells.append({"x": cx, "y": cy, "value": value})
        return {
            "position": {"x": x, "y": y},
            "cells": cells,
            "radius": self._observation_radius,
        }


def make_grid_env(
    *,
    width: int,
    height: int,
    agent_ids: List[str],
    landmarks: int = 2,
    observation_radius: int = 1,
    max_cycles: int = 25,
    seed: int | None = None,
) -> ValidationEnv:
    """Create a grid-world environment for validation."""
    return GridWorldEnv(
        width=width,
        height=height,
        agent_ids=agent_ids,
        landmarks=landmarks,
        observation_radius=observation_radius,
        max_cycles=max_cycles,
        seed=seed,
    )
