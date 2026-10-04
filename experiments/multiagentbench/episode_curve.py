"""Track Werewolf entropy and modularity one episode at a time.

The environment records facts, holders, and votes here.
Agents do not read this record.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from experiments.multiagentbench.metrics import entropy
from experiments.multiagentbench.recover import modularity_of


class FactBook:
    """Hold the facts and the episode curve for one game.

    A fact is a night outcome.
    Holders are living players who have been sent its text.
    """

    def __init__(self, players: Sequence[str]) -> None:
        """Start with every player alive and no facts.

        Args:
            players: Player ids in the game.
        """
        self.audience = set(players)
        self.facts: list[dict[str, Any]] = []
        self.episodes: list[dict[str, Any]] = []
        self.line_count = 0
        self._created: list[dict[str, Any]] = []
        self._propagated: list[dict[str, Any]] = []

    def create(self, origin: str, proposition: str, holders: Sequence[str]) -> None:
        """Record a new fact and its first holders.

        Args:
            origin: Episode name where the fact is created.
            proposition: Text that carries the fact.
            holders: Players who are sent that text now.
        """
        living = [name for name in holders if name in self.audience]
        self.facts.append(
            {
                "origin": origin,
                "proposition": proposition,
                "holders": set(living),
            }
        )
        self._created.append({"proposition": proposition, "holders": list(living)})

    def deliver(self, content: str, recipients: Sequence[str]) -> None:
        """Give existing facts to living recipients of a matching message.

        Args:
            content: Delivered message text.
            recipients: Players who are sent that message.
        """
        self.line_count += 1
        for fact in self.facts:
            if fact["proposition"] not in content:
                continue
            fresh = []
            for name in recipients:
                if name in self.audience and name not in fact["holders"]:
                    fact["holders"].add(name)
                    fresh.append(name)
            if fresh:
                self._propagated.append(
                    {
                        "origin": fact["origin"],
                        "proposition": fact["proposition"],
                        "new_holders": fresh,
                    }
                )

    def remove(self, player_id: str) -> None:
        """Drop a dead player from the audience and from every fact.

        Args:
            player_id: Player who died.
        """
        self.audience.discard(player_id)
        for fact in self.facts:
            fact["holders"].discard(player_id)

    def close_night(self, episode: str) -> dict[str, Any]:
        """Append the entropy snapshot for one night.

        Args:
            episode: Night name, such as night-1.

        Returns:
            The episode row.
        """
        return self._close(episode, None)

    def close_day(self, episode: str, votes: Optional[Mapping[str, str]]) -> dict[str, Any]:
        """Append the entropy snapshot and the exile vote for one day.

        Args:
            episode: Day name, such as day-1.
            votes: Player id to exile label.
                Fewer than two votes leaves the modularity empty.

        Returns:
            The episode row.
        """
        return self._close(episode, votes)

    def document(self) -> dict[str, Any]:
        """Return the episodes written so far.

        Returns:
            A document with an episodes list.
        """
        return {"episodes": list(self.episodes)}

    def _close(
        self,
        episode: str,
        votes: Optional[Mapping[str, str]],
    ) -> dict[str, Any]:
        audience = sorted(self.audience)
        population = len(audience)
        fact_rows = []
        scores = []
        for fact in self.facts:
            holders = sorted(name for name in fact["holders"] if name in self.audience)
            score = entropy(len(holders), population)
            fact_rows.append(
                {
                    "origin": fact["origin"],
                    "proposition": fact["proposition"],
                    "holders": holders,
                    "entropy": score,
                }
            )
            scores.append(score)
        game_entropy = sum(scores) / len(scores) if scores else 0.0
        modularity = None
        vote_map = None
        if votes is not None and len(votes) >= 2:
            vote_map = {str(name): str(label) for name, label in votes.items()}
            modularity = modularity_of(vote_map)
        row = {
            "episode": episode,
            "audience": audience,
            "created": list(self._created),
            "propagated": list(self._propagated),
            "facts": fact_rows,
            "game_entropy": game_entropy,
            "votes": vote_map,
            "modularity": modularity,
            "end_line": self.line_count,
        }
        self.episodes.append(row)
        self._created = []
        self._propagated = []
        return row


def write_document(path: Path, document: Mapping[str, Any]) -> None:
    """Write the episode curve to a private file.

    Args:
        path: Destination path.
        document: Episode document.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2), encoding="utf-8")
