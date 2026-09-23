"""Tests for the stand-in Magentic-One team."""

from pathlib import Path
from types import SimpleNamespace
import json
import os
import tempfile
import unittest

from examples._shared.llm_client import LLMResponse
from experiments.attribution.baselines import OutputLogCollector, StepIOCollector
from experiments.attribution.campaign import run_cost_campaign
from experiments.magentic_one.query import FROZEN_QUERY
from experiments.magentic_one.run import (
    _openai_api_key,
    measure_magentic_capture,
    run_recorded,
)
from experiments.attribution.judge import judge_view
from experiments.magentic_one.direct import run_direct_team
from experiments.magentic_one.query import (
    CODER,
    COMPUTER_TERMINAL,
    FILE_SURFER,
    ORCHESTRATOR,
    WEB_SURFER,
)
from experiments.magentic_one.specialists import build_specialists
from experiments.magentic_one.team import run_magentic_team


def _choices(session):
    """Return decision choices that carry an action.

    Args:
        session:
            Finished session.

    Returns:
        Actor and action pairs, in record order.
    """
    found = []
    for record in session.inspect("agent_update"):
        decision = (record.payload or {}).get("decision") or {}
        response = decision.get("response") or {}
        action = (response.get("choice") or {}).get("action")
        if isinstance(action, dict):
            found.append((record.actor, action))
    return found


class TestMagenticStandIn(unittest.TestCase):
    def test_accept_last_labels_the_orchestrator(self):
        result = run_magentic_team(storage="memory")
        gold = result["gold"]
        self.assertEqual(gold["gold_who"], ORCHESTRATOR)
        self.assertEqual(gold["gold_when"], 4)
        self.assertEqual(result["web_result"]["fact"], "M-19")
        self.assertEqual(result["file_result"]["fact"], "M-17")
        self.assertEqual(result["assignment"]["assignee"], WEB_SURFER)
        self.assertIn("Accept a code only when the two agree.", result["assignment"]["plan"])

        choices = _choices(result["session"])
        self.assertEqual(
            [actor for actor, _action in choices],
            [ORCHESTRATOR, WEB_SURFER, ORCHESTRATOR, FILE_SURFER, ORCHESTRATOR],
        )
        self.assertEqual(choices[-1][1]["type"], "accept")
        self.assertEqual(choices[-1][1]["fact"], "M-19")

    def test_idle_specialists_do_not_decide(self):
        result = run_magentic_team(storage="memory")
        actors = {actor for actor, _action in _choices(result["session"])}
        self.assertIn(FILE_SURFER, actors)
        self.assertNotIn(CODER, actors)
        self.assertNotIn(COMPUTER_TERMINAL, actors)

    def test_explanations_omit_the_true_answer(self):
        result = run_magentic_team(storage="memory")
        for record in result["session"].inspect("agent_update"):
            decision = (record.payload or {}).get("decision") or {}
            response = decision.get("response") or {}
            explanation = response.get("explanation") or ""
            lowered = explanation.lower()
            for banned in ("wrong", "plant", "correct", "paris"):
                self.assertNotIn(banned, lowered)

    def test_other_modes_are_rejected(self):
        with self.assertRaises(ValueError):
            run_magentic_team(plant={"mode": "none"}, storage="memory")

    def test_direct_run_matches_session_gold(self):
        session_run = run_magentic_team(storage="memory")
        direct_run = run_direct_team()
        self.assertEqual(direct_run["gold"]["gold_who"], session_run["gold"]["gold_who"])
        self.assertEqual(direct_run["gold"]["gold_when"], session_run["gold"]["gold_when"])
        self.assertEqual(direct_run["web_result"]["fact"], session_run["web_result"]["fact"])
        self.assertEqual(
            direct_run["assignment"]["assignee"],
            session_run["assignment"]["assignee"],
        )

    def test_collectors_share_the_step_clock(self):
        session_w = OutputLogCollector()
        session_t = StepIOCollector()
        session_run = run_magentic_team(
            collectors=(session_w, session_t),
            storage="memory",
        )
        direct_w = OutputLogCollector()
        direct_t = StepIOCollector()
        direct_run = run_direct_team(collectors=(direct_w, direct_t))

        self.assertEqual([step["step"] for step in session_w.steps()], [0, 1, 2, 3, 4])
        self.assertEqual(
            [step["agent"] for step in session_w.steps()],
            [step["agent"] for step in direct_w.steps()],
        )
        self.assertTrue(all("content" in step and "input" not in step for step in session_w.steps()))
        self.assertEqual(
            [(step["step"], step["agent"]) for step in session_t.steps()],
            [(step["step"], step["agent"]) for step in direct_t.steps()],
        )
        self.assertTrue(all("input" in step and "output" in step for step in session_t.steps()))
        self.assertEqual(session_run["gold"]["gold_who"], direct_run["gold"]["gold_who"])
        self.assertEqual(session_run["gold"]["gold_when"], direct_run["gold"]["gold_when"])

    def test_judge_prompt_names_the_stored_roster(self):
        """The judge names the stored roster."""
        run = run_magentic_team(storage="memory")
        seen = {}

        def client(*, model, temperature, messages):
            seen["system"] = messages[0]["content"]
            return LLMResponse(
                text='{"who": "orchestrator", "when": 2, "reason": "accepted"}',
                provider="fake",
                requested_model=model,
                response_model=model,
                usage={"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            )

        judge_view(
            method="all_at_once",
            view="w",
            task=run["gold"]["query"],
            evidence=[{"step": 0, "agent": ORCHESTRATOR, "content": "assign"}],
            client=client,
            roster=run["gold"]["roster"],
        )
        prompt = seen["system"]
        for name in (ORCHESTRATOR, WEB_SURFER, FILE_SURFER, CODER, COMPUTER_TERMINAL):
            self.assertIn(name, prompt)
        self.assertNotIn("solver", prompt)
        self.assertNotIn("checker", prompt)

    def test_supplied_web_surfer_answers_through_on_messages(self):
        """A supplied WebSurfer is asked through on_messages."""

        class _Surfer:
            def __init__(self):
                self.messages = []
                self.closed = False

            async def on_messages(self, messages, cancellation_token):
                self.messages.extend(messages)
                return SimpleNamespace(chat_message=SimpleNamespace(content="Lyon"))

            async def close(self):
                self.closed = True

        surfer = _Surfer()
        result = run_magentic_team(storage="memory", specialists={WEB_SURFER: surfer})
        self.assertEqual(result["web_result"]["fact"], "Lyon")
        self.assertEqual(result["web_result"]["type"], "web_result")
        self.assertEqual(surfer.messages[0].content, "What is the shelf code for crate 4817?")
        self.assertTrue(surfer.closed)
        accepted = _choices(result["session"])[-1][1]
        self.assertEqual(accepted["type"], "accept")
        self.assertEqual(accepted["fact"], "Lyon")

    def test_build_specialists_uses_the_autogen_names(self):
        """The builder constructs four specialists with the AutoGen names."""
        seen = {}

        def _klass(label):
            class _Agent:
                def __init__(self, name, **kwargs):
                    seen[label] = (name, kwargs)

            return _Agent

        client = object()
        executor = object()
        built = build_specialists(
            client,
            executor,
            classes={
                "web": _klass("web"),
                "file": _klass("file"),
                "coder": _klass("coder"),
                "terminal": _klass("terminal"),
            },
        )
        self.assertEqual(
            set(built),
            {WEB_SURFER, FILE_SURFER, CODER, COMPUTER_TERMINAL},
        )
        self.assertEqual(
            seen["web"],
            ("WebSurfer", {"model_client": client, "headless": True}),
        )
        self.assertEqual(seen["file"], ("FileSurfer", {"model_client": client}))
        self.assertEqual(seen["coder"], ("Coder", {"model_client": client}))
        self.assertEqual(
            seen["terminal"],
            ("ComputerTerminal", {"code_executor": executor}),
        )

    def test_recorded_run_writes_gold_and_packs(self):
        """A file run writes gold, collector packs, and session views."""

        class _Surfer:
            async def on_messages(self, messages, cancellation_token):
                return SimpleNamespace(chat_message=SimpleNamespace(content="Lyon"))

        who = OutputLogCollector()
        trace = StepIOCollector()
        with tempfile.TemporaryDirectory() as folder:
            result = run_recorded(
                specialists={WEB_SURFER: _Surfer()},
                collectors=(who, trace),
                storage="file",
                output_base=folder,
            )
            gold_path = Path(result["artifact_paths"]["gold"])
            gold = json.loads(gold_path.read_text(encoding="utf-8"))
            self.assertEqual(gold["gold_who"], ORCHESTRATOR)
            self.assertEqual(gold["roster"][1], WEB_SURFER)
            who_path = Path(result["artifact_paths"]["w"])
            trace_path = Path(result["artifact_paths"]["t"])
            self.assertEqual(who_path.name, "who_when.json")
            self.assertEqual(trace_path.name, "trace_elephant.json")
            self.assertTrue(who_path.is_file())
            self.assertTrue(trace_path.is_file())
            analysis = gold_path.parent / "analysis" / "attribution"
            for name in ("d0.json", "d1.json", "d2.json"):
                payload = json.loads((analysis / name).read_text(encoding="utf-8"))
                self.assertIsInstance(payload, list)
                self.assertTrue(payload)
            lookup = json.loads((analysis / "lookup.json").read_text(encoding="utf-8"))
            self.assertIsNone(lookup)

    def test_real_specialist_classes_construct(self):
        """The installed AutoGen classes construct without calling a model."""

        class _Client:
            model_info = {"function_calling": True, "vision": True}

        from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor

        built = build_specialists(_Client(), LocalCommandLineCodeExecutor())
        self.assertEqual(
            set(built),
            {WEB_SURFER, FILE_SURFER, CODER, COMPUTER_TERMINAL},
        )
        for agent in built.values():
            self.assertTrue(callable(agent.on_messages))

    def test_cost_repeat_labels_the_orchestrator(self):
        """One Magentic cost repeat stores orchestrator gold."""
        with tempfile.TemporaryDirectory() as folder:
            rows = run_cost_campaign(
                FROZEN_QUERY,
                {"mode": "accept_last", "wrong_fact": "M-19", "ledger_fact": "M-17"},
                campaign_dir=folder,
                repeats=1,
                conditions=("d2",),
                capture_runner=measure_magentic_capture,
            )
            gold = json.loads(
                (Path(rows[0]["run_path"]) / "gold.json").read_text(encoding="utf-8")
            )
            self.assertEqual(gold["gold_who"], ORCHESTRATOR)
            self.assertEqual(gold["gold_when"], 4)
            self.assertEqual(len(rows), 1)

    def test_openai_key_is_read_from_dotenv(self):
        """A .env file supplies the OpenAI key."""
        from examples._shared.env_file import load_dotenv

        names = ("OPENAI_API_KEY", "DOAGENT_OPENAI_API_KEY")
        saved = {name: os.environ.pop(name, None) for name in names}
        try:
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / ".env"
                path.write_text("OPENAI_API_KEY=from-file\n", encoding="utf-8")
                load_dotenv(path)
                self.assertEqual(_openai_api_key(), "from-file")
        finally:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value
