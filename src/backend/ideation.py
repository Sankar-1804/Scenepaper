"""
Ideation — topic -> 3-4 verified candidate one-liners (docs/task-breakdown.md
Tasklist 2.1 / CLAUDE.md's "Search, verification & trust model").

Chains searxng_client.py's already-written pieces end to end against the
now-live SearXNG instance (ai-docs/plan.md, 2026-08-09):

    classify_query -> generate_broad_queries / generate_specific_queries ->
    _execute_searxng_query (per query) -> cluster_results (domain-quality
    filtered) -> fetch_top_results_per_cluster -> [one-liner generation]

Deliberately NOT built here: the prompt that turns a cluster's fetched
results into the one-liner text a creator actually reads and picks from.
That is the same category of judgment call as gemini_client.py's
STRUCTURING_PROMPT / VERIFICATION_RULES_PROMPT -- docs/task-breakdown.md
Tasklist 2.1 flags "Ideation prompt tuning (quality of 3-4 one-liners)" as
hil, and searxng_client.py's own module docstring reserves this exact step
for a human-driven session. ONE_LINER_PROMPT below is a None placeholder for
that reason. Do not fill it in as an agent -- see that constant's comment.

Everything above the one-liner step (query generation, search execution,
domain-quality filtering, clustering) is real and safe to run/test today.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

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

# Reserved for the human -- see module docstring. Do not draft this as an
# agent; it is user-facing creative output (what a creator reads and picks
# from), the same category of work as gemini_client.py's structuring/
# verification prompts.
ONE_LINER_PROMPT = None

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

    _request_type, _clusters = gather_candidate_clusters(topic, niche, client=client)
    raise NotImplementedError("unreachable until ONE_LINER_PROMPT is written")
