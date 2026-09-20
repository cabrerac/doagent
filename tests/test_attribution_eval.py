"""Tests for the three-agent addition example and its repeated campaigns."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from experiments._shared import output_bytes_from_path
from experiments.attribution.campaign import (
    ACCURACY_FIELDS,
    COST_FIELDS,
    new_campaign_dir,
    run_accuracy_campaign,
    run_cost_campaign,
    summarise_accuracy,
    summarise_cost,
    update_summary,
    write_rows,
)
from experiments.attribution.evaluate import evaluate_attribution
from experiments.attribution.plots import load_rows, render_campaign
from experiments.attribution.projections import project_logging_level
from experiments.attribution.run import CHECKER, run_addition_team


class TestAdditionTeamExample(unittest.TestCase):
    def test_checker_is_labelled_when_it_accepts_a_wrong_sum(self):
        result = run_addition_team(
            {"a": 3, "b": 4},
            {"plant_wrong_sum": 8, "plant_accept_wrong": True},
            storage="memory",
        )
        gold = result["gold"]
        self.assertEqual(gold["gold_who"], CHECKER)
        self.assertEqual(gold["gold_when"], 2)
        self.assertEqual(result["assignment"], {"assignee": "solver", "op": "add", "a": 3, "b": 4})
        self.assertEqual(result["solver_value"], 8)

        session = result["session"]
        updates = session.inspect("agent_update")
        actors = [r.actor for r in updates]
        self.assertIn("orchestrator", actors)
        self.assertIn("solver", actors)
        self.assertIn("checker", actors)

        checker_view = session.decision_context("checker", kinds="agent_update")
        self.assertTrue(checker_view)
        self.assertTrue(all(r.actor == "orchestrator" for r in checker_view))

        check_updates = [
            r
            for r in updates
            if r.actor == "checker"
            and (r.payload.get("decision") or {})
            .get("response", {})
            .get("choice", {})
            .get("action", {})
            .get("type")
            == "check"
        ]
        self.assertEqual(len(check_updates), 1)
        action = check_updates[0].payload["decision"]["response"]["choice"]["action"]
        self.assertTrue(action["accept"])
        self.assertEqual(action["reported"], 8)
        self.assertEqual(action["correct"], 7)

        artifacts = result["artifacts"]
        self.assertEqual(set(artifacts), {"d0", "d1", "d2", "lookup"})
        self.assertEqual(artifacts["lookup"]["who"], CHECKER)
        self.assertEqual(artifacts["lookup"]["when"], 2)
        self.assertLess(len(artifacts["d0"]), len(artifacts["d2"]))
        self.assertTrue(all(step.get("kind") != "trace" for step in artifacts["d0"]))
        self.assertTrue(
            all(not (step.get("provenance") or {}) for step in artifacts["d0"])
        )
        self.assertFalse(
            any(
                (step.get("payload") or {}).get("decision", {}).get("explanation")
                for step in artifacts["d1"]
            )
        )

    def test_file_run_writes_reproducible_attribution_artifacts(self):
        with tempfile.TemporaryDirectory() as output_base:
            result = run_addition_team(
                {"a": 3, "b": 4},
                {"plant_wrong_sum": 8, "plant_accept_wrong": True},
                storage="file",
                output_base=output_base,
            )

            paths = result["artifact_paths"]
            self.assertEqual(
                set(paths),
                {"d0", "d1", "d2", "lookup", "manifest"},
            )
            for path in paths.values():
                self.assertTrue(Path(path).is_file())

            lookup = json.loads(Path(paths["lookup"]).read_text(encoding="utf-8"))
            self.assertEqual(lookup["who"], CHECKER)
            self.assertEqual(lookup["when"], 2)

            manifest = json.loads(Path(paths["manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["run_id"], result["session"].run_id)
            self.assertEqual(manifest["config"]["query"], {"a": 3, "b": 4})
            self.assertEqual(manifest["config"]["storage"], "file")
            self.assertTrue(manifest["config_hash"])

    def test_evaluate_measures_the_same_addition_run(self):
        result = evaluate_attribution(
            {"a": 3, "b": 4},
            {"plant_wrong_sum": 8, "plant_accept_wrong": True},
            storage="memory",
        )
        self.assertEqual(result.condition["storage"], "memory")
        self.assertEqual(result.condition["capture"], "d2")
        self.assertEqual(result.condition["logging_level"], 2)
        self.assertEqual(result.task_metrics["gold_who"], CHECKER)
        self.assertEqual(result.task_metrics["lookup_who"], CHECKER)
        self.assertEqual(result.task_metrics["lookup_when"], 2)
        self.assertGreaterEqual(result.elapsed_seconds, 0.0)
        self.assertEqual(result.output_bytes, 0)

    def test_projected_d0_matches_logging_rules(self) -> None:
        d2 = [
            {
                "kind": "agent_update",
                "provenance": {"created_by": "solver"},
                "accountability": {"owner": "solver"},
                "payload": {
                    "decision": {
                        "explanation": "drop me",
                        "response": {"reasoning": ["x"], "choice": {"action": {}}},
                    }
                },
            },
            {"kind": "trace", "payload": {"round": 1}, "provenance": {"a": 1}},
            {"kind": "outcome", "payload": {"round": 1}, "provenance": {"a": 1}},
        ]
        d0 = project_logging_level(d2, 0)
        d1 = project_logging_level(d2, 1)
        self.assertEqual([item["kind"] for item in d0], ["agent_update", "outcome"])
        self.assertEqual(d0[0]["provenance"], {})
        self.assertNotIn("explanation", d0[0]["payload"]["decision"])
        self.assertNotIn("reasoning", d0[0]["payload"]["decision"]["response"])
        self.assertEqual([item["kind"] for item in d1], ["agent_update", "trace", "outcome"])
        self.assertEqual(d1[0]["provenance"], {"created_by": "solver"})
        self.assertNotIn("explanation", d1[0]["payload"]["decision"])
        self.assertEqual(project_logging_level(d2, 2), d2)

    def test_live_d0_records_are_smaller_than_d2(self) -> None:
        with tempfile.TemporaryDirectory() as output_base:
            d0 = evaluate_attribution(
                {"a": 3, "b": 4},
                {"plant_wrong_sum": 8, "plant_accept_wrong": True},
                storage="file",
                output_base=output_base,
                logging_level=0,
            )
            d2 = evaluate_attribution(
                {"a": 3, "b": 4},
                {"plant_wrong_sum": 8, "plant_accept_wrong": True},
                storage="file",
                output_base=output_base,
                logging_level=2,
            )
            self.assertEqual(d0.condition["capture"], "d0")
            self.assertEqual(d2.condition["capture"], "d2")
            self.assertLess(d0.output_bytes, d2.output_bytes)
            self.assertGreater(d0.output_bytes, 0)
            self.assertEqual(
                d2.output_bytes,
                output_bytes_from_path(Path(d2.run_path) / "records"),
            )
            self.assertTrue((Path(d2.run_path) / "gold.json").is_file())


def _fake_scores(views, *, method="all_at_once"):
    """Scores shaped like one judged pass, without calling a model."""
    return {
        "gold": {"who": CHECKER, "when": 2},
        "lookup": {
            "who": CHECKER,
            "when": 2,
            "who_match": True,
            "when_match": True,
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        },
        "judges": {
            method: {
                view: {
                    "who": CHECKER,
                    "when": 2,
                    "who_match": True,
                    "when_match": view != "w",
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 10,
                        "total_tokens": 110,
                    },
                }
                for view in views
            }
        },
    }


class TestAttributionCampaign(unittest.TestCase):
    """Repeat counts, long-format rows, and aggregation."""

    QUERY = {"a": 3, "b": 4}
    PLANT = {"plant_wrong_sum": 8, "plant_accept_wrong": True}

    def test_cost_campaign_repeats_every_condition(self) -> None:
        with tempfile.TemporaryDirectory() as output_base:
            campaign_dir = new_campaign_dir(output_base)
            rows = run_cost_campaign(
                self.QUERY,
                self.PLANT,
                campaign_dir=campaign_dir,
                repeats=2,
                conditions=("w", "d2"),
            )
            self.assertEqual(len(rows), 4)
            self.assertEqual([row["repeat"] for row in rows], [1, 2, 1, 2])
            self.assertEqual({row["condition"] for row in rows}, {"w", "d2"})
            self.assertTrue(all(row["capture_bytes"] > 0 for row in rows))
            self.assertTrue(all(row["run_path"] for row in rows))

            summary = summarise_cost(rows)
            self.assertEqual(summary["w"]["elapsed_seconds"]["n"], 2)
            self.assertIn("p10", summary["d2"]["elapsed_seconds"])
            self.assertIn("p90", summary["d2"]["elapsed_seconds"])
            self.assertLess(
                summary["w"]["capture_bytes"]["median"],
                summary["d2"]["capture_bytes"]["median"],
            )

    def test_cost_rows_round_trip_through_csv(self) -> None:
        with tempfile.TemporaryDirectory() as output_base:
            campaign_dir = new_campaign_dir(output_base)
            rows = run_cost_campaign(
                self.QUERY,
                self.PLANT,
                campaign_dir=campaign_dir,
                repeats=1,
                conditions=("w",),
            )
            csv_path = write_rows(campaign_dir / "cost.csv", rows, COST_FIELDS)
            with csv_path.open(newline="", encoding="utf-8") as handle:
                written = list(csv.DictReader(handle))
            self.assertEqual(len(written), 1)
            self.assertEqual(list(written[0]), list(COST_FIELDS))
            self.assertEqual(written[0]["condition"], "w")

    def test_cost_campaign_rejects_zero_repeats(self) -> None:
        with tempfile.TemporaryDirectory() as output_base:
            campaign_dir = new_campaign_dir(output_base)
            with self.assertRaises(ValueError):
                run_cost_campaign(
                    self.QUERY,
                    self.PLANT,
                    campaign_dir=campaign_dir,
                    repeats=0,
                )

    def test_accuracy_campaign_repeats_judging_over_one_execution(self) -> None:
        calls = []

        def fake_judge_runner(run_path, **kwargs):
            calls.append({"run_path": run_path, **kwargs})
            return {"scores": _fake_scores(kwargs["views"])}

        with tempfile.TemporaryDirectory() as output_base:
            campaign_dir = new_campaign_dir(output_base)
            rows = run_accuracy_campaign(
                self.QUERY,
                self.PLANT,
                campaign_dir=campaign_dir,
                executions=1,
                judge_passes=3,
                judge={"methods": ["all_at_once"], "views": ["w", "d2"]},
                judge_runner=fake_judge_runner,
            )

            # Three passes over one execution: 3 x 1 method x 2 views, plus
            # one lookup row for the execution itself.
            self.assertEqual(len(rows), 7)
            self.assertEqual(len(calls), 3)
            self.assertEqual({call["run_path"] for call in calls}, {calls[0]["run_path"]})
            self.assertEqual(
                [call["label"] for call in calls],
                ["pass01", "pass02", "pass03"],
            )
            self.assertEqual(calls[0]["methods"], ("all_at_once",))
            self.assertEqual(calls[0]["views"], ("w", "d2"))

            lookup_rows = [row for row in rows if row["method"] == "lookup"]
            self.assertEqual(len(lookup_rows), 1)
            self.assertEqual(lookup_rows[0]["total_tokens"], 0)
            self.assertEqual(lookup_rows[0]["judge_pass"], "")

            summary = summarise_accuracy(rows)
            self.assertEqual(summary["all_at_once"]["w"]["n"], 3)
            self.assertEqual(summary["all_at_once"]["w"]["who_accuracy"], 1.0)
            self.assertEqual(summary["all_at_once"]["w"]["when_accuracy"], 0.0)
            self.assertEqual(summary["all_at_once"]["d2"]["when_accuracy"], 1.0)
            self.assertEqual(summary["lookup"]["d2"]["both_accuracy"], 1.0)

    def test_accuracy_campaign_writes_collector_packs(self) -> None:
        def fake_judge_runner(run_path, **kwargs):
            return {"scores": _fake_scores(kwargs["views"])}

        with tempfile.TemporaryDirectory() as output_base:
            campaign_dir = new_campaign_dir(output_base)
            rows = run_accuracy_campaign(
                self.QUERY,
                self.PLANT,
                campaign_dir=campaign_dir,
                executions=1,
                judge_passes=1,
                judge={"methods": ["all_at_once"], "views": ["w"]},
                judge_runner=fake_judge_runner,
            )
            run_dirs = list((campaign_dir / "runs").iterdir())
            self.assertEqual(len(run_dirs), 1)
            analysis = run_dirs[0] / "analysis" / "attribution"
            for name in ("who_when.json", "trace_elephant.json", "d0.json", "d2.json"):
                self.assertTrue((analysis / name).is_file(), name)
            gold = json.loads((run_dirs[0] / "gold.json").read_text(encoding="utf-8"))
            self.assertEqual(gold["gold_who"], CHECKER)
            self.assertEqual(rows[0]["gold_who"], CHECKER)

    def test_summary_keeps_earlier_sections(self) -> None:
        with tempfile.TemporaryDirectory() as output_base:
            campaign_dir = new_campaign_dir(output_base)
            update_summary(
                campaign_dir,
                "capture_cost",
                {"repeats": 2},
                config={"query": self.QUERY},
            )
            update_summary(campaign_dir, "attribution", {"judge_passes": 3})
            summary = json.loads(
                (campaign_dir / "summary.json").read_text(encoding="utf-8")
            )
            self.assertEqual(summary["capture_cost"]["repeats"], 2)
            self.assertEqual(summary["attribution"]["judge_passes"], 3)
            self.assertEqual(summary["config"]["query"], self.QUERY)
            self.assertTrue(summary["config_hash"])
            self.assertTrue(summary["campaign_id"].startswith("attribution_campaign_"))


class TestAttributionPlots(unittest.TestCase):
    """Figures are drawn from the CSV files the campaign wrote."""

    def test_campaign_plots_are_written_from_csv(self) -> None:
        cost_rows = [
            {
                "condition": condition,
                "repeat": repeat,
                "elapsed_seconds": 0.01 * repeat,
                "capture_bytes": 100 * repeat,
                "run_id": "",
                "run_path": "",
            }
            for condition in ("w", "d2")
            for repeat in (1, 2)
        ]
        accuracy_rows = [
            {
                "execution": 1,
                "run_id": "run",
                "judge_pass": 1,
                "method": "all_at_once",
                "view": view,
                "predicted_who": CHECKER,
                "predicted_when": 2,
                "gold_who": CHECKER,
                "gold_when": 2,
                "who_match": 1,
                "when_match": 1,
                "both_match": 1,
                "input_tokens": 100,
                "output_tokens": 10,
                "total_tokens": 110,
            }
            for view in ("w", "d2")
        ]
        with tempfile.TemporaryDirectory() as base:
            campaign_dir = Path(base)
            write_rows(campaign_dir / "cost.csv", cost_rows, COST_FIELDS)
            write_rows(campaign_dir / "accuracy.csv", accuracy_rows, ACCURACY_FIELDS)
            written = render_campaign(campaign_dir)
            self.assertEqual(
                set(written),
                {"capture_cost", "attribution_accuracy", "tokens_against_accuracy"},
            )
            for paths in written.values():
                self.assertEqual(set(paths), {"png", "pdf"})
                for path in paths.values():
                    self.assertTrue(Path(path).is_file())
                    self.assertGreater(Path(path).stat().st_size, 0)

    def test_numeric_columns_are_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            path = Path(base) / "cost.csv"
            write_rows(
                path,
                [
                    {
                        "condition": "w",
                        "repeat": 1,
                        "elapsed_seconds": 0.5,
                        "capture_bytes": 42,
                        "run_id": "",
                        "run_path": "",
                    }
                ],
                COST_FIELDS,
            )
            rows = load_rows(path, ("elapsed_seconds", "capture_bytes", "repeat"))
            self.assertEqual(rows[0]["elapsed_seconds"], 0.5)
            self.assertEqual(rows[0]["capture_bytes"], 42)
            self.assertEqual(rows[0]["repeat"], 1)


if __name__ == "__main__":
    unittest.main()
