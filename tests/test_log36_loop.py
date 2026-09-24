"""Tests for the log 36 ledger loop with a scripted model."""

from pathlib import Path
from types import SimpleNamespace
import json
import tempfile
import unittest

from experiments.magentic_one.free_loop import run_free_team, write_free_artifacts
from experiments.magentic_one.log36 import DATASET_MISTAKE_STEP, REFERENCE_ANSWER
from experiments.magentic_one.query import ORCHESTRATOR, WEB_SURFER


def _ledger(
    *,
    done: bool,
    making: bool = True,
    looping: bool = False,
    instruction: str = "Open the IMDb list.",
) -> str:
    return json.dumps(
        {
            "is_request_satisfied": {
                "reason": "The request is satisfied." if done else "Netflix is still unchecked.",
                "answer": done,
            },
            "is_in_loop": {"reason": "no", "answer": looping},
            "is_progress_being_made": {"reason": "yes", "answer": making},
            "next_speaker": {"reason": "web", "answer": "WebSurfer"},
            "instruction_or_question": {"reason": "look", "answer": instruction},
        }
    )


class _ScriptedModel:
    """Return queued replies from create."""

    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self.seen: list[list] = []
        self.model_info = {
            "json_output": True,
            "vision": True,
            "function_calling": True,
            "structured_output": False,
        }

    async def create(self, messages: list, **kwargs: object) -> SimpleNamespace:
        if not self._replies:
            raise AssertionError("The scripted model ran out of replies.")
        self.seen.append(messages)
        return SimpleNamespace(content=self._replies.pop(0))


class _Surfer:
    """Record the instruction and return a page report."""

    def __init__(self) -> None:
        self.instructions: list[str] = []
        self.resets = 0

    async def on_messages(self, messages: list, cancellation_token: object = None) -> SimpleNamespace:
        self.instructions.append(messages[0].content)
        return SimpleNamespace(
            chat_message=SimpleNamespace(content="The viewport shows 18 percent of the list.")
        )

    async def on_reset(self, cancellation_token: object = None) -> None:
        self.resets += 1


class TestLog36Loop(unittest.TestCase):
    def test_one_web_step_then_stop_leaves_gold_unlabeled(self) -> None:
        """A satisfied ledger stops the run without copying the dataset step."""
        surfer = _Surfer()
        model = _ScriptedModel(
            [
                "1. GIVEN OR VERIFIED FACTS\nnone",
                "- Ask WebSurfer for the IMDb list.",
                _ledger(done=False),
                _ledger(done=True),
                "Glass Onion: A Knives Out Mystery",
            ]
        )
        result = run_free_team(
            model_client=model,
            web_surfer=surfer,
            max_turns=5,
            max_stalls=3,
        )
        actors = [item["agent"] for item in result["trace"]]
        self.assertEqual(
            actors,
            [
                ORCHESTRATOR,
                ORCHESTRATOR,
                ORCHESTRATOR,
                WEB_SURFER,
                ORCHESTRATOR,
                ORCHESTRATOR,
            ],
        )
        self.assertEqual(surfer.instructions, ["Open the IMDb list."])
        self.assertEqual(result["final_answer"], REFERENCE_ANSWER)
        self.assertIsNone(result["gold"]["gold_who"])
        self.assertIsNone(result["gold"]["gold_when"])
        self.assertNotEqual(result["gold"]["gold_when"], DATASET_MISTAKE_STEP)
        self.assertEqual(result["gold"]["dataset_label"]["mistake_step"], DATASET_MISTAKE_STEP)
        self.assertEqual(result["gold"]["roster"], [ORCHESTRATOR, WEB_SURFER])
        self.assertEqual(result["trace"][3]["action"]["fact"], "The viewport shows 18 percent of the list.")

    def test_stall_replans_before_the_next_progress_step(self) -> None:
        """One stall rewrites the fact sheet and the plan, then resets WebSurfer."""
        surfer = _Surfer()
        model = _ScriptedModel(
            [
                "facts",
                "plan",
                _ledger(done=False, making=False),
                "updated facts",
                "updated plan",
                _ledger(done=True),
                "Glass Onion: A Knives Out Mystery",
            ]
        )
        result = run_free_team(
            model_client=model,
            web_surfer=surfer,
            max_turns=5,
            max_stalls=1,
        )
        parts = [
            item["action"].get("part")
            for item in result["trace"]
            if item["action"].get("type") == "task_ledger"
        ]
        self.assertEqual(parts, ["facts", "plan", "facts", "plan"])
        self.assertEqual(surfer.instructions, [])
        self.assertEqual(surfer.resets, 1)
        self.assertIsNone(result["gold"]["gold_when"])

    def test_round_cap_keeps_the_last_page_report(self) -> None:
        """The final step still sees the last WebSurfer report."""
        surfer = _Surfer()
        model = _ScriptedModel(
            [
                "facts",
                "plan",
                _ledger(done=False),
                "Glass Onion: A Knives Out Mystery",
            ]
        )
        run_free_team(
            model_client=model,
            web_surfer=surfer,
            max_turns=1,
            max_stalls=3,
        )
        final_messages = model.seen[-1]
        blob = " ".join(str(getattr(message, "content", message)) for message in final_messages)
        self.assertIn("18 percent", blob)

    def test_file_run_writes_unlabeled_gold(self) -> None:
        """A file-backed run stores empty who and when labels."""
        surfer = _Surfer()
        model = _ScriptedModel(
            [
                "facts",
                "plan",
                _ledger(done=True),
                "Glass Onion: A Knives Out Mystery",
            ]
        )
        with tempfile.TemporaryDirectory() as folder:
            result = run_free_team(
                model_client=model,
                web_surfer=surfer,
                max_turns=3,
                storage="file",
                output_base=folder,
            )
            written = write_free_artifacts(result, ())
            gold = json.loads(Path(written["gold"]).read_text(encoding="utf-8"))
            self.assertIsNone(gold["gold_who"])
            self.assertIsNone(gold["gold_when"])
            self.assertTrue(Path(written["d0"]).is_file())

    def test_loop_does_not_start_their_group_chat(self) -> None:
        """The free loop does not name their group chat class."""
        source = Path("experiments/magentic_one/free_loop.py").read_text(encoding="utf-8")
        self.assertNotIn("MagenticOneGroupChat", source)
