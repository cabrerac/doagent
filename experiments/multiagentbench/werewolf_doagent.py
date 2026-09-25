"""Werewolf environment for one night and the day that follows.

reset starts the night.
Each step asks the players for the current action and writes their lines on the outcome.
The day elects a sheriff on day 1, hears last words, takes speeches, then votes.
A sheriff who dies at night or is exiled decides who receives the badge.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional


class WerewolfEnv:
    """Owns one night and the day after it.

    A missing role is skipped.
    Wolf discussion repeats while the wolves lack a majority and rounds remain.
    """

    def __init__(self, roles: Mapping[str, str], max_days: int = 1) -> None:
        """Store player ids, roles, and how many days to play.

        Args:
            roles: Player id to role name.
            max_days: Stop after this many days even if both sides remain.
        """
        self._roles = dict(roles)
        self._max_days = max_days
        self.finished = False
        self.asked: list[str] = []
        self.action_name = ""
        self._alive: List[str] = []
        self._protected: Optional[str] = None
        self._last_protected: Optional[str] = None
        self._antidote = 1
        self._poison = 1
        self._rounds_left = 5
        self._wolf_votes: Dict[str, str] = {}
        self._final_target: Optional[str] = None
        self._dead: List[str] = []
        self._phase = "guard"
        self._day = 1
        self._sheriff: Optional[str] = None
        self._badge_from: Optional[str] = None
        self._after_badge = ""
        self._candidates: List[str] = []
        self._candidate_index = 0
        self._speaker_index = 0
        self._speech_order: List[str] = []
        self._use_daily_tasks = True
        self.phases: List[Dict[str, Any]] = []

    @property
    def agents(self) -> list[str]:
        """Return the player ids."""
        return list(self._roles)

    def living(self, role: str) -> list[str]:
        """Return living player ids with one role.

        Args:
            role: Role name, such as wolf or seer.

        Returns:
            Living player ids.
        """
        return [
            player_id
            for player_id in self._alive
            if self._roles.get(player_id) == role
        ]

    def reset(self, *, seed: Optional[int] = None) -> Dict[str, Any]:
        """Start the night and return the first ask.

        Args:
            seed: Ignored.

        Returns:
            One observation per player who must answer.
        """
        del seed
        self.finished = False
        self._alive = list(self._roles)
        self._protected = None
        self._last_protected = None
        self._antidote = 1
        self._poison = 1
        self._rounds_left = 5
        self._wolf_votes = {}
        self._final_target = None
        self._dead = []
        self._phase = "guard"
        self._day = 1
        self._sheriff = None
        self._badge_from = None
        self._after_badge = ""
        self._candidates = []
        self._candidate_index = 0
        self._speaker_index = 0
        self._speech_order = []
        self.phases = []
        return self._open_ask()

    def step(self, actions: Mapping[str, Any]) -> Dict[str, Any]:
        """Apply the current ask and open the next one.

        Args:
            actions: Player id to the action returned by that player's policy.

        Returns:
            Observations, rewards, and whether the night has finished.
            New game lines are under observations["game_line"].
        """
        lines = self._apply(actions)
        observations = self._open_ask()
        observations["game_line"] = lines
        return {
            "observations": observations,
            "rewards": {},
            "done": self.finished,
        }

    def render(self) -> None:
        """Do nothing."""

    def _open_ask(self) -> Dict[str, Any]:
        """Return observations for the next players who must answer."""
        while self._phase != "done":
            players = self._players_for_phase()
            if players:
                self.asked = players
                self.action_name = _ACTION_NAMES[self._phase]
                return {
                    player_id: {"action": self.action_name}
                    for player_id in players
                }
            self._phase = _next_phase(self._phase)
        self.asked = []
        self.action_name = ""
        self.finished = True
        return {}

    def _players_for_phase(self) -> list[str]:
        """Return the player ids the current phase asks."""
        if self._phase == "guard":
            return self.living("guard")
        if self._phase in ("werewolf_action", "werewolf_discussion"):
            return self.living("wolf")
        if self._phase == "seer":
            return self.living("seer")
        if self._phase == "witch":
            return self.living("witch")
        if self._phase == "run_for_sheriff":
            return list(self._alive)
        if self._phase == "sheriff_speech":
            if self._candidate_index < len(self._candidates):
                return [self._candidates[self._candidate_index]]
            return []
        if self._phase == "vote_for_sheriff":
            return [player_id for player_id in self._alive if player_id not in self._candidates]
        if self._phase == "last_words":
            if self._day == 1 and self._dead:
                return [self._dead[0]]
            return []
        if self._phase == "decide_speech_sequence":
            if self._sheriff in self._alive:
                return [self._sheriff]
            return []
        if self._phase == "player_speech":
            if not self._speech_order:
                self._speech_order = sorted(self._alive)
            speakers = self._speech_order
            if self._speaker_index < len(speakers):
                return [speakers[self._speaker_index]]
            return []
        if self._phase == "vote_action":
            return list(self._alive)
        if self._phase == "badge_flow" and self._badge_from:
            return [self._badge_from]
        return []

    def _apply(self, actions: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Apply the current phase and return the lines it writes."""
        phase = self._phase
        if phase == "guard":
            lines = self._apply_guard(actions)
        elif phase in ("werewolf_action", "werewolf_discussion"):
            lines = self._apply_wolves(actions)
        elif phase == "seer":
            lines = self._apply_seer(actions)
        elif phase == "witch":
            lines = self._apply_witch(actions)
        elif phase == "run_for_sheriff":
            lines = self._apply_run_for_sheriff(actions)
        elif phase == "sheriff_speech":
            lines = self._apply_sheriff_speech(actions)
        elif phase == "vote_for_sheriff":
            lines = self._apply_sheriff_vote(actions)
        elif phase == "last_words":
            lines = self._apply_last_words(actions)
        elif phase == "decide_speech_sequence":
            lines = self._apply_speech_order(actions)
        elif phase == "player_speech":
            lines = self._apply_player_speech(actions)
        elif phase == "vote_action":
            lines = self._apply_exile_vote(actions)
        elif phase == "badge_flow":
            lines = self._apply_badge(actions)
        else:
            lines = []
        if self._phase == "resolve":
            lines.extend(self._resolve())
        return lines

    def _apply_guard(self, actions: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Record the guard's protection and move on to the wolves."""
        guard_id = self.living("guard")[0]
        target = _field(actions.get(guard_id), "protect_target")
        lines = []
        if target in self._alive and target != self._last_protected:
            self._protected = target
            lines.append(
                _line(
                    guard_id,
                    [guard_id],
                    f"Guard protects {target}.",
                )
            )
        else:
            self._protected = None
            lines.append(
                _line(guard_id, [guard_id], "Guard protection failed.")
            )
        lines.append(
            _line(
                "system",
                list(self._alive),
                "Guard has chosen to protect a player.",
            )
        )
        self._phase = "werewolf_action"
        return lines

    def _apply_wolves(self, actions: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Record the wolf vote, or ask for another discussion round."""
        wolves = self.living("wolf")
        votes: Dict[str, str] = {}
        for wolf_id in wolves:
            action = actions.get(wolf_id) or {}
            nested = action.get("action") if isinstance(action, Mapping) else None
            source = nested if isinstance(nested, Mapping) else action
            attack = bool(source.get("attack")) if isinstance(source, Mapping) else False
            target = source.get("target") if isinstance(source, Mapping) else None
            if attack and target in self._alive:
                votes[wolf_id] = str(target)
            else:
                votes[wolf_id] = "false"
        self._wolf_votes = votes
        counts: Dict[str, int] = {}
        for choice in votes.values():
            if choice != "false":
                counts[choice] = counts.get(choice, 0) + 1
        majority = None
        for choice, count in counts.items():
            if count > len(wolves) / 2:
                majority = choice
                break
        if majority:
            self._final_target = majority
            killed = self._protected != majority
            if killed and majority in self._alive:
                self._dead.append(majority)
            target_text = f"target {majority}"
            self._phase = "seer"
        else:
            self._rounds_left -= 1
            target_text = "target none"
            if self._rounds_left > 0:
                self._phase = "werewolf_discussion"
            else:
                self._final_target = None
                self._phase = "seer"
        return [
            _line("wolves", wolves, target_text),
            _line(
                "system",
                list(self._alive),
                "Werewolves have chosen their target.",
            ),
        ]

    def _apply_seer(self, actions: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Tell the seer whether the checked player is a wolf."""
        seer_id = self.living("seer")[0]
        target = _field(actions.get(seer_id), "check_target")
        if target in self._roles and self._roles[target] == "wolf":
            result = "werewolf"
        else:
            result = "not a werewolf"
        self._phase = "witch"
        return [
            _line(
                seer_id,
                [seer_id],
                f"Seer checked {target}. The result is {result}.",
            ),
            _line(
                "system",
                list(self._alive),
                "Seer has checked a player's identity.",
            ),
        ]

    def _apply_witch(self, actions: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Apply the witch's antidote or poison."""
        witch_id = self.living("witch")[0]
        action = actions.get(witch_id) or {}
        nested = action.get("action") if isinstance(action, Mapping) else None
        source = nested if isinstance(nested, Mapping) else action
        if not isinstance(source, Mapping):
            source = {}
        use_antidote = bool(source.get("use_antidote"))
        use_poison = bool(source.get("use_poison"))
        poison_target = source.get("poison_target")
        note = "Witch chose not to use a potion."
        if use_antidote and self._antidote and self._final_target in self._dead:
            self._dead.remove(self._final_target)
            self._antidote = 0
            note = f"Witch saved {self._final_target}."
        elif use_poison and self._poison and poison_target in self._alive:
            if poison_target not in self._dead:
                self._dead.append(str(poison_target))
            self._poison = 0
            note = f"Witch poisoned {poison_target}."
        self._phase = "resolve"
        return [
            _line(witch_id, [witch_id], note),
            _line(
                "system",
                list(self._alive),
                "Witch has made her decision on potion use.",
            ),
        ]

    def _resolve(self) -> List[Dict[str, Any]]:
        """Remove the night's dead and either stop or start the day."""
        for player_id in self._dead:
            if player_id in self._alive:
                self._alive.remove(player_id)
        if self._dead:
            content = "Night deaths: " + ", ".join(self._dead)
        else:
            content = "Night deaths: nobody."
        self.phases.append(
            {
                "phase": f"night-{self._day}",
                "wolf_target": self._final_target,
                "protected": self._protected,
                "deaths": list(self._dead),
            }
        )
        if _side_wiped(self._alive, self._roles):
            self._phase = "done"
        elif self._offer_badge(self._sheriff if self._sheriff in self._dead else None, "day"):
            pass
        elif self._day == 1:
            self._phase = "run_for_sheriff"
        else:
            self._open_speeches()
        lines = [_line("system", list(self._roles), content)]
        lines.extend(self._daily_task_lines())
        return lines

    def _apply_run_for_sheriff(self, actions: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Collect who stands for sheriff."""
        self._candidates = []
        for player_id in self._alive:
            if _flag(_body(actions.get(player_id)), "run_for_sheriff"):
                self._candidates.append(player_id)
        self._candidate_index = 0
        if self._candidates:
            content = "Sheriff election candidates: " + ", ".join(self._candidates)
            self._phase = "sheriff_speech"
        else:
            content = "No candidates decided to run for sheriff."
            self._phase = "last_words"
        return [_line("system", list(self._alive), content)]

    def _apply_sheriff_speech(self, actions: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Publish one sheriff candidate's speech."""
        speaker = self._candidates[self._candidate_index]
        speech = _field(actions.get(speaker), "speech") or "..."
        self._candidate_index += 1
        if self._candidate_index >= len(self._candidates):
            self._phase = "vote_for_sheriff"
        return [_line(speaker, list(self._alive), speech)]

    def _apply_sheriff_vote(self, actions: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Elect a sheriff when one candidate has a majority."""
        votes = {
            player_id: _field(actions.get(player_id), "action_vote") or "abstain"
            for player_id in self._alive
            if player_id not in self._candidates
        }
        self._sheriff = _majority(votes, None)
        if self._sheriff:
            content = f"Sheriff elected: {self._sheriff}."
        else:
            content = "No sheriff was elected."
        self._phase = "last_words"
        return [_line("system", list(self._alive), content)]

    def _apply_last_words(self, actions: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Publish the night victim's last words."""
        speaker = self._dead[0]
        speech = _field(actions.get(speaker), "speech") or "..."
        self._open_speeches()
        return [_line(speaker, list(self._roles), speech)]

    def _apply_player_speech(self, actions: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Publish one living player's day speech."""
        speaker = self._speech_order[self._speaker_index]
        speech = _field(actions.get(speaker), "speech") or "..."
        self._speaker_index += 1
        if self._speaker_index >= len(self._speech_order):
            self._phase = "vote_action"
        return [_line(speaker, list(self._alive), speech)]

    def _apply_exile_vote(self, actions: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Exile the majority choice, then start the next night or stop."""
        votes = {
            player_id: _field(actions.get(player_id), "action_vote") or "abstain"
            for player_id in self._alive
        }
        exiled = _majority(votes, self._sheriff)
        if exiled and exiled in self._alive:
            self._alive.remove(exiled)
            content = f"Exile: {exiled}."
        else:
            content = "Exile: nobody."
        self.phases.append(
            {
                "phase": f"day-{self._day}",
                "sheriff": self._sheriff,
                "exile": exiled,
                "votes": votes,
            }
        )
        holder = exiled if exiled == self._sheriff else None
        if self._offer_badge(holder, "night"):
            pass
        elif _side_wiped(self._alive, self._roles) or self._day >= self._max_days:
            self._phase = "done"
        else:
            self._day += 1
            self._begin_night()
            self._phase = "guard"
        return [_line("system", list(self._roles), content)]

    def _offer_badge(self, holder: Optional[str], resume: str) -> bool:
        """Ask a sheriff who just died what to do with the badge."""
        if not holder or holder in self._alive:
            return False
        self._badge_from = holder
        self._after_badge = resume
        self._phase = "badge_flow"
        return True

    def _apply_badge(self, actions: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Pass the badge to a living player, or destroy it."""
        holder = self._badge_from or ""
        source = _body(actions.get(holder))
        receiver = source.get("badge_receiver")
        receiver_name = ""
        if receiver not in (None, "", "None", "null"):
            receiver_name = str(receiver)
        if _flag(source, "pass_badge") and receiver_name in self._alive:
            self._sheriff = receiver_name
            content = f"{holder} has passed the badge to {receiver_name}."
        elif _flag(source, "pass_badge"):
            self._sheriff = None
            content = (
                f"{holder} attempted to pass the badge, but it was destroyed instead."
            )
        else:
            self._sheriff = None
            content = f"{holder} has destroyed the badge."
        self._badge_from = None
        self._resume_after_badge()
        return [_line("system", list(self._roles), content)]

    def _resume_after_badge(self) -> None:
        """Continue the day, or the next night, after the badge decision."""
        resume = self._after_badge
        self._after_badge = ""
        if resume == "night":
            if _side_wiped(self._alive, self._roles) or self._day >= self._max_days:
                self._phase = "done"
            else:
                self._day += 1
                self._begin_night()
                self._phase = "guard"
            return
        if self._day == 1:
            self._phase = "run_for_sheriff"
        else:
            self._open_speeches()

    def _open_speeches(self) -> None:
        """Ask the sheriff for the order, or sort the living players by name."""
        self._speaker_index = 0
        self._speech_order = []
        if self._sheriff in self._alive:
            self._phase = "decide_speech_sequence"
        else:
            self._speech_order = sorted(self._alive)
            self._phase = "player_speech"

    def _apply_speech_order(self, actions: Mapping[str, Any]) -> List[Dict[str, Any]]:
        """Build the speech order from the sheriff's starting player and direction."""
        source = _body(actions.get(self._sheriff))
        starting = str(source.get("starting_player") or self._sheriff)
        from_left = bool(source.get("from_left", True))
        self._speech_order = _speech_order(
            list(self._roles),
            self._alive,
            self._sheriff,
            starting,
            from_left,
        )
        self._speaker_index = 0
        self._phase = "player_speech"
        order_text = ", ".join(self._speech_order)
        return [_line("system", list(self._alive), f"Speech order: {order_text}")]

    def _daily_task_lines(self) -> List[Dict[str, Any]]:
        """Return the public daily-task line when the published config leaves tasks on."""
        if not self._use_daily_tasks:
            return []
        private = []
        public = []
        if self.living("seer"):
            private.append("protect_seer")
        if self._poison:
            private.append("poison_werewolf")
            public.append("poison_werewolf")
        if self._antidote:
            private.append("rescue_villager")
            public.append("rescue_villager")
        if self._day == 1:
            private.append("run_for_sheriff")
            public.append("run_for_sheriff")
        private.append("exile_werewolf")
        public.extend(["exile_werewolf", "protect_seer"])
        return [
            _line("system", [], "Daily tasks private: " + ", ".join(private)),
            _line("system", list(self._alive), "Daily tasks: " + ", ".join(public)),
        ]

    def _begin_night(self) -> None:
        """Clear the night counters and keep the previous guard target."""
        self._last_protected = self._protected
        self._protected = None
        self._rounds_left = 5
        self._wolf_votes = {}
        self._final_target = None
        self._dead = []
        self._speech_order = []


_ACTION_NAMES = {
    "guard": "guard_action",
    "werewolf_action": "werewolf_action",
    "werewolf_discussion": "werewolf_discussion",
    "seer": "seer_action",
    "witch": "witch_action",
    "run_for_sheriff": "run_for_sheriff",
    "sheriff_speech": "sheriff_speech",
    "vote_for_sheriff": "vote_for_sheriff",
    "last_words": "last_words",
    "decide_speech_sequence": "decide_speech_sequence",
    "player_speech": "player_speech",
    "vote_action": "vote_action",
    "badge_flow": "badge_flow",
}


def _next_phase(phase: str) -> str:
    """Return the phase that follows an empty ask."""
    order = (
        "guard",
        "werewolf_action",
        "seer",
        "witch",
        "resolve",
        "run_for_sheriff",
        "sheriff_speech",
        "vote_for_sheriff",
        "last_words",
        "decide_speech_sequence",
        "player_speech",
        "vote_action",
        "done",
    )
    if phase not in order:
        return "done"
    return order[order.index(phase) + 1]


def _speech_order(
    players: List[str],
    alive: List[str],
    sheriff: Optional[str],
    starting: str,
    from_left: bool,
) -> List[str]:
    """Return the living speech order, with the sheriff last."""
    ordered = sorted(players)
    if starting not in ordered:
        starting = ordered[0]
    index = ordered.index(starting)
    if from_left:
        order = ordered[index:] + ordered[:index]
    else:
        order = ordered[index::-1] + ordered[:index:-1]
    if sheriff in order:
        order.remove(sheriff)
        order.append(sheriff)
    return [player_id for player_id in order if player_id in alive]


def _line(speaker: str, recipients: List[str], content: str) -> Dict[str, Any]:
    """Build one game line."""
    return {
        "speaker": speaker,
        "recipients": list(recipients),
        "content": content,
    }


def _side_wiped(alive: List[str], roles: Mapping[str, str]) -> bool:
    """Return True when every wolf is dead or every non-wolf is dead."""
    wolves = [player_id for player_id in alive if roles.get(player_id) == "wolf"]
    others = [player_id for player_id in alive if roles.get(player_id) != "wolf"]
    return not wolves or not others


def _body(action: Any) -> Mapping[str, Any]:
    """Return the mapping that holds the tool fields."""
    if not isinstance(action, Mapping):
        return {}
    nested = action.get("action")
    if isinstance(nested, Mapping):
        return nested
    return action


def _flag(source: Mapping[str, Any], name: str) -> bool:
    """Return the boolean value of one tool field."""
    return bool(source.get(name))


def _majority(votes: Mapping[str, str], sheriff: Optional[str]) -> Optional[str]:
    """Return the choice with more than half the weight, or None on a tie."""
    weights: Dict[str, float] = {}
    for voter, choice in votes.items():
        if not choice or choice == "abstain":
            continue
        weight = 1.5 if voter == sheriff else 1.0
        weights[choice] = weights.get(choice, 0.0) + weight
    if not weights:
        return None
    winner = max(weights, key=lambda choice: weights[choice])
    top = weights[winner]
    tied = [choice for choice, weight in weights.items() if weight == top]
    if len(tied) != 1:
        return None
    cast = sum(1.5 if voter == sheriff else 1.0 for voter in votes)
    if top > cast / 2:
        return winner
    return None


def _field(action: Any, name: str) -> Optional[str]:
    """Return one tool field as text."""
    if not isinstance(action, Mapping):
        return None
    nested = action.get("action")
    source = nested if isinstance(nested, Mapping) else action
    value = source.get(name) if isinstance(source, Mapping) else None
    if value is None:
        return None
    return str(value)
