"""
Offline tests for the ScenePaper MCP server tools.

Exercises tool logic via the registered functions directly — no live HTTP,
no MCP transport needed. A fake HTTP layer patches mcp_server.http_client so
the suite passes without Catalyst being up.
"""
import pytest

# The MCP SDK requires Python >= 3.10, but the Catalyst functions pin this
# repo to 3.9 -- and since the merge to main both test suites share
# src/tests/, `pytest src/tests/` under 3.9 could not even COLLECT this file
# (ModuleNotFoundError), which aborted the whole run including the 98 tests
# that do pass. Skip cleanly instead: run this suite under 3.10+.
pytest.importorskip("mcp", reason="mcp SDK needs Python >= 3.10; see src/mcp_server/requirements.txt")

import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import requests

# Ensure src/ is on the path (mirrors pytest.ini's pythonpath = src)
_src = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _src not in sys.path:
    sys.path.insert(0, _src)

from mcp_server import server  # noqa: E402  (needs sys.path set above)
from mcp_server import http_client  # noqa: E402


def _tool(name):
    """Return the raw tool function by name from the MCPServer registry."""
    tools = server.mcp._tool_manager._tools
    if name not in tools:
        raise KeyError(f"tool {name!r} not registered")
    return tools[name].fn


class TestSearchStoryIdeas(unittest.TestCase):
    def test_returns_candidates_json(self):
        fake = {"candidates": [{"one_liner": "A"}, {"one_liner": "B"}]}
        with patch.object(http_client, "ideate", return_value=fake):
            result = _tool("search_story_ideas")(topic="comeback story")
        parsed = json.loads(result)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["one_liner"], "A")

    def test_empty_candidates(self):
        with patch.object(http_client, "ideate", return_value={"candidates": []}):
            result = _tool("search_story_ideas")(topic="x")
        self.assertEqual(json.loads(result), [])

    def test_http_error_propagates(self):
        with patch.object(
            http_client, "ideate", side_effect=requests.HTTPError("500")
        ):
            with self.assertRaises(requests.HTTPError):
                _tool("search_story_ideas")(topic="x")


class TestGenerateScenePaper(unittest.TestCase):
    def test_returns_started_with_ids(self):
        fake = {"job_id": "job-1", "paper_id": "paper-abc"}
        with patch.object(http_client, "generate", return_value=fake):
            result = _tool("generate_scene_paper")(
                topic="comeback", candidate_one_liner="Guy lost everything"
            )
        parsed = json.loads(result)
        self.assertEqual(parsed["status"], "started")
        self.assertEqual(parsed["job_id"], "job-1")
        self.assertEqual(parsed["paper_id"], "paper-abc")
        self.assertIn("note", parsed)

    def test_note_tells_user_to_poll(self):
        fake = {"job_id": "j", "paper_id": "p"}
        with patch.object(http_client, "generate", return_value=fake):
            result = _tool("generate_scene_paper")(
                topic="x", candidate_one_liner="y"
            )
        self.assertIn("get_scene_paper", json.loads(result)["note"])

    def test_passes_candidate_as_dict(self):
        called_with = {}

        def fake_generate(topic, candidate):
            called_with["candidate"] = candidate
            return {"job_id": "j", "paper_id": "p"}

        with patch.object(http_client, "generate", side_effect=fake_generate):
            _tool("generate_scene_paper")(topic="t", candidate_one_liner="ol")
        self.assertIsInstance(called_with["candidate"], dict)
        self.assertEqual(called_with["candidate"]["one_liner"], "ol")


class TestGetScenePaper(unittest.TestCase):
    def test_returns_paper_json(self):
        fake_paper = {"id": "paper-1", "title": "The Comeback"}
        with patch.object(http_client, "get_paper", return_value=fake_paper):
            result = _tool("get_scene_paper")(paper_id="paper-1")
        self.assertEqual(json.loads(result)["title"], "The Comeback")

    def test_http_error_returns_error_json(self):
        with patch.object(
            http_client, "get_paper", side_effect=Exception("404 Not Found")
        ):
            result = _tool("get_scene_paper")(paper_id="missing")
        parsed = json.loads(result)
        self.assertIn("error", parsed)
        self.assertIn("404", parsed["error"])


class TestVerifySource(unittest.TestCase):
    def test_surfaces_sources_and_status(self):
        fake_paper = {
            "id": "p1",
            "verification_status": "verified",
            "sources": [
                {"title": "WSJ", "confidence_score": 8, "flags": []},
            ],
        }
        with patch.object(http_client, "get_paper", return_value=fake_paper):
            result = _tool("verify_source")(paper_id="p1")
        parsed = json.loads(result)
        self.assertEqual(parsed["verification_status"], "verified")
        self.assertEqual(len(parsed["sources"]), 1)
        self.assertEqual(parsed["sources"][0]["title"], "WSJ")

    def test_missing_paper_returns_error(self):
        with patch.object(
            http_client, "get_paper", side_effect=Exception("404")
        ):
            result = _tool("verify_source")(paper_id="missing")
        self.assertIn("error", json.loads(result))

    def test_empty_sources_array(self):
        fake_paper = {"verification_status": "unverified", "sources": []}
        with patch.object(http_client, "get_paper", return_value=fake_paper):
            result = _tool("verify_source")(paper_id="p2")
        self.assertEqual(json.loads(result)["sources"], [])


class TestStubs(unittest.TestCase):
    def test_generate_voiceover_not_implemented(self):
        result = json.loads(_tool("generate_voiceover")(paper_id="x"))
        self.assertEqual(result["error"], "not_implemented")

    def test_list_available_stories_not_implemented(self):
        result = json.loads(_tool("list_available_stories")(category="suspense"))
        self.assertEqual(result["error"], "not_implemented")

    def test_get_usage_status_not_implemented(self):
        result = json.loads(_tool("get_usage_status")(user_id="u1"))
        self.assertEqual(result["error"], "not_implemented")


class TestAllSevenToolsRegistered(unittest.TestCase):
    def test_all_tools_present(self):
        expected = {
            "search_story_ideas",
            "generate_scene_paper",
            "get_scene_paper",
            "verify_source",
            "generate_voiceover",
            "list_available_stories",
            "get_usage_status",
        }
        registered = set(server.mcp._tool_manager._tools.keys())
        self.assertEqual(registered, expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
