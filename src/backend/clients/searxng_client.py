"""
SearXNG client wrapper — ideation search (topic -> candidate story sources),
per CLAUDE.md's "Search, verification & trust model" section.

Pipeline this module implements the *shape* of (see CLAUDE.md addendum):

    user request -> classify (broad vs. specific) -> build query set ->
    SearXNG -> filter/rank (domain-quality score) -> cluster into distinct
    candidates -> [one-liner summarization — NOT built here, see below]

Two request modes:
  - Broad  (e.g. "motivational story"): fan out into 3-4 parallel queries
    across structurally different sub-angles of the creator's niche
    (era / industry / failure-vs-success), not near-synonyms.
  - Specific (e.g. "Snapchat"): a discovery step first decides Axis 1
    (different documented events, preferred when >=3 exist) vs. Axis 2
    (different framings of one event, fallback).

Both modes produce a list of `QueryPlan` objects: {query, angle_type,
rationale} using the controlled `angle_type` vocabulary (ANGLE_TYPES below),
so the "show me more" loop can mechanically exclude already-used angle types
rather than hoping a model varies on its own (CLAUDE.md, verbatim).

**No live SearXNG instance exists yet** (issue #21 — hosting location still
undecided). `_execute_searxng_query()` is written against SearXNG's
documented public JSON search API shape (`GET /search?q=...&format=json`)
but has nothing to connect to tonight — see the TODO at that function.

**Explicitly NOT built in this module**: the step that turns fetched/
clustered search results into the 3-4 user-facing one-liner candidates. That
is "Ideation prompt tuning (quality of 3-4 one-liners)" — flagged **hil** in
issue #9 and docs/task-breakdown.md Tasklist 2.1, i.e. deliberately left for
a human-driven session, same category of work as the structuring prompt in
gemini_client.py. This module stops at "verified, scored, clustered source
material," which is exactly what that (not-yet-built) step would consume.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

SEARXNG_BASE_URL = os.environ.get("SEARXNG_BASE_URL", "http://localhost:8888")

# Controlled angle_type vocabulary (CLAUDE.md: "comeback, rejection, pivot,
# underdog, sacrifice, lucky-break, etc."). Kept as a plain list (not a
# strict enum) since CLAUDE.md itself says "etc." — new angle types may be
# added over time, but additions should be deliberate, not ad hoc per-query.
ANGLE_TYPES: list[str] = [
    "comeback",
    "rejection",
    "pivot",
    "underdog",
    "sacrifice",
    "lucky-break",
    "reinvention",
    "downfall",
    "rivalry",
]


# ---------------------------------------------------------------------------
# Query classification — broad vs. specific
# ---------------------------------------------------------------------------

# Deliberately a simple heuristic, not an LLM call — per the overnight brief,
# "your call, but keep it simple." Revisit if it misclassifies in practice.
_BROAD_HINT_PHRASES = {
    "story",
    "stories",
    "motivational",
    "motivation",
    "inspiring",
    "inspirational",
    "success story",
    "failure story",
    "true crime",
    "mystery",
    "underdog story",
    "comeback story",
    "cautionary tale",
}

_STOPWORDS = {"a", "an", "the", "of", "in", "on", "about", "story", "stories"}


def classify_query(topic: str) -> str:
    """Return "broad" or "specific" for a raw user topic string.

    Heuristic: a short phrase containing a capitalized token that isn't a
    known broad-category phrase reads as a specific named subject (e.g.
    "Snapchat", "Elizabeth Holmes"). Anything containing a broad-category
    hint phrase, or lacking any proper-noun-shaped token, reads as broad
    (e.g. "motivational story", "a business failure story").
    """

    normalized = topic.strip().lower()
    if not normalized:
        return "broad"

    if any(phrase in normalized for phrase in _BROAD_HINT_PHRASES):
        return "broad"

    tokens = topic.strip().split()
    proper_noun_tokens = [
        t for t in tokens if t[:1].isupper() and t.lower() not in _STOPWORDS
    ]

    if len(tokens) <= 5 and proper_noun_tokens:
        return "specific"

    return "broad"


# ---------------------------------------------------------------------------
# Query plans (query-generation call output shape)
# ---------------------------------------------------------------------------


@dataclass
class QueryPlan:
    """One SearXNG query to run, tagged for the exclusion-context loop.

    Matches CLAUDE.md's addendum JSON shape: {query, angle_type, rationale}.
    `event_name` is only populated for Axis-1 (different-events) specific
    discovery, where each query targets a distinct documented event.
    """

    query: str
    angle_type: str
    rationale: str
    event_name: str | None = None

    def __post_init__(self) -> None:
        if self.angle_type not in ANGLE_TYPES:
            logger.warning(
                "angle_type '%s' is not in the controlled ANGLE_TYPES vocabulary "
                "— allowed but flagged, since CLAUDE.md's vocabulary is meant "
                "to stay deliberate, not ad hoc.",
                self.angle_type,
            )


@dataclass
class DiscoveryResult:
    """Output of the specific-request discovery step (Axis 1 vs Axis 2)."""

    axis: str  # "axis_1_events" or "axis_2_framings"
    documented_event_count_estimate: int
    rationale: str
    subject_ambiguity_note: str | None = None
    candidate_events: list[str] = field(default_factory=list)


# Real, but deliberately mechanical, instruction text for the query-generation
# call — NOT the ideation one-liner prompt and NOT the structuring prompt
# (both of those are reserved for the human, see gemini_client.py). This text
# only produces internal SearXNG search-engine query strings, never anything
# shown to the end user, so it's in-scope to write for real tonight per the
# overnight brief ("build everything around it for real").
_QUERY_GENERATION_INSTRUCTIONS = (
    "You generate search-engine queries (not full sentences) for SearXNG, a "
    "metasearch engine, to find candidate short-form video story ideas. "
    "Produce concise, keyword-style queries a human would type into a search "
    "box. Each query must use a different angle_type from the provided "
    "controlled vocabulary, and each angle_type must be phrased as a "
    "structurally different angle (e.g. different era, different industry, "
    "failure vs. success) — not near-synonyms of each other. Never reuse an "
    "angle_type listed in the exclusion set."
)


def _query_generation_response_schema():
    from google.genai import types

    return types.Schema(
        type=types.Type.ARRAY,
        items=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "query": types.Schema(type=types.Type.STRING),
                "angle_type": types.Schema(type=types.Type.STRING, enum=ANGLE_TYPES),
                "rationale": types.Schema(type=types.Type.STRING),
                "event_name": types.Schema(type=types.Type.STRING, nullable=True),
            },
            required=["query", "angle_type", "rationale"],
        ),
    )


def _gemini_client(client=None):
    """Lazily build (or reuse) a Gemini client for query-generation calls.

    Imported lazily to avoid a hard dependency cycle at module import time;
    the actual client construction/behavior lives in gemini_client.py.
    """

    if client is not None:
        return client
    from backend.clients.gemini_client import _client as build_client

    return build_client()


def _generate_query_plans(
    context_instructions: str,
    num_queries: int,
    exclude_angle_types: list[str] | None = None,
    *,
    client=None,
) -> list[QueryPlan]:
    """Shared Gemini call used by both broad fan-out and specific-axis query
    generation. `context_instructions` supplies the topic/niche/axis-specific
    framing on top of `_QUERY_GENERATION_INSTRUCTIONS`.
    """

    from google.genai import types

    exclude_angle_types = exclude_angle_types or []
    gemini_client = _gemini_client(client)

    prompt = (
        f"{_QUERY_GENERATION_INSTRUCTIONS}\n\n"
        f"{context_instructions}\n\n"
        f"Number of queries to produce: {num_queries}\n"
        f"Angle types already used this session (do not reuse): "
        f"{exclude_angle_types or 'none'}\n"
        f"Controlled angle_type vocabulary: {ANGLE_TYPES}"
    )

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=_query_generation_response_schema(),
        ),
    )

    payload = response.parsed if hasattr(response, "parsed") else response.text
    data = payload if isinstance(payload, list) else json.loads(payload)
    return [
        QueryPlan(
            query=item["query"],
            angle_type=item["angle_type"],
            rationale=item["rationale"],
            event_name=item.get("event_name"),
        )
        for item in data
    ]


def generate_broad_queries(
    topic: str,
    niche: str | None = None,
    num_variants: int = 4,
    exclude_angle_types: list[str] | None = None,
    *,
    client=None,
) -> list[QueryPlan]:
    """Broad-request fan-out: 3-4 parallel query variants across niche
    sub-angles. `num_variants` should be 3 or 4 per CLAUDE.md.
    """

    context = (
        f"Request type: BROAD. Topic: '{topic}'. "
        f"Creator niche/domain: '{niche or 'unspecified'}'. "
        "Fan these queries out across structurally different sub-angles of "
        "this niche (e.g. different era, different industry, failure vs. "
        "success), not near-synonyms of the same angle."
    )
    return _generate_query_plans(context, num_variants, exclude_angle_types, client=client)


def discover_specific_axis(
    topic: str,
    niche: str | None = None,
    *,
    client=None,
) -> DiscoveryResult:
    """Specific-request discovery step: decide Axis 1 (different documented
    events, when >=3 exist) vs Axis 2 (different framings of one event,
    fallback). Also surfaces subject ambiguity for the caller to resolve or
    ask about (CLAUDE.md: "resolve via profile/domain or ask").
    """

    from google.genai import types

    gemini_client = _gemini_client(client)

    schema = types.Schema(
        type=types.Type.OBJECT,
        properties={
            "axis": types.Schema(
                type=types.Type.STRING,
                enum=["axis_1_events", "axis_2_framings"],
            ),
            "documented_event_count_estimate": types.Schema(type=types.Type.INTEGER),
            "rationale": types.Schema(type=types.Type.STRING),
            "subject_ambiguity_note": types.Schema(type=types.Type.STRING, nullable=True),
            "candidate_events": types.Schema(
                type=types.Type.ARRAY, items=types.Schema(type=types.Type.STRING)
            ),
        },
        required=["axis", "documented_event_count_estimate", "rationale", "candidate_events"],
    )

    prompt = (
        "Given a specific named subject for a short-form video story search, "
        "estimate how many distinct, well-documented historical events exist "
        "in this subject's history (not near-duplicates of the same event). "
        "If there are 3 or more, prefer axis_1_events and list the candidate "
        "events. Otherwise prefer axis_2_framings (different framings of the "
        "single dominant event). Also flag if the subject name is ambiguous "
        "(e.g. could refer to more than one distinct entity) so it can be "
        "resolved via the creator's niche/domain or by asking them directly.\n\n"
        f"Subject: '{topic}'. Creator niche/domain: '{niche or 'unspecified'}'."
    )

    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )

    payload = response.parsed if hasattr(response, "parsed") else response.text
    data = payload if isinstance(payload, dict) else json.loads(payload)
    return DiscoveryResult(
        axis=data["axis"],
        documented_event_count_estimate=data["documented_event_count_estimate"],
        rationale=data["rationale"],
        subject_ambiguity_note=data.get("subject_ambiguity_note"),
        candidate_events=data.get("candidate_events", []),
    )


def generate_specific_queries(
    topic: str,
    niche: str | None = None,
    exclude_angle_types: list[str] | None = None,
    *,
    client=None,
) -> tuple[DiscoveryResult, list[QueryPlan]]:
    """Full specific-request flow: discover the axis, then build queries
    appropriate to whichever axis was chosen.

    Applies the >=3-documented-events rule itself (not just trusting the
    model's `axis` field blindly) as a defense-in-depth check, since
    CLAUDE.md states the preference rule explicitly as a hard >=3 threshold.
    """

    discovery = discover_specific_axis(topic, niche, client=client)

    # Defense-in-depth: enforce the >=3 rule in code, don't just trust the
    # model's own axis choice.
    axis = (
        "axis_1_events"
        if discovery.documented_event_count_estimate >= 3
        else "axis_2_framings"
    )
    if axis != discovery.axis:
        logger.info(
            "Overriding model's axis choice (%s) with rule-enforced axis (%s) "
            "based on documented_event_count_estimate=%d",
            discovery.axis,
            axis,
            discovery.documented_event_count_estimate,
        )

    if axis == "axis_1_events" and discovery.candidate_events:
        context = (
            f"Request type: SPECIFIC, Axis 1 (different documented events). "
            f"Subject: '{topic}'. Creator niche/domain: '{niche or 'unspecified'}'. "
            f"Documented events to cover, one query per event: "
            f"{discovery.candidate_events}. Set event_name on each query to the "
            "specific event it targets."
        )
        num_queries = len(discovery.candidate_events)
    else:
        context = (
            f"Request type: SPECIFIC, Axis 2 (different framings of one event). "
            f"Subject: '{topic}'. Creator niche/domain: '{niche or 'unspecified'}'. "
            "Since there aren't 3+ distinct documented events, produce queries "
            "that frame the same dominant event differently (different angle_type "
            "per query), rather than covering different events. Deliberately "
            "reach for a less-covered angle if the subject is heavily over-told."
        )
        num_queries = 3

    plans = _generate_query_plans(context, num_queries, exclude_angle_types, client=client)
    return discovery, plans


# ---------------------------------------------------------------------------
# SearXNG HTTP client — no live instance yet (issue #21)
# ---------------------------------------------------------------------------


def _strip_www(domain: str) -> str:
    """Strip a literal "www." prefix. `str.lstrip("www.")` is a common bug —
    it strips any leading characters in the set {w, .}, not the literal
    prefix "www." (e.g. it would mangle "wikipedia.org"). Use this instead.
    """

    return domain.removeprefix("www.")


@dataclass
class SearchResult:
    """One SearXNG result item, per its documented JSON search API shape."""

    title: str
    url: str
    content: str  # snippet
    engine: str | None = None
    score: float | None = None

    @property
    def domain(self) -> str:
        return _strip_www(urlparse(self.url).netloc.lower())


def _execute_searxng_query(query: str, timeout: float = 8.0) -> list[SearchResult]:
    """Run one query against SearXNG's documented public JSON search API:
    `GET /search?q=...&format=json`.

    # TODO(issue #21): SearXNG hosting is not decided/stood up yet — this
    # will fail to connect (or hang until timeout) until a real instance is
    # reachable at SEARXNG_BASE_URL. The request shape below matches
    # SearXNG's own documented API; nothing here should need to change once
    # a real instance exists, only the base URL / auth wrapper if the chosen
    # hosting option ends up needing one (see docs/catalyst-notes.md's
    # "no built-in auth" caveat).
    """

    url = f"{SEARXNG_BASE_URL}/search"
    try:
        response = requests.get(url, params={"q": query, "format": "json"}, timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        logger.warning(
            "SearXNG request failed (expected tonight — no live instance yet, "
            "see issue #21). query=%r base_url=%r",
            query,
            SEARXNG_BASE_URL,
            exc_info=True,
        )
        return []

    return [
        SearchResult(
            title=item.get("title", ""),
            url=item.get("url", ""),
            content=item.get("content", ""),
            engine=item.get("engine"),
            score=item.get("score"),
        )
        for item in payload.get("results", [])
    ]


# ---------------------------------------------------------------------------
# Domain-quality scoring + clustering
# ---------------------------------------------------------------------------

# Deliberately small and honest about being a starting point, not a finished
# reliability model — CLAUDE.md: "sectors without a dedicated source
# integration still work, just score lower, honestly reflecting reduced
# verification depth." Unknown domains get a neutral-low default, not zero.
_HIGH_QUALITY_DOMAINS = {
    "wikipedia.org": 0.75,  # tertiary source, good for orientation, not proof
    "reuters.com": 0.95,
    "apnews.com": 0.95,
    "bbc.com": 0.9,
    "bbc.co.uk": 0.9,
    "nytimes.com": 0.85,
    "npr.org": 0.85,
}
_LOW_QUALITY_DOMAIN_HINTS = ("blogspot.", "medium.com", "reddit.com", "quora.com")
_DEFAULT_DOMAIN_SCORE = 0.4
_GOV_EDU_BONUS = 0.15


def score_domain_quality(url: str) -> float:
    """Return a 0-1 domain-quality score, used to filter/rank BEFORE
    clustering (CLAUDE.md: "domain-quality scoring happens before
    clustering"). Not a verification score — this only ranks source
    reliability by domain reputation, ahead of Call A's real
    fabrication/satire/AI-farm judgment.
    """

    domain = _strip_www(urlparse(url).netloc.lower())

    if domain in _HIGH_QUALITY_DOMAINS:
        return _HIGH_QUALITY_DOMAINS[domain]

    if domain.endswith((".gov", ".edu")):
        return min(1.0, _DEFAULT_DOMAIN_SCORE + _GOV_EDU_BONUS)

    if any(hint in domain for hint in _LOW_QUALITY_DOMAIN_HINTS):
        return 0.2

    return _DEFAULT_DOMAIN_SCORE


def _title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def cluster_results(
    results: list[SearchResult],
    similarity_threshold: float = 0.55,
    min_domain_score: float = 0.0,
) -> list[list[SearchResult]]:
    """Cluster SearXNG results into distinct candidate stories.

    Domain-quality filtering happens first (results below
    `min_domain_score` are dropped before clustering — SearXNG is noisy by
    design, per CLAUDE.md). Clustering itself uses simple title-similarity
    grouping (difflib) rather than embeddings — a deliberately lightweight
    approach appropriate for a hackathon-scale result set, not a claim that
    this is the final clustering approach.
    """

    filtered = [r for r in results if score_domain_quality(r.url) >= min_domain_score]
    # Rank by domain quality first so the "representative" item of each
    # cluster tends to be the highest-quality one.
    filtered.sort(key=lambda r: score_domain_quality(r.url), reverse=True)

    clusters: list[list[SearchResult]] = []
    for result in filtered:
        placed = False
        for cluster in clusters:
            if _title_similarity(cluster[0].title, result.title) >= similarity_threshold:
                cluster.append(result)
                placed = True
                break
        if not placed:
            clusters.append([result])

    return clusters


def fetch_top_results_per_cluster(
    clusters: list[list[SearchResult]], n: int = 2
) -> list[list[SearchResult]]:
    """Return the top `n` (by domain quality) results per cluster.

    CLAUDE.md: "snippets alone are too thin to judge a story ... expect to
    fetch the top 1-2 results per cluster." This function selects *which*
    results to fetch in full; the actual full-page fetch (as opposed to the
    snippet already returned by SearXNG) is left as a follow-up TODO — it
    needs its own fetch/parse/timeout handling and there's no live SearXNG
    result to test it against tonight.
    """

    top_per_cluster = []
    for cluster in clusters:
        ranked = sorted(cluster, key=lambda r: score_domain_quality(r.url), reverse=True)
        top_per_cluster.append(ranked[:n])
    return top_per_cluster


# ---------------------------------------------------------------------------
# "Show me more" — exclusion context + exhaustion detection
# ---------------------------------------------------------------------------


@dataclass
class ShowMeMoreSession:
    """Tracks state across "show me more" rounds for one ideation request.

    Fresh search every round (CLAUDE.md: "no pre-fetch caching — cost scales
    with actual demand"), but query generation is told which angle_types
    have already been surfaced so round 2 mechanically avoids round 1's
    angles rather than hoping the model varies on its own.
    """

    topic: str
    niche: str | None = None
    request_type: str | None = None  # set after first classify_query() call
    already_surfaced_angle_types: list[str] = field(default_factory=list)
    already_surfaced_urls: list[str] = field(default_factory=list)
    round_number: int = 0
    exhausted: bool = False
    exhaustion_reason: str | None = None

    def next_round(self, *, client=None) -> list[QueryPlan]:
        """Advance to the next round and produce a fresh set of query plans
        excluding already-surfaced angle types. Caller is responsible for
        actually executing the returned queries and calling
        `record_round_results()` afterward.
        """

        if self.exhausted:
            logger.info(
                "ShowMeMoreSession for topic=%r is already marked exhausted "
                "(%s) — returning no new queries.",
                self.topic,
                self.exhaustion_reason,
            )
            return []

        if self.request_type is None:
            self.request_type = classify_query(self.topic)

        self.round_number += 1

        if self.request_type == "broad":
            return generate_broad_queries(
                self.topic,
                self.niche,
                exclude_angle_types=self.already_surfaced_angle_types,
                client=client,
            )

        _discovery, plans = generate_specific_queries(
            self.topic,
            self.niche,
            exclude_angle_types=self.already_surfaced_angle_types,
            client=client,
        )
        return plans

    def record_round_results(
        self,
        plans: list[QueryPlan],
        clusters: list[list[SearchResult]],
    ) -> None:
        """Update exclusion context + run exhaustion detection after a round
        of results comes back."""

        self.already_surfaced_angle_types.extend(p.angle_type for p in plans)

        new_urls = [r.url for cluster in clusters for r in cluster]
        overlap = (
            len(set(new_urls) & set(self.already_surfaced_urls)) / len(new_urls)
            if new_urls
            else 1.0
        )
        self.already_surfaced_urls.extend(new_urls)

        if overlap >= 0.7 or not clusters:
            self.exhausted = True
            self.exhaustion_reason = (
                f"Round {self.round_number}: {overlap:.0%} URL overlap with prior "
                "rounds (or no new clusters) — likely exhausted for this topic. "
                "Say so honestly rather than serving progressively worse "
                "candidates (CLAUDE.md)."
            )
            logger.info(self.exhaustion_reason)
