"""Score Hidden Profile views and plot answer share against bytes read.

The rules are the true answers.
A view matches a question when its answer equals the rules.
Both views matching is a tie.
Only the session matching is a win.
Only the other view matching is a loss.
Neither matching is a blank.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path

from experiments.information_flow.hidden_profile.access import COMPONENT_LOGS
from experiments.information_flow.hidden_profile.compare import (
    AGENT_LOGS,
    ONE_LOG,
    ViewAnswers,
    _bridge_message_id,
    _view,
    compare_deals,
)
from experiments.information_flow.hidden_profile.parse import parse_doagent
from experiments.information_flow.hidden_profile.reading import session_reading
from experiments.information_flow.hidden_profile.reference import reference_report
from experiments.information_flow.hidden_profile.rules import (
    DEFAULT_CONFIG,
    HiddenProfileConfig,
    run_episode,
)
from experiments.information_flow.hidden_profile.run_doagent import run_session
from experiments.information_flow.hidden_profile.service_trace import TRACE_NAME
from experiments.information_flow.queries import Answer

LABELS = {
    "D0": "Session level 0",
    "D1": "Session level 1",
    "D2": "Session level 2",
    "S1": "One component log",
    "Sk": "Three agent logs",
    "Sall": "All component logs",
    "Sstructured": "Structured file",
}
_MARBLE = {
    "marble_one": "S1",
    "marble_agents": "Sk",
    "marble_sall": "Sall",
    "marble_structured": "Sstructured",
}
_SESSIONS = ("D0", "D1", "D2")
_MARBLE_NAMES = ("S1", "Sk", "Sall", "Sstructured")


@dataclass(frozen=True)
class ViewScore:
    """How often one view matches the rules, and what it costs to read.

    Args:
        name: Short name of the view.
        label: Name used on the plot.
        matched: Answer slots that equal the rules.
        total: Answer slots that were scored.
        share: Matched slots divided by the total.
        mean_bytes_read: Average bytes read across the deals.
        mean_bytes_stored: Average bytes stored for that view.
    """

    name: str
    label: str
    matched: int
    total: int
    share: float
    mean_bytes_read: float
    mean_bytes_stored: float


@dataclass(frozen=True)
class PairScore:
    """Win, tie, loss, and blank counts for one session level against one view.

    Args:
        session: Session level name.
        marble: MARBLE view name.
        wins: Slots where only the session matches the rules.
        ties: Slots where both match the rules.
        losses: Slots where only the MARBLE view matches the rules.
        blanks: Slots where neither matches the rules.
    """

    session: str
    marble: str
    wins: int
    ties: int
    losses: int
    blanks: int


@dataclass(frozen=True)
class QuestionScore:
    """Win, tie, loss, and blank counts for one question.

    Args:
        name: Question slot.
        session: Session level name.
        marble: MARBLE view name.
        wins: Deals where only the session matches the rules.
        ties: Deals where both match the rules.
        losses: Deals where only the MARBLE view matches the rules.
        blanks: Deals where neither matches the rules.
    """

    name: str
    session: str
    marble: str
    wins: int
    ties: int
    losses: int
    blanks: int


@dataclass(frozen=True)
class ScoreReport:
    """Scored views, pairwise counts, and the plot path.

    Args:
        deals: How many deals were scored.
        views: One row per session level and MARBLE view.
        pairs: One row per session level and MARBLE view.
        questions: One row per question, session level, and MARBLE view.
        score_path: Path of the written score file.
        plot_path: Path of the written plot.
    """

    deals: int
    views: tuple[ViewScore, ...]
    pairs: tuple[PairScore, ...]
    questions: tuple[QuestionScore, ...]
    score_path: Path
    plot_path: Path


def score_deals(
    output_base: str | Path,
    config: HiddenProfileConfig = DEFAULT_CONFIG,
) -> ScoreReport:
    """Score every deal and write the table and the plot.

    Session level 1 and the MARBLE views come from the comparison run.
    Session levels 0 and 2 are played into the same deal folders.

    Args:
        output_base: Directory that receives the score, the plot, and the runs.
        config: Hidden profile configuration.

    Returns:
        The scored views and the pairwise counts.
    """
    folder = Path(output_base)
    folder.mkdir(parents=True, exist_ok=True)
    report = reference_report(config)
    comparisons = compare_deals(folder, config)
    by_deal: dict[int, dict[str, ViewAnswers]] = {}
    for comparison, deal in zip(comparisons, report.deals, strict=True):
        events = run_episode(comparison.index, config, dict(deal.allocation)).events
        message_id = _bridge_message_id(events, report.bridge_fact_id)
        named = {
            _MARBLE.get(view.source, view.source): view
            for view in comparison.views
        }
        named["D1"] = named.pop("doagent")
        deal_folder = folder / f"deal-{comparison.index}"
        for level, name in ((0, "D0"), (2, "D2")):
            session = run_session(
                comparison.index,
                level,
                deal_folder / name,
                config,
                dict(deal.allocation),
            )
            named[name] = _view(
                name,
                parse_doagent(session.records_path),
                message_id,
                report.bridge_fact_id,
                config,
                session_reading(session.records_path),
            )
        by_deal[comparison.index] = named
    views = _view_scores(by_deal, folder)
    pairs, questions = _pair_scores(by_deal)
    score_path = folder / "score.json"
    plot_path = folder / "frontier.png"
    _write_score(score_path, len(comparisons), views, pairs, questions)
    _write_plot(plot_path, views)
    return ScoreReport(
        deals=len(comparisons),
        views=views,
        pairs=pairs,
        questions=questions,
        score_path=score_path,
        plot_path=plot_path,
    )


def _slots(view: ViewAnswers) -> tuple[tuple[str, Answer], ...]:
    """Return each scored answer and its slot name."""
    rows: list[tuple[str, Answer]] = [
        ("recipients", view.recipients),
        ("access_before", view.access_before),
        ("access_after", view.access_after),
        ("sender", view.sender),
        ("group_votes", view.group_votes),
        ("bridge_path", view.bridge_path),
        ("chances", view.chances),
        ("belief_change", view.belief_change),
        ("transition", view.transition),
    ]
    rows.extend((f"votes.{index}", answer) for index, answer in enumerate(view.votes))
    rows.extend((f"bases.{index}", answer) for index, answer in enumerate(view.bases))
    rows.extend(
        (f"vote_match.{index}", answer) for index, answer in enumerate(view.vote_match)
    )
    return tuple(rows)


def _view_scores(
    by_deal: Mapping[int, Mapping[str, ViewAnswers]],
    folder: Path,
) -> tuple[ViewScore, ...]:
    """Return match share and average cost for each view."""
    scores = []
    deal_count = len(by_deal)
    for name in LABELS:
        matched = 0
        total = 0
        read_bytes = 0
        stored_bytes = 0
        for index, views in by_deal.items():
            truth = dict(_slots(views["rules"]))
            for slot, answer in _slots(views[name]):
                total += 1
                if answer == truth[slot]:
                    matched += 1
            reading = views[name].reading
            if reading is None:
                raise ValueError("a scored view must record a reading cost")
            read_bytes += reading.bytes_read
            stored_bytes += _stored_bytes(folder, index, name)
        scores.append(
            ViewScore(
                name=name,
                label=LABELS[name],
                matched=matched,
                total=total,
                share=matched / total,
                mean_bytes_read=read_bytes / deal_count,
                mean_bytes_stored=stored_bytes / deal_count,
            )
        )
    return tuple(scores)


def _stored_bytes(folder: Path, index: int, name: str) -> int:
    """Return the bytes stored for one view of one deal."""
    deal = folder / f"deal-{index}"
    if name in ("D0", "D2"):
        return (deal / name / "records.json").stat().st_size
    if name == "D1":
        return (deal / "doagent" / "records.json").stat().st_size
    logs = deal / "marble" / "logs"
    if name == "S1":
        return (logs / ONE_LOG).stat().st_size
    if name == "Sk":
        return sum((logs / item).stat().st_size for item in AGENT_LOGS)
    if name == "Sall":
        return sum((logs / item).stat().st_size for item in COMPONENT_LOGS)
    if name == "Sstructured":
        return (logs / TRACE_NAME).stat().st_size
    raise ValueError("name must be a scored view")


def _pair_scores(
    by_deal: Mapping[int, Mapping[str, ViewAnswers]],
) -> tuple[tuple[PairScore, ...], tuple[QuestionScore, ...]]:
    """Return pairwise counts for every session level and MARBLE view."""
    pair_counts = {
        (session, marble): [0, 0, 0, 0]
        for session in _SESSIONS
        for marble in _MARBLE_NAMES
    }
    question_counts: dict[tuple[str, str, str], list[int]] = {}
    for views in by_deal.values():
        truth = dict(_slots(views["rules"]))
        for session in _SESSIONS:
            session_slots = dict(_slots(views[session]))
            for marble in _MARBLE_NAMES:
                marble_slots = dict(_slots(views[marble]))
                for name in session_slots:
                    verdict = _verdict(
                        session_slots[name] == truth[name],
                        marble_slots[name] == truth[name],
                    )
                    counts = question_counts.setdefault((name, session, marble), [0, 0, 0, 0])
                    _add(counts, verdict)
                    _add(pair_counts[(session, marble)], verdict)
    pairs = tuple(
        PairScore(session, marble, *counts)
        for (session, marble), counts in pair_counts.items()
    )
    questions = tuple(
        QuestionScore(name, session, marble, *counts)
        for (name, session, marble), counts in question_counts.items()
    )
    return pairs, questions


def _verdict(session_matches: bool, marble_matches: bool) -> str:
    """Return win, tie, loss, or blank from the two match flags.

    Args:
        session_matches: The session answer equals the rules.
        marble_matches: The MARBLE answer equals the rules.

    Returns:
        Tie, win, loss, or blank.
    """
    if session_matches and marble_matches:
        return "tie"
    if session_matches:
        return "win"
    if marble_matches:
        return "loss"
    return "blank"


def _add(counts: list[int], verdict: str) -> None:
    """Add one verdict into a win, tie, loss, blank list."""
    labels = ("win", "tie", "loss", "blank")
    counts[labels.index(verdict)] += 1


def _write_score(
    path: Path,
    deals: int,
    views: Sequence[ViewScore],
    pairs: Sequence[PairScore],
    questions: Sequence[QuestionScore],
) -> None:
    """Write the score table.

    Args:
        path: Destination of the score file.
        deals: How many deals were scored.
        views: Match share and cost for each view.
        pairs: Pairwise counts for each session level and MARBLE view.
        questions: Pairwise counts for each question.
    """
    payload = {
        "deals": deals,
        "population": "all enumerated deals",
        "sample_interval": None,
        "views": [
            {
                "name": view.name,
                "label": view.label,
                "matched": view.matched,
                "total": view.total,
                "share": view.share,
                "mean_bytes_read": view.mean_bytes_read,
                "mean_bytes_stored": view.mean_bytes_stored,
            }
            for view in views
        ],
        "pairs": [
            {
                "session": pair.session,
                "marble": pair.marble,
                "wins": pair.wins,
                "ties": pair.ties,
                "losses": pair.losses,
                "blanks": pair.blanks,
            }
            for pair in pairs
        ],
        "questions": [
            {
                "name": question.name,
                "session": question.session,
                "marble": question.marble,
                "wins": question.wins,
                "ties": question.ties,
                "losses": question.losses,
                "blanks": question.blanks,
            }
            for question in questions
        ],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_plot(path: Path, views: Sequence[ViewScore]) -> None:
    """Save the share of matching answers against average bytes read.

    Args:
        path: Destination of the plot.
        views: One point per view.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(figsize=(8, 5))
    for index, view in enumerate(views):
        axes.scatter(view.mean_bytes_read, view.share)
        axes.annotate(
            view.label,
            (view.mean_bytes_read, view.share),
            textcoords="offset points",
            xytext=(6, 4 + (index % 3) * 10),
            fontsize=8,
        )
    axes.set_xlabel("Average bytes read")
    axes.set_ylabel("Share of answers that match the rules")
    axes.set_ylim(-0.05, 1.05)
    figure.tight_layout()
    figure.savefig(path)
    plt.close(figure)
