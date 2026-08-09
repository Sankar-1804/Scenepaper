"""
ScenePaper MCP server — wraps the live Catalyst Gateway pipeline as tool calls.

Run via stdio (for Claude Desktop / any MCP client):
    python -m mcp_server.server

Or import `mcp` directly in tests to exercise tool logic without a transport.

Architecture (confirmed 2026-08-09): standalone Python process, HTTP calls to
the three live Gateway routes. Not hosted inside Catalyst — sidesteps the
REST-only gateway and 30s Advanced I/O cap.

Seven tools per CLAUDE.md spec:
  search_story_ideas     — POST /ideate                        (built)
  generate_scene_paper   — POST /generate  async, returns job  (built)
  get_scene_paper        — GET  /paper?id=                     (built)
  verify_source          — GET  /paper?id=, surfaces sources[] (built)
  generate_voiceover     — depends on TTS work (not built yet) (stub)
  list_available_stories — needs category-filter route (stub)  (stub)
  get_usage_status       — needs UserProfile counter (stub)     (stub)
"""

import json
from mcp.server.mcpserver import MCPServer
from mcp_server import http_client as _http

mcp = MCPServer(
    name="scenepaper",
    version="0.1.0",
    description=(
        "ScenePaper pipeline: search verified story ideas, generate "
        "scene papers, retrieve and inspect them."
    ),
)


# ---------------------------------------------------------------------------
# Tool 1 — search_story_ideas
# ---------------------------------------------------------------------------

@mcp.tool(
    name="search_story_ideas",
    description=(
        "Search for 3–4 verified story candidates on a topic. Returns "
        "one-liner summaries with verification scores. The user picks one "
        "candidate before calling generate_scene_paper."
    ),
)
def search_story_ideas(topic: str) -> str:
    """
    Args:
        topic: The subject or theme to search, e.g. 'underdog comeback story'.
    Returns:
        JSON list of candidate one-liners with scores.
    """
    data = _http.ideate(topic)
    candidates = data.get("candidates", [])
    return json.dumps(candidates, indent=2)


# ---------------------------------------------------------------------------
# Tool 2 — generate_scene_paper
# ---------------------------------------------------------------------------

@mcp.tool(
    name="generate_scene_paper",
    description=(
        "Start the full structuring pipeline for a chosen story candidate. "
        "This is ASYNC — it returns a job_id and paper_id immediately; the "
        "paper is not ready yet. Poll get_scene_paper(paper_id) until it "
        "appears. Generation takes 15–30+ seconds."
    ),
)
def generate_scene_paper(topic: str, candidate_one_liner: str) -> str:
    """
    Args:
        topic: The original topic string used in search_story_ideas.
        candidate_one_liner: The one-liner text of the candidate the user chose.
    Returns:
        JSON with job_id and paper_id. Paper is not ready yet — poll
        get_scene_paper with the returned paper_id.
    """
    candidate = {"one_liner": candidate_one_liner}
    data = _http.generate(topic, candidate)
    return json.dumps(
        {
            "status": "started",
            "job_id": data.get("job_id"),
            "paper_id": data.get("paper_id"),
            "note": (
                "Paper is generating. Call get_scene_paper(paper_id) "
                "in ~20 seconds to check if it is ready."
            ),
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Tool 3 — get_scene_paper
# ---------------------------------------------------------------------------

@mcp.tool(
    name="get_scene_paper",
    description=(
        "Retrieve a full ScenePaper by its ID, including hooks, scenes, "
        "pacing marks, delivery notes, and source verification details. "
        "Returns a 404-style error if the paper does not exist yet."
    ),
)
def get_scene_paper(paper_id: str) -> str:
    """
    Args:
        paper_id: The paper_id returned by generate_scene_paper.
    Returns:
        Full ScenePaper JSON document, or an error message if not found.
    """
    try:
        paper = _http.get_paper(paper_id)
        return json.dumps(paper, indent=2)
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tool 4 — verify_source
# ---------------------------------------------------------------------------

@mcp.tool(
    name="verify_source",
    description=(
        "Surface the source verification details for a ScenePaper: each "
        "source's confidence score, trust flags (e.g. 'single source only', "
        "'sources conflict'), and whether any sources were suppressed. Shows "
        "overall verification_status of the paper."
    ),
)
def verify_source(paper_id: str) -> str:
    """
    Args:
        paper_id: The ID of the paper to inspect.
    Returns:
        JSON with verification_status and the full sources[] array.
    """
    try:
        paper = _http.get_paper(paper_id)
        return json.dumps(
            {
                "paper_id": paper_id,
                "verification_status": paper.get("verification_status"),
                "sources": paper.get("sources", []),
            },
            indent=2,
        )
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# Tools 5–7 — stubs for unbuilt dependencies
# The tools are registered so a client can see them; they return an honest
# "not implemented" rather than fabricated data.
# ---------------------------------------------------------------------------

@mcp.tool(
    name="generate_voiceover",
    description=(
        "Regenerate the voiceover audio for a ScenePaper. "
        "NOT YET IMPLEMENTED — depends on TTS integration from "
        "api-integration-agent."
    ),
)
def generate_voiceover(paper_id: str) -> str:  # noqa: ARG001
    return json.dumps(
        {
            "error": "not_implemented",
            "detail": (
                "generate_voiceover is not yet available. "
                "It depends on the TTS pipeline from api-integration-agent."
            ),
        }
    )


@mcp.tool(
    name="list_available_stories",
    description=(
        "Browse ScenePapers filtered by category "
        "(suspense / cautionary / human_interest / curious). "
        "NOT YET IMPLEMENTED — depends on a category-filter route."
    ),
)
def list_available_stories(category: str) -> str:  # noqa: ARG001
    return json.dumps(
        {
            "error": "not_implemented",
            "detail": (
                "list_available_stories is not yet available. "
                "It depends on a category-filtered list route that has not "
                "been built yet."
            ),
        }
    )


@mcp.tool(
    name="get_usage_status",
    description=(
        "Check how many free ScenePaper generations a user has remaining "
        "and whether their export is locked. "
        "NOT YET IMPLEMENTED — depends on the UserProfile counter."
    ),
)
def get_usage_status(user_id: str) -> str:  # noqa: ARG001
    return json.dumps(
        {
            "error": "not_implemented",
            "detail": (
                "get_usage_status is not yet available. "
                "It depends on the UserProfile counter endpoint."
            ),
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
