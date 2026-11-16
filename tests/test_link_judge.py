"""Check the model trace and the judge against a scripted Hidden Profile run."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.information_flow.hidden_profile.parse import parse_doagent
from experiments.information_flow.hidden_profile.run_doagent import run_session
from experiments.information_flow.judge import (
    judge_mismatches,
    judge_prompt,
    record_evidence,
    trace_evidence,
)
from experiments.information_flow.model_trace import (
    ModelTrace,
    decision_prompt,
    recorded_call,
)
from experiments.information_flow.queries import Answer, decode


def _dump(answer: Answer) -> str:
    """Return one exact answer as the JSON a judge would send back."""
    if answer.kind == "unknown":
        return json.dumps({"kind": "unknown"})
    if answer.kind == "exact":
        return json.dumps({"kind": "exact", "value": _jsonable(answer.value)})
    return json.dumps(
        {"kind": "candidates", "candidates": _jsonable(answer.candidates)}
    )


def _jsonable(value: object) -> object:
    """Return a JSON-ready copy of an answer value."""
    if isinstance(value, frozenset):
        return sorted(_jsonable(item) for item in value)
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    return value


class ModelTraceTests(unittest.TestCase):
    """Store one call, and store a provider limit, without a second game run."""

    def test_one_call_writes_the_prompt_and_the_output(self) -> None:
        """A single call leaves one line and no record id."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "traces.jsonl"
            trace = ModelTrace(path)
            output = recorded_call(lambda prompt: "route-hill", "Choose a route.", trace)
            trace.close()
            text = path.read_text(encoding="utf-8")
        self.assertEqual(output, "route-hill")
        self.assertEqual(
            json.loads(text.splitlines()[0]),
            {"output": "route-hill", "prompt": "Choose a route."},
        )
        self.assertEqual(len(text.splitlines()), 1)

    def test_a_record_id_is_refused(self) -> None:
        """The export does not accept a UUID in the prompt or the output."""
        with tempfile.TemporaryDirectory() as folder:
            trace = ModelTrace(Path(folder) / "traces.jsonl")
            prompt = "Look at 12345678-1234-1234-1234-123456789abc before you choose."
            with self.assertRaises(ValueError):
                recorded_call(lambda text: "route-hill", prompt, trace)
            with self.assertRaises(ValueError):
                recorded_call(
                    lambda text: "12345678-1234-1234-1234-123456789abc",
                    "Choose a route.",
                    trace,
                )
            trace.close()
            self.assertEqual(Path(folder).joinpath("traces.jsonl").read_text(encoding="utf-8"), "")

    def test_a_rate_limit_is_stored_and_still_stops_the_call(self) -> None:
        """A rate limit is written on the same call that it blocks."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "traces.jsonl"
            trace = ModelTrace(path)

            def blocked(prompt: str) -> str:
                del prompt
                error = RuntimeError("rate limit exceeded")
                error.status_code = 429  # type: ignore[attr-defined]
                raise error

            with self.assertRaises(RuntimeError):
                recorded_call(blocked, "Choose a route.", trace)
            trace.close()
            line = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(line["blocked"], "rate_limit")
        self.assertEqual(line["prompt"], "Choose a route.")

    def test_a_context_limit_is_stored_and_still_stops_the_call(self) -> None:
        """A context limit is written on the same call that it blocks."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "traces.jsonl"
            trace = ModelTrace(path)

            def blocked(prompt: str) -> str:
                del prompt
                raise RuntimeError("maximum context length exceeded")

            with self.assertRaises(RuntimeError):
                recorded_call(blocked, "Choose a route.", trace)
            trace.close()
            line = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(line["blocked"], "context_limit")

    def test_the_decision_prompt_is_the_observation(self) -> None:
        """The text sent for a decision is the observation and not a record id."""
        prompt = decision_prompt({"held_facts": ["f1"], "phase": "vote"})
        self.assertIn("f1", prompt)
        self.assertNotIn("derived_from", prompt)


class JudgeCalibrationTests(unittest.TestCase):
    """Score a judge on the scripted run, where the exact answers are known."""

    def test_the_same_questions_are_scored_on_both_readings(self) -> None:
        """A matching judge has no errors, and a wrong judge is reported on both readings."""
        with tempfile.TemporaryDirectory() as folder:
            session = run_session(0, logging_level=1, output_base=Path(folder))
            document = json.loads(session.records_path.read_text(encoding="utf-8"))
            events = parse_doagent(session.records_path)
        vote = decode(events, "decision_action", event_id="vote-agent-a")
        group = decode(events, "group_votes", event_id="outcome-group")
        questions = (
            ("Who acted, and what did they choose? Event vote-agent-a.", vote),
            ("Which votes produced the group choice? Event outcome-group.", group),
        )
        evidence = {
            "traces": trace_evidence(events),
            "records": record_evidence(document),
        }
        self.assertNotIn("12345678-1234-1234-1234-123456789abc", evidence["traces"])
        self.assertIn("-", evidence["records"])
        by_question = {question: answer for question, answer in questions}

        def matching(prompt: str) -> str:
            question = prompt.split("Question: ", 1)[1].split("\n", 1)[0]
            return _dump(by_question[question])

        def wrong(prompt: str) -> str:
            del prompt
            return json.dumps({"kind": "unknown"})

        self.assertEqual(judge_mismatches(matching, questions, evidence), ())
        mismatches = judge_mismatches(wrong, questions, evidence)
        self.assertEqual(len(mismatches), 4)
        self.assertEqual({item.reading for item in mismatches}, {"traces", "records"})
        trace_prompt = judge_prompt(questions[0][0], evidence["traces"], "traces")
        record_prompt = judge_prompt(questions[0][0], evidence["records"], "records")
        self.assertIn(questions[0][0], trace_prompt)
        self.assertIn(questions[0][0], record_prompt)
