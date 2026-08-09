"""
scenepaper_pipeline_job -- Job Function (the actual pipeline, 15-min budget)

Receives params from the Advanced I/O front door (POST /generate):
  paper_id  -- pre-generated id already handed back to the caller so it can
               poll GET /paper?id=<paper_id>
  topic     -- the original topic string the user submitted
  candidate -- JSON-encoded dict: the one candidate the user picked from
               POST /ideate's results. Expected keys:
                 one_liner  -- the one-line candidate summary shown to the user
                 sources    -- optional list of {title, url, snippet, date,
                               source_type} dicts (empty for stub candidates)
  user_id   -- optional, not used yet (UserProfile work item 3)

Stage layout:
  1+2  generate_scene_paper (orchestrator) -- Call A + Call B, one import
  3    voiceover                           -- stub, api-integration-agent
  4    images                              -- stub, api-integration-agent
  5    write to NoSQL                      -- REAL

DynamoDB encoding note: all NoSQL values must be DynamoDB-encoded. insert_items
uses _NoSqlItem.to_nosql() for the full document. See comments in
functions/scenepaper_pipeline/main.py for the full encoding reference.
"""

import json
import logging
import os
from decimal import Decimal

import zcatalyst_sdk
from zcatalyst_sdk.nosql.transfom import Item as _NoSqlItem

from backend.clients.gemini_client import SourceMaterial
from backend.orchestrator import Candidate, generate_scene_paper

logger = logging.getLogger()

# Catalyst Functions have no environment variables. API keys live in Catalyst
# Cache (seeded once manually via the Console: key = 'GEMINI_API_KEY', etc.)
# and are read here at handler start. os.environ fallback keeps local dev
# working via a .env loaded before the process starts.
_GEMINI_KEY_VARS = ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3")


def _seed_api_keys_from_cache(app) -> None:
    """Read Gemini API keys from Catalyst Cache into os.environ.

    Only writes keys that aren't already set (env takes precedence for local
    dev). Logs a warning if GEMINI_API_KEY itself is missing after the attempt
    since gemini_client will fail silently if no key is present.
    """
    cache = app.cache().segment()
    for var in _GEMINI_KEY_VARS:
        if os.environ.get(var):
            continue  # already set (local dev / CI)
        try:
            value = (cache.get_value(var) or "").strip()
            if value:
                os.environ[var] = value
        except Exception:
            pass  # key simply not in Cache yet -- that's fine for _2/_3
    if not os.environ.get("GEMINI_API_KEY"):
        logger.warning(
            "GEMINI_API_KEY not found in env or Catalyst Cache -- "
            "seed it via the Console: Cache > default segment > key=GEMINI_API_KEY"
        )


def _floats_to_decimal(obj):
    """Recursively convert float values to Decimal before DynamoDB encoding.

    zcatalyst_sdk's TypeSerializer raises TypeError on floats -- Decimal is the
    documented equivalent for NoSQL numbers. sources[].confidence_score (a float
    from Call A's VerificationResult) is the real-world trigger.
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _floats_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_floats_to_decimal(item) for item in obj]
    return obj


def _build_candidate(candidate_dict: dict) -> Candidate:
    """Map the JSON-decoded candidate dict from the job param to a Candidate.

    The /ideate stub emits {'one_liner': '...'} with no sources. Once ideation
    is real (work item 1 in api-integration-agent's plan), candidates will also
    carry a `sources` list of {title, url, snippet, date, source_type} dicts.
    Both shapes are handled here.
    """
    summary = candidate_dict.get("one_liner") or candidate_dict.get("summary", "")
    raw_sources = candidate_dict.get("sources") or []
    sources = [
        SourceMaterial(
            title=s.get("title", ""),
            url=s.get("url", ""),
            snippet_or_text=s.get("snippet", ""),
            date=s.get("date"),
            source_type=s.get("source_type", "web"),
        )
        for s in raw_sources
        if isinstance(s, dict)
    ]
    return Candidate(summary=summary, sources=sources)


def _stage_generate(topic: str, candidate: Candidate) -> dict:
    """Call A (verify) + Call B (structure) via the orchestrator.

    Returns a dict shaped like CLAUDE.md's ScenePaper entity schema, plus
    `topic` and the profile parser's audit trail fields.

    profile_md_text is omitted here -- work item 3 (UserProfile) will wire it
    in once the UserProfile entity exists. The orchestrator defaults it to ""
    and the profile_parser produces empty warnings, so nothing breaks.
    """
    logger.info("stage 1+2/4: generate_scene_paper for topic=%r", topic)
    return generate_scene_paper(topic, candidate)


def _stage_voiceover(scene_paper: dict):
    """TODO(api-integration-agent work item 3): TTS via voicebox_client.
    Fix voicebox_client's assumed /api/tts endpoint, wire POST /generate +
    poll /generate/{id}/status + fetch /audio/{generation_id}.
    Returns None until implemented.
    """
    logger.info("STUB stage 2/4: voiceover")
    return None


def _stage_images(scene_paper: dict) -> list:
    """TODO(api-integration-agent work item 4): Pexels stock photos per scene.
    Wire per-scene keyword → pexels_client fetch. Returns [] until implemented.
    """
    logger.info("STUB stage 3/4: images")
    return []


def _stage_write_scenepaper(
    paper_id: str, scene_paper: dict, voiceover_url, image_set: list
):
    """Write the finished ScenePaper document to Catalyst NoSQL.

    Merges paper_id, voiceover_url, image_set, and locked media/export state
    into the orchestrator's draft dict before writing. All values must be
    DynamoDB-encoded -- _NoSqlItem.to_nosql() handles that for the full doc.
    """
    logger.info("stage 4/4: write ScenePaper id=%s", paper_id)

    doc = {
        **scene_paper,
        "id": paper_id,
        "voiceover_url": voiceover_url,
        "image_set": image_set or [],
        "media_status": "ready" if voiceover_url else "pending",
        "export_status": "locked",
    }

    # Remove orchestrator audit-trail keys that aren't part of the schema.
    for audit_key in ("profile_warnings", "profile_dropped_sections", "profile_truncated_fields"):
        dropped = doc.pop(audit_key, None)
        if dropped:
            logger.info("profile parser audit (%s): %s", audit_key, dropped)

    table = zcatalyst_sdk.initialize().nosql().get_table("ScenePaper")
    table.insert_items({"item": _NoSqlItem.to_nosql(_floats_to_decimal(doc))})
    logger.info("ScenePaper id=%s written to NoSQL", paper_id)


def handler(job_request, context):
    logger = logging.getLogger()

    # Seed thread-local Catalyst credentials from the job request headers,
    # exactly like the Advanced I/O function does with its HTTP request.
    # Without this, zcatalyst_sdk.initialize() raises "Catalyst headers are empty"
    # when _stage_write_scenepaper tries to write to NoSQL.
    app = zcatalyst_sdk.initialize(req=job_request)

    # Catalyst Functions have no env vars -- read Gemini API key(s) from Cache.
    _seed_api_keys_from_cache(app)

    all_params = job_request.get_all_job_params()
    logger.info("scenepaper_pipeline_job started, params=%s", all_params)

    paper_id = job_request.get_job_param("paper_id")
    topic = job_request.get_job_param("topic")
    candidate_raw = job_request.get_job_param("candidate")

    if not paper_id or not topic or not candidate_raw:
        logger.error(
            "Missing required job params (paper_id=%s, topic=%s, candidate=%s)",
            paper_id,
            topic,
            candidate_raw,
        )
        context.close_with_failure()
        return

    try:
        candidate_dict = json.loads(candidate_raw)
    except (TypeError, ValueError):
        logger.error("candidate job param was not valid JSON: %r", candidate_raw)
        context.close_with_failure()
        return

    try:
        candidate = _build_candidate(candidate_dict)
        scene_paper = _stage_generate(topic, candidate)
        voiceover_url = _stage_voiceover(scene_paper)
        image_set = _stage_images(scene_paper)
        _stage_write_scenepaper(paper_id, scene_paper, voiceover_url, image_set)
    except Exception:
        logger.exception("scenepaper_pipeline_job failed for paper_id=%s", paper_id)
        context.close_with_failure()
        return

    logger.info("scenepaper_pipeline_job finished for paper_id=%s", paper_id)
    context.close_with_success()
