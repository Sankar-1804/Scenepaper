"""
scenepaper_pipeline_job -- Job Function (the actual pipeline, 15-min budget)

Renamed from the `scenepaper_job_test` scaffold (was created only to
inspect Catalyst's generated Job-function code template) -- this is now the
real target of scenepaper_pipeline's POST /generate handler, submitted via
the Create_Immediate_Job pattern (zcatalyst_sdk job_scheduling().job().
submit_job(...), see functions/scenepaper_pipeline/main.py).

Why this function exists at all: Advanced I/O Functions (scenepaper_pipeline)
have a hard 30-second execution timeout. The real pipeline -- SearXNG
search/cluster, two isolated LLM calls (verification, then structuring per
CLAUDE.md's prompt-injection defense), TTS, image fetch, and the NoSQL
write -- does not fit in 30s. Job functions get a 15-minute budget instead,
so the Advanced I/O function only submits a job here and returns
immediately; this function does the actual work.

Expected job params (set by scenepaper_pipeline's _handle_generate):
  paper_id  -- pre-generated id the Advanced I/O function already handed
               back to the caller, so it can poll GET /paper/:id
  topic     -- the original topic string the user submitted
  candidate -- JSON-encoded object: the one candidate the user picked from
               POST /ideate's results (one_liner, any source hints, etc.)
  user_id   -- optional, for UserProfile-driven personalization

Every real pipeline stage below is stubbed and TODO-marked with the issue
it belongs to. None of it is implemented here -- search/verify/structure/
TTS/images are api-integration-agent's scope (issues #9, #10); the NoSQL
write is blocked on issue #1 (column-type verification for nested JSON
fields). This function's job tonight is only: receive params correctly,
walk through the stages in the right order, and close_with_success/
close_with_failure at the right points.
"""

import json
import logging

logger = logging.getLogger()


def _stage_search_and_verify(topic: str, candidate: dict) -> dict:
    """
    TODO(issue #9, api-integration-agent): Run the two-call verification
    step for the chosen candidate:
      - Call A (verification/scoring): sources only + platform-owned rules,
        NEVER sees the user's profile config (prompt-injection defense per
        CLAUDE.md). Produces a graded confidence score (x/10) plus binary
        flags (sources conflict / single source only / unverified origin /
        claim not found in primary sources).
    Not implemented -- returns the input candidate unchanged with a
    placeholder score so downstream stages have something to pass along.
    """
    logger.info("STUB stage 1/5 (issue #9): search_and_verify for topic=%r", topic)
    return {**candidate, "confidence_score": None, "flags": ["stub-not-verified"]}


def _stage_structure(topic: str, verified_candidate: dict) -> dict:
    """
    TODO(issue #9, api-integration-agent): Call B (structuring) -- takes
    the verified source + Call A's fixed score as input (score is
    read-only to this call, per CLAUDE.md's prompt-injection defense), plus
    the user's profile.md format preferences (scene structure, categories,
    runtime target, tone, avoid-list). Produces the full rich ScenePaper
    schema: hooks[], scenes[] with pacing tags, delivery_notes[],
    sources[], cta_text, etc. Also must flag unverifiable narrative framing
    distinctly from sourced fact (the hook-overstatement check).
    Not implemented -- returns a minimal placeholder scene paper body.
    """
    logger.info("STUB stage 2/5 (issue #9): structure for topic=%r", topic)
    return {
        "title": f"[stub] {topic}",
        "category": "curious",
        "dek": "[stub structuring output -- not a real scene paper]",
        "verification_status": verified_candidate.get("confidence_score"),
        "hooks": [],
        "scenes": [],
        "delivery_notes": [],
        "sources": [],
        "cta_text": "",
    }


def _stage_voiceover(scene_paper: dict) -> str:
    """
    TODO(issue #10, api-integration-agent): Generate a single consistent
    TTS voice reading story_body, with pauses inserted at breath points.
    Per-scene pacing-tag-aware delivery is a Tier 2 refinement, not
    required here. Not implemented -- returns None (no audio yet).
    """
    logger.info("STUB stage 3/5 (issue #10): voiceover")
    return None


def _stage_images(scene_paper: dict) -> list:
    """
    TODO(issue #10, api-integration-agent): Fetch real stock photos
    (Pexels or Unsplash) matched per scene keyword -- NOT AI-generated
    imagery. Not implemented -- returns an empty image_set.
    """
    logger.info("STUB stage 4/5 (issue #10): images")
    return []


def _stage_write_scenepaper(paper_id: str, scene_paper: dict, voiceover_url, image_set: list):
    """
    TODO(work item 1): Wire to the real orchestrator and write the finished
    ScenePaper document to NoSQL once api-integration-agent lands
    src/backend/orchestrator.py. Correct SDK surface (confirmed via live probe):
        from zcatalyst_sdk.nosql.transfom import Item as _NoSqlItem
        table = zcatalyst_sdk.initialize().nosql().get_table('ScenePaper')
        doc = {**scene_paper, 'id': paper_id, 'voiceover_url': voiceover_url,
               'image_set': image_set}
        table.insert_items({'item': _NoSqlItem.to_nosql(doc)})
    Not implemented -- just logs what would have been written.
    """
    logger.info(
        "STUB stage 5/5 (work item 1): write ScenePaper id=%s (scene_paper keys=%s, "
        "voiceover_url=%s, image_set_count=%d)",
        paper_id,
        list(scene_paper.keys()),
        voiceover_url,
        len(image_set),
    )


def handler(job_request, context):
    logger = logging.getLogger()

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
        candidate = json.loads(candidate_raw)
    except (TypeError, ValueError):
        logger.error("candidate job param was not valid JSON: %r", candidate_raw)
        context.close_with_failure()
        return

    try:
        verified_candidate = _stage_search_and_verify(topic, candidate)
        scene_paper = _stage_structure(topic, verified_candidate)
        voiceover_url = _stage_voiceover(scene_paper)
        image_set = _stage_images(scene_paper)
        _stage_write_scenepaper(paper_id, scene_paper, voiceover_url, image_set)
    except Exception:  # pragma: no cover - defensive, stages are stubs today
        logger.exception("scenepaper_pipeline_job failed for paper_id=%s", paper_id)
        context.close_with_failure()
        return

    logger.info("scenepaper_pipeline_job finished for paper_id=%s", paper_id)
    context.close_with_success()
