"""
scenepaper_pipeline -- Advanced I/O Function (front door only)

Per the session decision referenced in issue #8 / issue #2: Catalyst Advanced
I/O Functions have a hard 30-second execution timeout, so this function must
NEVER run the actual content pipeline (search, verify, structure, TTS,
images, NoSQL write). Its only jobs are:
  1. Route incoming HTTP requests to the right handler.
  2. Validate inputs minimally.
  3. For CRUD on ScenePaper, read/write via the Catalyst NoSQL ScenePaper
     table (issue #1 resolved -- tables exist in console, nested fields are
     native JSON documents, no serialization needed).
  4. For POST /generate, kick off the long-running pipeline as a Job
     (Create_Immediate_Job pattern, via zcatalyst_sdk's job_scheduling
     service) targeting the `scenepaper_pipeline_job` Job function (15-min
     budget) and return the job id immediately. The actual pipeline logic
     lives in that Job function, not here -- and even there, the
     search/verify/structure/TTS/image stages are api-integration-agent's
     scope (issues #9, #10), stubbed with TODO markers, not implemented.

Routes (per CLAUDE.md's MCP tool list / entity schema, catalyst-agent scope
per docs/task-breakdown.md Phase 1 + issue #8):
  POST   /ideate       -> validate topic, return candidate one-liners
                           (search/verify itself is api-integration-agent's
                           scope, issue #9 -- stubbed here)
  POST   /generate      -> validate chosen candidate, submit pipeline Job,
                           return job_id + paper_id immediately
  GET    /paper/:id     -> read one ScenePaper document from NoSQL
  PUT    /paper/:id     -> update one ScenePaper document in NoSQL
  DELETE /paper/:id     -> delete one ScenePaper document from NoSQL

NOT implemented here (out of scope for catalyst-agent):
  - SearXNG search, verification scoring (Call A), structuring (Call B),
    TTS, image fetch (api-integration-agent's scope, issues #9/#10)
  - UserProfile reads/writes (no route currently touches UserProfile --
    follow-up once api-integration-agent wires user_id/profile lookups)
"""

import json
import logging
import os
import re
import uuid

from flask import Request, jsonify, make_response
import zcatalyst_sdk

logger = logging.getLogger()

_PAPER_ID_RE = re.compile(r"^/paper/([^/]+)/?$")


# --------------------------------------------------------------------------
# Response helpers
# --------------------------------------------------------------------------

def _json_response(status_code: int, payload: dict):
    return make_response(jsonify(payload), status_code)


def _error(status_code: int, message: str):
    return _json_response(status_code, {"status": "error", "message": message})


# --------------------------------------------------------------------------
# NoSQL CRUD -- ScenePaper table (issue #1 resolved)
#
# Real tables exist in the Catalyst console: ScenePaper (partition key: id)
# and UserProfile (partition key: id). All nested fields are native JSON
# documents -- no serialization step needed.
#
# SDK surface (zcatalyst_sdk.nosql, verified from installed package):
#   table.insert_items({'item': {...}})        -> NoSqlResponse (.create list)
#   table.fetch_item({'keys': [{'id': ...}]}) -> NoSqlResponse (.get list)
#   table.update_items({'keys': ..., 'update_attributes': [...]})
#   table.delete_items({'keys': {'id': ...}})
#
# NOTE: update_value shape {'value': v} is from the type stubs; verify with
# one live call before trusting for non-scalar values (arrays, nested dicts).
# --------------------------------------------------------------------------

def _get_nosql_table(name: str):
    return zcatalyst_sdk.initialize().nosql().get_table(name)


def _create_scenepaper(payload: dict) -> dict:
    item = {'id': payload.get('id') or str(uuid.uuid4()), **payload}
    table = _get_nosql_table('ScenePaper')
    table.insert_items({'item': item})
    return item


def _get_scenepaper(paper_id: str):
    table = _get_nosql_table('ScenePaper')
    try:
        result = table.fetch_item({'keys': [{'id': paper_id}]})
    except Exception:
        return None
    items = result.get or []
    if not items:
        return None
    return items[0].get('item')


def _update_scenepaper(paper_id: str, updates: dict):
    existing = _get_scenepaper(paper_id)
    if existing is None:
        return None
    table = _get_nosql_table('ScenePaper')
    update_attrs = [
        {'operation_type': 'PUT', 'attribute_path': [k], 'update_value': {'value': v}}
        for k, v in updates.items()
    ]
    table.update_items({'keys': {'id': paper_id}, 'update_attributes': update_attrs})
    existing.update(updates)
    return existing


def _delete_scenepaper(paper_id: str) -> bool:
    existing = _get_scenepaper(paper_id)
    if existing is None:
        return False
    table = _get_nosql_table('ScenePaper')
    table.delete_items({'keys': {'id': paper_id}})
    return True


# --------------------------------------------------------------------------
# Stub ideation search -- TODO(issue #9)
#
# search_story_ideas is api-integration-agent's scope (SearXNG query
# building, domain-quality scoring, clustering -- see CLAUDE.md's "Search,
# verification & trust model" section). Not implemented here.
# --------------------------------------------------------------------------

def _stub_run_ideation_search(topic: str) -> list:
    """
    TODO(issue #9): Replace with the real ideation pipeline: classify
    broad-vs-specific, build the query set, run it against SearXNG,
    domain-quality-score + filter, cluster into distinct candidates,
    summarize each cluster into a one-liner. Always surface the top 3
    regardless of score (see CLAUDE.md trust model -- no silent
    suppression except fabrication/satire/AI-content-farms).
    For now: returns 3 canned placeholder candidates so /ideate's routing
    and response shape can be exercised locally without SearXNG.
    """
    return [
        {
            "one_liner": f"[stub] Candidate A for '{topic}'",
            "confidence_score": None,
            "flags": [],
        },
        {
            "one_liner": f"[stub] Candidate B for '{topic}'",
            "confidence_score": None,
            "flags": [],
        },
        {
            "one_liner": f"[stub] Candidate C for '{topic}'",
            "confidence_score": None,
            "flags": [],
        },
    ]


# --------------------------------------------------------------------------
# Job submission -- Create_Immediate_Job pattern (issue #8 / issue #2)
# --------------------------------------------------------------------------

def _submit_pipeline_job(job_params: dict) -> dict:
    """
    Submit the long-running pipeline (search -> verify -> structure -> TTS
    -> images -> NoSQL write) as an immediate Job targeting the
    `scenepaper_pipeline_job` Job function, per the Create_Immediate_Job
    pattern. This is the only way the actual pipeline work happens -- this
    Advanced I/O function's 30s budget is nowhere near enough.

    Requires a Job Pool (target_type=Function, pointing at the deployed
    scenepaper_pipeline_job Job function) to exist in this Catalyst project.

    Job pool "scenepaper_job_pool" (id 59024000000020001) and the deployed
    scenepaper_pipeline_job function (id 59024000000021001) were created
    this session via the Catalyst MCP + CLI. Hardcoded as the default below
    rather than read purely from env vars: Catalyst Functions turned out to
    have no platform-level environment-variable support at all (confirmed
    via both the CLI's `functions:config` -- only --memory is configurable
    -- and the MCP's env-var tools, which are scoped to AppSail deployment
    resources, not Functions). Overridable via env var if that ever
    changes, or for local/test overrides.
    """
    jobpool_id = os.environ.get("SCENEPAPER_JOBPOOL_ID", "59024000000020001")
    jobpool_name = os.environ.get("SCENEPAPER_JOBPOOL_NAME", "scenepaper_job_pool")
    job_function_id = os.environ.get("SCENEPAPER_JOB_FUNCTION_ID", "59024000000021001")
    job_function_name = os.environ.get(
        "SCENEPAPER_JOB_FUNCTION_NAME", "scenepaper_pipeline_job"
    )

    if not jobpool_id or not job_function_id:
        raise RuntimeError(
            "Pipeline job pool/function not configured yet -- set "
            "SCENEPAPER_JOBPOOL_ID and SCENEPAPER_JOB_FUNCTION_ID once the "
            "job pool is created and scenepaper_pipeline_job is deployed "
            "(HIL provisioning step, see issue #8)."
        )

    app = zcatalyst_sdk.initialize()
    job_meta = {
        "job_name": f"scenepaper_generate_{uuid.uuid4().hex[:10]}",
        "jobpool_id": jobpool_id,
        "jobpool_name": jobpool_name,
        "target_type": "Function",
        "target_id": job_function_id,
        "target_name": job_function_name,
        # Job params must be a flat Dict[str, str] -- nested structures
        # (e.g. the chosen candidate) are JSON-encoded.
        "params": {key: str(value) for key, value in job_params.items()},
    }
    return app.job_scheduling().job().submit_job(job_meta)


# --------------------------------------------------------------------------
# Route handlers
# --------------------------------------------------------------------------

def _handle_ideate(request: Request):
    body = request.get_json(silent=True) or {}
    topic = body.get("topic")
    if not isinstance(topic, str) or not topic.strip():
        return _error(400, "'topic' is required and must be a non-empty string")

    candidates = _stub_run_ideation_search(topic.strip())
    return _json_response(200, {"status": "success", "topic": topic, "candidates": candidates})


def _handle_generate(request: Request):
    body = request.get_json(silent=True) or {}
    topic = body.get("topic")
    candidate = body.get("candidate")

    if not isinstance(topic, str) or not topic.strip():
        return _error(400, "'topic' is required and must be a non-empty string")
    if not isinstance(candidate, dict) or not candidate:
        return _error(
            400,
            "'candidate' is required and must be the chosen candidate object "
            "returned from POST /ideate",
        )

    # Generate the paper id up front so the caller can immediately start
    # polling GET /paper/:id -- the job function writes to this id once the
    # real NoSQL write lands (issue #1). This is an implementation choice
    # made to keep /generate's response self-sufficient; it doesn't touch
    # NoSQL schema or pipeline logic, so it's within this session's scope.
    paper_id = body.get("paper_id") or str(uuid.uuid4())

    job_params = {
        "paper_id": paper_id,
        "topic": topic.strip(),
        "candidate": json.dumps(candidate),
        "user_id": body.get("user_id", ""),
    }

    try:
        job_result = _submit_pipeline_job(job_params)
    except RuntimeError as exc:
        logger.error("Pipeline job not submitted: %s", exc)
        return _error(503, str(exc))
    except Exception:  # pragma: no cover - defensive, real SDK/network errors
        logger.exception("Failed to submit pipeline job")
        return _error(502, "Failed to submit pipeline job")

    job_id = job_result.get("job_id") if isinstance(job_result, dict) else None
    return _json_response(
        202,
        {
            "status": "accepted",
            "job_id": job_id,
            "paper_id": paper_id,
            "message": (
                "Scene paper generation started. Poll GET /paper/:id with "
                "the returned paper_id once the job completes."
            ),
        },
    )


def _handle_get_paper(paper_id: str):
    if not paper_id:
        return _error(400, "paper id is required")

    row = _get_scenepaper(paper_id)
    if row is None:
        return _error(404, f"no ScenePaper found with id '{paper_id}'")
    return _json_response(200, {"status": "success", "paper": row})


def _handle_put_paper(request: Request, paper_id: str):
    if not paper_id:
        return _error(400, "paper id is required")

    updates = request.get_json(silent=True)
    if not isinstance(updates, dict) or not updates:
        return _error(400, "request body must be a non-empty JSON object of fields to update")

    row = _update_scenepaper(paper_id, updates)
    if row is None:
        return _error(404, f"no ScenePaper found with id '{paper_id}'")
    return _json_response(200, {"status": "success", "paper": row})


def _handle_delete_paper(paper_id: str):
    if not paper_id:
        return _error(400, "paper id is required")

    deleted = _delete_scenepaper(paper_id)
    if not deleted:
        return _error(404, f"no ScenePaper found with id '{paper_id}'")
    return _json_response(200, {"status": "success", "message": f"deleted '{paper_id}'"})


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def handler(request: Request):
    """
    Catalyst Advanced I/O Function entry point. Dispatches manually on
    request.method / request.path -- Advanced I/O functions receive a raw
    Flask-style Request, there's no app.route() decorator wiring (matches
    the "hello world" scaffold's style this replaces).

    API Gateway route wiring (so this is reachable by path) is a separate,
    still-blocked step per issue #8 -- not done in this session.
    """
    method = request.method
    path = request.path or "/"

    if path == "/" and method == "GET":
        return _json_response(200, {"status": "success", "message": "scenepaper_pipeline is up"})

    if path == "/ideate" and method == "POST":
        return _handle_ideate(request)

    if path == "/generate" and method == "POST":
        return _handle_generate(request)

    paper_match = _PAPER_ID_RE.match(path)
    if paper_match:
        paper_id = paper_match.group(1)
        if method == "GET":
            return _handle_get_paper(paper_id)
        if method == "PUT":
            return _handle_put_paper(request, paper_id)
        if method == "DELETE":
            return _handle_delete_paper(paper_id)
        return _error(405, f"method '{method}' not allowed on /paper/:id")

    return _error(404, f"unknown route: {method} {path}")
