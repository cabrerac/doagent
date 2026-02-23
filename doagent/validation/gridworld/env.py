"""Lightweight grid-world environment for validation scenarios."""

from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any, Dict, Iterable, List, Tuple

from ..environment import StepResult, ValidationEnv

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]


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
        render_mode: str | None = None,
    ) -> None:
        self._width = width
        self._height = height
        self._agent_ids = list(agent_ids)
        self._landmarks = landmarks
        self._observation_radius = observation_radius
        self._max_cycles = max_cycles
        self._rng = random.Random(seed)
        self._render_mode = render_mode
        self._renderer = None
        self._cell_size = 32
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

    def render(self) -> "np.ndarray | None":
        if self._render_mode == "human":
            self._render_pygame()
            return None
        if self._render_mode == "rgb_array":
            return self._render_rgb_array()
        self._render_ansi()
        return None

    def _render_ansi(self) -> None:
        lines = []
        header = f"GridWorld step {self._step_count}"
        lines.append(header)
        grid = [["." for _ in range(self._width)] for _ in range(self._height)]
        for lx, ly in self._landmark_positions:
            grid[ly][lx] = "L"
        for idx, agent_id in enumerate(self._agent_ids):
            pos = self._positions.get(agent_id)
            if not pos:
                continue
            ax, ay = pos
            marker = str(idx) if idx < 10 else "A"
            if grid[ay][ax] != ".":
                marker = "*"
            grid[ay][ax] = marker
        for row in grid:
            lines.append(" ".join(row))
        print("\n".join(lines))

    def _draw_to_surface(self, surface: Any) -> None:
        """Draw current state onto a pygame Surface (used by human and rgb_array)."""
        import pygame  # type: ignore
        surface.fill((245, 245, 245))
        for x in range(self._width):
            for y in range(self._height):
                rect = pygame.Rect(
                    x * self._cell_size,
                    y * self._cell_size,
                    self._cell_size,
                    self._cell_size,
                )
                pygame.draw.rect(surface, (220, 220, 220), rect, 1)
        for lx, ly in self._landmark_positions:
            rect = pygame.Rect(
                lx * self._cell_size,
                ly * self._cell_size,
                self._cell_size,
                self._cell_size,
            )
            pygame.draw.rect(surface, (255, 204, 0), rect)
        colors = [
            (66, 135, 245),
            (245, 66, 167),
            (66, 245, 170),
            (245, 152, 66),
        ]
        font = pygame.font.Font(None, max(16, self._cell_size // 2))
        for idx, agent_id in enumerate(self._agent_ids):
            pos = self._positions.get(agent_id)
            if not pos:
                continue
            ax, ay = pos
            color = colors[idx % len(colors)]
            center = (
                ax * self._cell_size + self._cell_size // 2,
                ay * self._cell_size + self._cell_size // 2,
            )
            pygame.draw.circle(surface, color, center, self._cell_size // 3)
            label = agent_id.split("_")[-1] if "_" in agent_id else agent_id[:3]
            text_surf = font.render(label, True, (0, 0, 0))
            text_rect = text_surf.get_rect(center=center)
            surface.blit(text_surf, text_rect)

    def _render_rgb_array(self) -> "np.ndarray | None":
        """Render to an offscreen buffer and return (H, W, 3) uint8 array."""
        if np is None:
            return None
        try:
            import pygame  # type: ignore
        except Exception:
            return None
        pygame.init()
        width_px = self._width * self._cell_size
        height_px = self._height * self._cell_size
        surface = pygame.Surface((width_px, height_px))
        self._draw_to_surface(surface)
        # pygame.surfarray: (W, H, 3) -> we need (H, W, 3)
        arr = pygame.surfarray.array3d(surface)
        return np.asarray(arr).swapaxes(0, 1)

    def _render_pygame(self) -> None:
        try:
            import pygame  # type: ignore
        except Exception:
            self._render_ansi()
            return
        if self._renderer is None:
            pygame.init()
            width_px = self._width * self._cell_size
            height_px = self._height * self._cell_size
            self._renderer = pygame.display.set_mode((width_px, height_px))
            pygame.display.set_caption("GridWorld")
        self._draw_to_surface(self._renderer)
        pygame.display.flip()

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
            "width": self._width,
            "height": self._height,
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
    render_mode: str | None = None,
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
        render_mode=render_mode,
    )
