"""Tests for per-agent tool tracing and reasoning merge.

Covers:
  - _TraceCollector wrapping and step capture
  - merge_reasoning logic (tool-only, policy-only, hybrid)
  - SessionAgent.decide() with tools: traces appear in recorded reasoning
  - LLM policy example: act, abstain, error via mock callable
"""

import json
import unittest
from typing import Any, Dict

from doagent import Session, RunConfig
from doagent.core._internal.trace_collector import _TraceCollector, merge_reasoning
from doagent.core.adapters import InMemorySharedData
from examples.llm_policy import llm_decide_factory


# ---------------------------------------------------------------------------
# _TraceCollector unit tests
# ---------------------------------------------------------------------------

class TestTraceCollector(unittest.TestCase):
    def test_wrap_captures_call(self):
        collector = _TraceCollector()
        fn = lambda x, y: x + y
        traced = collector.wrap("add", fn)

        result = traced(3, 4)
        self.assertEqual(result, 7)
        self.assertEqual(len(collector.steps), 1)
        step = collector.steps[0]
        self.assertEqual(step["kind"], "tool")
        self.assertEqual(step["name"], "add")
        self.assertIn("output", step)
        self.assertIn("elapsed_s", step)

    def test_wrap_captures_kwargs(self):
        collector = _TraceCollector()
        fn = lambda *, model, messages: {"content": "hello"}
        traced = collector.wrap("llm", fn)

        result = traced(model="gemini-3.1-flash-lite-preview", messages=[{"role": "user", "content": "hi"}])
        self.assertEqual(result, {"content": "hello"})
        step = collector.steps[0]
        self.assertEqual(step["inputs"]["kwargs"]["model"], "gemini-3.1-flash-lite-preview")

    def test_wrap_captures_error(self):
        collector = _TraceCollector()
        def failing():
            raise ValueError("boom")
        traced = collector.wrap("bad_tool", failing)

        with self.assertRaises(ValueError):
            traced()
        self.assertEqual(len(collector.steps), 1)
        self.assertIn("error", collector.steps[0])
        self.assertEqual(collector.steps[0]["error"], "boom")

    def test_to_dict(self):
        collector = _TraceCollector()
        fn = lambda: 42
        traced = collector.wrap("answer", fn)
        traced()
        d = collector.to_dict()
        self.assertIn("steps", d)
        self.assertEqual(len(d["steps"]), 1)

    def test_empty_collector(self):
        collector = _TraceCollector()
        self.assertEqual(collector.steps, [])
        self.assertEqual(collector.to_dict(), {"steps": []})


# ---------------------------------------------------------------------------
# merge_reasoning tests
# ---------------------------------------------------------------------------

class TestMergeReasoning(unittest.TestCase):
    def test_both_none(self):
        self.assertIsNone(merge_reasoning(None, None))

    def test_policy_only(self):
        pr = {"source": "llm", "text": "I thought..."}
        result = merge_reasoning(pr, None)
        self.assertEqual(result, pr)

    def test_tool_only(self):
        tr = {"steps": [{"kind": "tool", "name": "calc", "output": 42}]}
        result = merge_reasoning(None, tr)
        self.assertEqual(result, tr)

    def test_hybrid(self):
        pr = {"source": "llm", "text": "I thought..."}
        tr = {"steps": [{"kind": "tool", "name": "calc", "output": 42}]}
        result = merge_reasoning(pr, tr)
        self.assertEqual(result["source"], "llm")
        self.assertEqual(result["text"], "I thought...")
        self.assertEqual(len(result["tool_steps"]), 1)

    def test_empty_tool_steps(self):
        pr = {"source": "llm", "text": "..."}
        tr = {"steps": []}
        result = merge_reasoning(pr, tr)
        self.assertEqual(result, pr)


# ---------------------------------------------------------------------------
# SessionAgent.decide() with tools — integration
# ---------------------------------------------------------------------------

class StubEnv:
    agents = ["a"]
    def reset(self, *, seed=None):
        return {"a": {"obs": "hello"}}
    def step(self, actions):
        return {"observations": {"a": {"obs": "done"}}, "rewards": {"a": 0.0}}


def _policy_using_tool(params):
    def decide(request):
        tools = request.get("tools", {})
        calc = tools.get("calc")
        if calc:
            result = calc(2, 3)
        return {"choice": {"status": "act", "action": 1}}
    return decide


def _policy_with_own_reasoning(params):
    def decide(request):
        tools = request.get("tools", {})
        calc = tools.get("calc")
        if calc:
            calc(10, 20)
        return {
            "choice": {"status": "act", "action": 2},
            "reasoning": {"source": "policy", "note": "I computed something"},
        }
    return decide


class TestSessionAgentToolTracing(unittest.TestCase):
    def _make_session_and_agents(self, policy_factory, agent_tools, level=2):
        shared_data = InMemorySharedData()
        session = Session(shared_data, RunConfig(logging_level=level))
        env = session.wrap_env(StubEnv(), env_actor="test_env")

        from doagent.core._internal.policy import PolicyRegistry
        registry = PolicyRegistry()
        registry.register("test_policy", policy_factory)

        configs = [{
            "id": "a",
            "policy": {"name": "test_policy", "params": {}},
            "tools": agent_tools,
        }]
        agents = session.create_agents(configs, registry)
        return session, env, agents, shared_data

    def test_tool_trace_captured_at_level_2(self):
        calc_fn = lambda x, y: x + y
        session, env, agents, sd = self._make_session_and_agents(
            _policy_using_tool, {"calc": calc_fn}, level=2,
        )
        observations = env.reset(seed=1)
        agents["a"].decide(observations["a"], 1)
        env.step({"a": 1})

        records = list(sd.listen("agent_update"))
        self.assertEqual(len(records), 1)
        response = records[0].payload["decision"]["response"]
        self.assertIn("reasoning", response)
        reasoning = response["reasoning"]
        self.assertIn("steps", reasoning)
        self.assertEqual(len(reasoning["steps"]), 1)
        self.assertEqual(reasoning["steps"][0]["name"], "calc")
        self.assertEqual(reasoning["steps"][0]["output"], 5)

    def test_tool_trace_stripped_at_level_1(self):
        calc_fn = lambda x, y: x + y
        session, env, agents, sd = self._make_session_and_agents(
            _policy_using_tool, {"calc": calc_fn}, level=1,
        )
        observations = env.reset(seed=1)
        agents["a"].decide(observations["a"], 1)
        env.step({"a": 1})

        records = list(sd.listen("agent_update"))
        response = records[0].payload["decision"]["response"]
        self.assertNotIn("reasoning", response)

    def test_hybrid_merge_in_record(self):
        calc_fn = lambda x, y: x + y
        session, env, agents, sd = self._make_session_and_agents(
            _policy_with_own_reasoning, {"calc": calc_fn}, level=2,
        )
        observations = env.reset(seed=1)
        agents["a"].decide(observations["a"], 1)
        env.step({"a": 2})

        records = list(sd.listen("agent_update"))
        response = records[0].payload["decision"]["response"]
        reasoning = response["reasoning"]
        self.assertEqual(reasoning["source"], "policy")
        self.assertEqual(reasoning["note"], "I computed something")
        self.assertIn("tool_steps", reasoning)
        self.assertEqual(len(reasoning["tool_steps"]), 1)

    def test_no_tools_no_reasoning(self):
        def plain_policy(params):
            def decide(request):
                return {"choice": {"status": "act", "action": 0}}
            return decide

        session, env, agents, sd = self._make_session_and_agents(
            plain_policy, {}, level=2,
        )
        observations = env.reset(seed=1)
        agents["a"].decide(observations["a"], 1)
        env.step({"a": 0})

        records = list(sd.listen("agent_update"))
        response = records[0].payload["decision"]["response"]
        self.assertNotIn("reasoning", response)


# ---------------------------------------------------------------------------
# LLM policy mock tests (act, abstain, error)
# ---------------------------------------------------------------------------

class TestLLMPolicy(unittest.TestCase):
    def _make_mock_llm(self, response_text):
        def mock_llm(*, model, messages):
            return {"choices": [{"message": {"content": response_text}}]}
        return mock_llm

    def test_act(self):
        mock = self._make_mock_llm('{"action": 2, "confidence": 0.9, "reasoning": "Go right."}')
        factory_params = {
            "action_space": {0: "stay", 1: "left", 2: "right"},
            "confidence_threshold": 0.3,
        }
        decide = llm_decide_factory(factory_params)
        result = decide({"inputs": {"observation": {"x": 1}}, "goal": "move", "tools": {"llm": mock}})
        self.assertEqual(result["choice"]["status"], "act")
        self.assertEqual(result["choice"]["action"], 2)
        self.assertIn("reasoning", result)
        self.assertEqual(result["reasoning"]["text"], "Go right.")

    def test_abstain_low_confidence(self):
        mock = self._make_mock_llm('{"action": null, "confidence": 0.1, "reasoning": "Unsure."}')
        decide = llm_decide_factory({"action_space": {0: "stay"}, "confidence_threshold": 0.3})
        result = decide({"inputs": {"observation": {}}, "goal": "act", "tools": {"llm": mock}})
        self.assertEqual(result["choice"]["status"], "abstain")
        self.assertIsNone(result["choice"]["action"])

    def test_error_bad_json(self):
        mock = self._make_mock_llm("I am not JSON at all!")
        decide = llm_decide_factory({"action_space": {0: "stay"}})
        result = decide({"inputs": {"observation": {}}, "goal": "act", "tools": {"llm": mock}})
        self.assertEqual(result["choice"]["status"], "error")
        self.assertIn("error", result["choice"])

    def test_error_no_llm_tool(self):
        decide = llm_decide_factory({"action_space": {0: "stay"}})
        result = decide({"inputs": {"observation": {}}, "goal": "act", "tools": {}})
        self.assertEqual(result["choice"]["status"], "error")

    def test_error_llm_raises(self):
        def failing_llm(*, model, messages):
            raise ConnectionError("API down")
        decide = llm_decide_factory({"action_space": {0: "stay"}})
        result = decide({"inputs": {"observation": {}}, "goal": "act", "tools": {"llm": failing_llm}})
        self.assertEqual(result["choice"]["status"], "error")
        self.assertIn("API down", result["choice"]["error"])

    def test_custom_prompt_builder(self):
        captured_prompt = {}
        def mock_llm(*, model, messages):
            captured_prompt["user"] = messages[-1]["content"]
            return '{"action": 1, "confidence": 0.8, "reasoning": "custom"}'

        def my_builder(obs, action_space, goal):
            return f"Custom: {goal} with {len(action_space)} actions"

        decide = llm_decide_factory({
            "action_space": {0: "stay", 1: "go"},
            "build_prompt": my_builder,
        })
        result = decide({"inputs": {"observation": {}}, "goal": "test_goal", "tools": {"llm": mock_llm}})
        self.assertEqual(result["choice"]["status"], "act")
        self.assertEqual(captured_prompt["user"], "Custom: test_goal with 2 actions")


if __name__ == "__main__":
    unittest.main(verbosity=2)
