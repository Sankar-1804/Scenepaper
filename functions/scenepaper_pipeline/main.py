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
from zcatalyst_sdk.nosql.transfom import Item as _NoSqlItem
from zcatalyst_sdk.nosql.types import TypeSerializer as _NoSqlTypeSerializer

logger = logging.getLogger()

_PAPER_ID_RE = re.compile(r"^/paper/([^/]+)/?$")

# Config this function needs at runtime, seeded into Catalyst Cache because
# Catalyst Functions have NO platform-level environment variables (confirmed
# via both the CLI's functions:config, which exposes only --memory, and the
# MCP env-var tools, which are AppSail-scoped).
#
# SEARXNG_BASE_URL points at the self-hosted SearXNG instance. It is NOT
# reachable at localhost from here -- this function runs in Catalyst's cloud
# and SearXNG runs on the developer's machine -- so the cached value is a
# public tunnel URL. Tunnel URLs change whenever the tunnel restarts, which
# is exactly why this is a cache entry rather than a constant.
_CACHED_CONFIG_VARS = ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3",
                       "SEARXNG_BASE_URL")


def _seed_config_from_cache() -> None:
    """Copy runtime config out of Catalyst Cache into os.environ.

    Env wins if already set (local dev / `catalyst serve`). Failures per key
    are non-fatal: an absent GEMINI_API_KEY_2 is normal, and the callers below
    degrade with their own clear errors rather than crashing here.
    """

    try:
        cache = zcatalyst_sdk.initialize().cache().segment()
    except Exception:
        logger.exception("could not reach Catalyst Cache for runtime config")
        return

    for var in _CACHED_CONFIG_VARS:
        if os.environ.get(var):
            continue
        try:
            value = (cache.get_value(var) or "").strip()
            if value:
                os.environ[var] = value
        except Exception:
            pass


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
# SDK surface (zcatalyst_sdk.nosql, confirmed live against the real table):
#
#   INSERT: item values must be DynamoDB-encoded via _NoSqlItem.to_nosql():
#     table.insert_items({'item': _NoSqlItem.to_nosql(python_dict)})
#     Raw Python dicts return INVALID_INPUT -- the API will not auto-encode.
#
#   FETCH:  key values must also be DynamoDB-encoded (confirmed live):
#     result = table.fetch_item({'keys': [{'id': {'S': paper_id}}]})
#     items[0].get('item') returns a deserialized Python dict.
#
#   UPDATE: both keys and update_value must be DynamoDB-encoded:
#     _NoSqlTypeSerializer().serialize(v) -> {'S': str} / {'L': list} / {'M': dict}
#     update_attributes: [{'operation_type': 'PUT', 'attribute_path': [k],
#                          'update_value': _NoSqlTypeSerializer().serialize(v)}]
#     keys: {'id': {'S': paper_id}}
#
#   DELETE: key values must also be DynamoDB-encoded:
#     table.delete_items({'keys': {'id': {'S': paper_id}}})
# --------------------------------------------------------------------------

def _get_nosql_table(name: str):
    return zcatalyst_sdk.initialize().nosql().get_table(name)


def _create_scenepaper(payload: dict) -> dict:
    item = {'id': payload.get('id') or str(uuid.uuid4()), **payload}
    table = _get_nosql_table('ScenePaper')
    table.insert_items({'item': _NoSqlItem.to_nosql(item)})
    return item


def _get_scenepaper(paper_id: str):
    table = _get_nosql_table('ScenePaper')
    try:
        result = table.fetch_item({'keys': [{'id': _NoSqlTypeSerializer().serialize(paper_id)}]})
    except Exception:
        # MUST log. A silent `return None` here makes a genuine NoSQL/network
        # failure indistinguishable from "no such paper" -- both surface as a
        # 404 -- which made it impossible to verify NoSQL was working at all.
        logger.exception("NoSQL fetch failed for paper_id=%s", paper_id)
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
    _ser = _NoSqlTypeSerializer()
    update_attrs = [
        {'operation_type': 'PUT', 'attribute_path': [k], 'update_value': _ser.serialize(v)}
        for k, v in updates.items()
    ]
    table.update_items({'keys': {'id': _NoSqlTypeSerializer().serialize(paper_id)}, 'update_attributes': update_attrs})
    existing.update(updates)
    return existing


def _delete_scenepaper(paper_id: str) -> bool:
    existing = _get_scenepaper(paper_id)
    if existing is None:
        return False
    table = _get_nosql_table('ScenePaper')
    table.delete_items({'keys': {'id': _NoSqlTypeSerializer().serialize(paper_id)}})
    return True


# --------------------------------------------------------------------------
# Stub ideation search -- TODO(issue #9)
#
# search_story_ideas is api-integration-agent's scope (SearXNG query
# building, domain-quality scoring, clustering -- see CLAUDE.md's "Search,
# verification & trust model" section). Not implemented here.
# --------------------------------------------------------------------------

def _run_ideation_search(topic: str) -> list:
    """Real ideation: classify -> query generation -> SearXNG -> domain-quality
    filter -> cluster -> one-liner generation (backend/ideation.py).

    Each candidate carries the real sources from its cluster, which is what
    makes the downstream verification meaningful: POST /generate feeds them
    straight into Call A, so the score reflects sources the system actually
    found rather than ones a caller supplied by hand.

    TIMING RISK, know this before changing anything here: measured ~20s
    locally, and this is an Advanced I/O function with a hard **30-second**
    cap. The budget is real but thin -- SearXNG is reached over a public
    tunnel (see _seed_config_from_cache), which adds latency on top. If this
    starts timing out, the fix is to move ideation to a Job function and poll,
    exactly as POST /generate already does, NOT to trim the search quality.
    """

    from backend import ideation  # imported lazily: keeps cold start cheap

    candidates = ideation.generate_candidate_one_liners(topic)

    # Always surface the top 3 regardless of score (CLAUDE.md trust model).
    # confidence_score stays None here on purpose -- scoring is Call A's job
    # during /generate, and inventing a number at ideation time would blur the
    # two signals the trust model deliberately keeps separate.
    return [
        {
            "one_liner": c.get("one_liner", ""),
            "confidence_score": None,
            "flags": (["thin sourcing"] if c.get("too_thin_to_summarize") else []),
            "sources": c.get("sources", []),
        }
        for c in candidates
    ]


# --------------------------------------------------------------------------
# Job submission -- Create_Immediate_Job pattern (issue #8 / issue #2)
# --------------------------------------------------------------------------

def _submit_pipeline_job(job_params: dict, request: Request = None) -> dict:
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

    # The incoming request MUST be handed to the SDK: initialize() calls
    # parse_headers_from_request(req), which is how the admin credentials for
    # this invocation get established. Called bare (no req), the SDK has no
    # credentials and every job submission fails -- which surfaced only as a
    # generic 502, since the failure happens inside the SDK's HTTP layer.
    app = zcatalyst_sdk.initialize(req=request)
    job_meta = {
        # Catalyst caps job_name at 20 chars and rejects the whole submission
        # with INVALID_INPUT past that -- verified live against the API, and
        # it is what made every POST /generate fail with a 502. The previous
        # value ("scenepaper_generate_" + 10 hex) was 30 chars.
        # "sp_gen_" (7) + 10 hex = 17, which leaves headroom.
        "job_name": f"sp_gen_{uuid.uuid4().hex[:10]}",
        "jobpool_id": jobpool_id,
        "jobpool_name": jobpool_name,
        "target_type": "Function",
        "target_id": job_function_id,
        "target_name": job_function_name,
        # Job params must be a flat Dict[str, str] -- nested structures
        # (e.g. the chosen candidate) are JSON-encoded.
        "params": {key: str(value) for key, value in job_params.items()},
    }
    # `.job` is a @property returning a Job instance -- NOT a method. Calling
    # it (`.job()`) raises "TypeError: 'Job' object is not callable".
    # `job_scheduling()` IS a method, hence the asymmetry.
    return app.job_scheduling().job.submit_job(job_meta)


# --------------------------------------------------------------------------
# Route handlers
# --------------------------------------------------------------------------

def _handle_ideate(request: Request):
    body = request.get_json(silent=True) or {}
    topic = body.get("topic")
    if not isinstance(topic, str) or not topic.strip():
        return _error(400, "'topic' is required and must be a non-empty string")

    candidates = _run_ideation_search(topic.strip())
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
        job_result = _submit_pipeline_job(job_params, request)
    except RuntimeError as exc:
        logger.error("Pipeline job not submitted: %s", exc)
        return _error(503, str(exc))
    except Exception as exc:  # pragma: no cover - real SDK/network errors
        # Include the actual exception text in BOTH the log and the response.
        # A bare "Failed to submit pipeline job" 502 hid two real, quite
        # different bugs (a 20-char job_name cap, and the SDK being
        # initialized without the request) and cost a deploy cycle each to
        # diagnose. This is a dev-environment service with no auth in front
        # of it, so there is nothing secret to leak here.
        logger.exception("Failed to submit pipeline job")
        return _error(502, f"Failed to submit pipeline job: {type(exc).__name__}: {exc}")

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
    # Initialize the SDK ONCE, here, with the request. initialize() runs
    # parse_headers_from_request(req), which establishes this invocation's
    # admin credentials; every later bare initialize() call in this module
    # (the NoSQL helpers) then picks those up. Skipping this is what made job
    # submission fail, and it would silently break every NoSQL call the same
    # way -- silently, because a failed read is indistinguishable from
    # "not found" at the HTTP layer.
    try:
        zcatalyst_sdk.initialize(req=request)
    except Exception:  # pragma: no cover - defensive
        logger.exception("zcatalyst_sdk.initialize(req=...) failed")

    # Gemini keys + SEARXNG_BASE_URL live in Catalyst Cache (Functions have no
    # environment variables). Must run before any handler that reaches for them.
    _seed_config_from_cache()

    method = request.method
    path = request.path or "/"

    if path == "/" and method == "GET":
        return _json_response(200, {"status": "success", "message": "scenepaper_pipeline is up"})

    if path == "/ideate" and method == "POST":
        return _handle_ideate(request)

    if path == "/generate" and method == "POST":
        return _handle_generate(request)

    # Paper CRUD accepts the id EITHER as a path segment (/paper/<id>) or as
    # a query parameter (/paper?id=<id>).
    #
    # The query-param form exists because of a hard API Gateway constraint:
    # a Gateway rule rewrites the incoming path to a FIXED target string, so
    # a rule for /paper can only ever forward "/paper" -- there is no way to
    # carry a per-request id through the path. Query strings pass through
    # untouched, so ?id= is the only form that works through the Gateway.
    #
    # The path form is kept because it still works for direct/local
    # invocation (`catalyst serve`, the test harness) and is the nicer URL if
    # Gateway ever supports path parameters.
    paper_match = _PAPER_ID_RE.match(path)
    paper_id = paper_match.group(1) if paper_match else None

    if paper_id is None and path.rstrip("/") == "/paper":
        try:
            paper_id = (request.args.get("id") or "").strip() or None
        except AttributeError:  # request object without .args (test fakes)
            paper_id = None
        if paper_id is None:
            return _error(
                400,
                "paper id is required -- call /paper?id=<paper_id> "
                "(the API Gateway cannot carry a path id, see the note in "
                "handler())",
            )

    if paper_id is not None:
        if method == "GET":
            return _handle_get_paper(paper_id)
        if method == "PUT":
            return _handle_put_paper(request, paper_id)
        if method == "DELETE":
            return _handle_delete_paper(paper_id)
        return _error(405, f"method '{method}' not allowed on /paper")

    return _error(404, f"unknown route: {method} {path}")
