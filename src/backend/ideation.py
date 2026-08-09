"""
Ideation — topic -> 3-4 verified candidate one-liners (docs/task-breakdown.md
Tasklist 2.1 / CLAUDE.md's "Search, verification & trust model").

Chains searxng_client.py's already-written pieces end to end against the
now-live SearXNG instance (ai-docs/plan.md, 2026-08-09):

    classify_query -> generate_broad_queries / generate_specific_queries ->
    _execute_searxng_query (per query) -> cluster_results (domain-quality
    filtered) -> fetch_top_results_per_cluster -> [one-liner generation]

ONE_LINER_PROMPT (the text a creator actually reads and picks from) is the
same category of judgment call as gemini_client.py's STRUCTURING_PROMPT /
VERIFICATION_RULES_PROMPT, which were drafted with the human and approved.
docs/task-breakdown.md Tasklist 2.1 flags "Ideation prompt tuning" as hil.
The current value is a DRAFT pending review -- see that constant's comment.

generate_candidate_one_liners() returns each candidate WITH the real sources
from its cluster, so POST /generate can feed them straight into Call A. That
is what makes the verification score meaningful: it reflects sources the
system found, not sources a caller typed in by hand.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.clients.gemini_client import (
    _client as _gemini_client,
    _generate_with_model_fallback,
)
from backend.clients.searxng_client import (
    SearchResult,
    _execute_searxng_query,
    classify_query,
    cluster_results,
    fetch_top_results_per_cluster,
    generate_broad_queries,
    generate_specific_queries,
)

logger = logging.getLogger(__name__)

# User-facing creative output (what a creator reads and picks from), the same
# category as gemini_client.py's verification/structuring prompts -- which
# were drafted with the human and approved rather than written blind.
#
# DRAFT, 2026-08-10, pending the user's review. Written to unblock the live
# ideation path (this step raised NotImplementedError before any search ran,
# so /ideate could not be wired at all). Tune against real candidate output;
# the anti-hype framing is the part that matters, since it mirrors the trust
# model -- help the creator judge a story, don't sell it to them.
ONE_LINER_PROMPT = """\
You turn clusters of real search results into short candidate story
one-liners that a short-form video creator will choose between.

Each cluster is a group of search results about the SAME underlying story,
with a representative title, URL and snippet.

For each cluster, write ONE one-liner that:
- States what actually happened, concretely -- a specific subject and a
  specific turn of events. "A 1900 lighthouse was rolled 70 metres inland to
  escape the sea" beats "An amazing story of engineering."
- Uses ONLY what the cluster's results actually say. Do not add facts,
  figures, names or outcomes that are not in the material. If the snippets
  are too thin to say anything specific, say so plainly rather than
  inventing detail.
- Is a single sentence of roughly 12-25 words, written to help someone decide
  whether the story is worth telling -- not to sell it. No hype, no
  clickbait, no rhetorical questions.

Across the set, prefer one-liners that are clearly DIFFERENT stories rather
than restatements of the same event. If two clusters are in fact the same
story, say so rather than padding the list.

Return the candidates in the order given.
"""

# Below this domain-quality score, a result is dropped before clustering
# (CLAUDE.md: "domain-quality scoring happens before clustering"). Set just
# above score_domain_quality's low-quality-hint floor (0.2 for
# blogspot/medium/reddit/quora) so those get filtered while the neutral
# default (0.4, unknown domains) and anything better survives. A numeric
# threshold, not a creative call -- safe to set here, but treat it as a
# starting point to recalibrate once real SearXNG output volume exists.
DEFAULT_MIN_DOMAIN_SCORE = 0.3


@dataclass
class CandidateCluster:
    """One cluster of SearXNG results, ready to become a one-liner candidate
    once ONE_LINER_PROMPT exists. Bundles what that step will need: every
    result in the cluster, already domain-quality filtered and ranked, plus
    a `representative` (the highest-quality result) for convenience."""

    results: list[SearchResult]

    @property
    def representative(self) -> SearchResult:
        return self.results[0]


def gather_candidate_clusters(
    topic: str,
    niche: str | None = None,
    exclude_angle_types: list[str] | None = None,
    num_results_per_cluster: int = 2,
    min_domain_score: float = DEFAULT_MIN_DOMAIN_SCORE,
    *,
    client=None,
) -> tuple[str, list[CandidateCluster]]:
    """Run the full search -> filter -> cluster pipeline for one topic.

    Returns `(request_type, clusters)` -- everything up to, but not
    including, one-liner generation (see module docstring). `request_type`
    is "broad" or "specific" (classify_query's output), so callers/logs can
    tell which query strategy produced these clusters.

    `client` is an optional injected Gemini SDK client, threaded through to
    the query-generation calls (generate_broad_queries /
    generate_specific_queries) -- tests pass a fake here.
    """

    request_type = classify_query(topic)

    if request_type == "broad":
        plans = generate_broad_queries(
            topic, niche, exclude_angle_types=exclude_angle_types, client=client
        )
    else:
        _discovery, plans = generate_specific_queries(
            topic, niche, exclude_angle_types=exclude_angle_types, client=client
        )

    all_results: list[SearchResult] = []
    for plan in plans:
        all_results.extend(_execute_searxng_query(plan.query))

    clusters = cluster_results(all_results, min_domain_score=min_domain_score)
    trimmed = fetch_top_results_per_cluster(clusters, n=num_results_per_cluster)

    return request_type, [CandidateCluster(results=r) for r in trimmed if r]


def generate_candidate_one_liners(
    topic: str,
    niche: str | None = None,
    num_sources_per_candidate: int = 3,
    *,
    client=None,
) -> list[dict]:
    """topic -> 3-4 candidate one-liners (the function work item 1 asks for).

    Checks the ONE_LINER_PROMPT guard FIRST, before running any search --
    fails fast rather than burning a live SearXNG/Gemini round trip on a
    step that cannot finish yet. See module docstring: this prompt is
    reserved for the human.
    """

    if ONE_LINER_PROMPT is None:
        raise NotImplementedError(
            "ONE_LINER_PROMPT has not been written yet -- reserved for the "
            "human (see module docstring and docs/task-breakdown.md Tasklist "
            "2.1's 'Ideation prompt tuning' item). gather_candidate_clusters() "
            "is real and safe to call/test on its own without this."
        )

    _request_type, clusters = gather_candidate_clusters(topic, niche, client=client)
    if not clusters:
        return []

    # Always surface the top 3 regardless of score (CLAUDE.md trust model:
    # suppressing low scorers silently narrows the library to well-SEO'd
    # mainstream stories, which is the opposite of the point). Take a 4th when
    # there is one, since the product promises "3-4".
    clusters = clusters[:4]

    cluster_block = "\n\n".join(
        "[{i}] title: {t}\n    url: {u}\n    snippet: {s}\n    other results in cluster: {n}".format(
            i=i + 1,
            t=c.representative.title,
            u=c.representative.url,
            s=(c.representative.content or "")[:600],
            n=max(len(c.results) - 1, 0),
        )
        for i, c in enumerate(clusters)
    )

    from google.genai import types  # local import: keeps module import cheap

    schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "candidates": types.Schema(
                type=types.Type.ARRAY,
                items=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "cluster_index": types.Schema(type=types.Type.INTEGER),
                        "one_liner": types.Schema(type=types.Type.STRING),
                        "too_thin_to_summarize": types.Schema(type=types.Type.BOOLEAN),
                    },
                    required=["cluster_index", "one_liner"],
                ),
            )
        },
        required=["candidates"],
    )

    response = _generate_with_model_fallback(
        client or _gemini_client(),
        contents=f"{ONE_LINER_PROMPT}\n\nTopic: {topic}\n\nClusters:\n{cluster_block}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=schema
        ),
    )

    import json

    payload = response.parsed if hasattr(response, "parsed") else response.text
    data = payload if isinstance(payload, dict) else json.loads(payload)

    candidates: list[dict] = []
    for entry in data.get("candidates", []):
        idx = int(entry.get("cluster_index", 0)) - 1
        if not (0 <= idx < len(clusters)):
            continue
        cluster = clusters[idx]
        # Carry the cluster's real sources through with the candidate. This is
        # what makes verification meaningful downstream: POST /generate feeds
        # these straight into Call A, so the score reflects sources the system
        # actually found rather than ones a caller typed in by hand.
        candidates.append(
            {
                "one_liner": entry.get("one_liner", ""),
                "too_thin_to_summarize": entry.get("too_thin_to_summarize", False),
                "sources": [
                    {
                        "title": r.title,
                        "url": r.url,
                        "snippet": (r.content or "")[:1500],
                        "source_type": "web",
                    }
                    for r in cluster.results[:num_sources_per_candidate]
                ],
            }
        )

    return candidates
