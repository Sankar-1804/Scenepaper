"""
Tests for ideation.py — the search -> filter -> cluster plumbing that chains
searxng_client.py's already-written pieces (work item 1,
docs/task-breakdown.md Tasklist 2.1). Does not call live SearXNG or Gemini;
both are faked, same pattern as test_gemini_client.py / test_orchestrator.py.
"""

import pytest

from backend import ideation
from backend.clients.searxng_client import SearchResult


class _FakeModels:
    """Returns each payload in `payloads` in call order. One call per Gemini
    round trip: broad fan-out is one call; the specific flow is two
    (discovery, then query generation)."""

    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.calls = 0

    def generate_content(self, **kwargs):
        payload = self._payloads[self.calls]
        self.calls += 1
        return type("FakeResponse", (), {"parsed": payload})()


class _FakeClient:
    def __init__(self, payloads):
        self.models = _FakeModels(payloads)


def _broad_plans_payload():
    return [
        {"query": "query one", "angle_type": "underdog", "rationale": "r1"},
        {"query": "query two", "angle_type": "pivot", "rationale": "r2"},
    ]


# ---------------------------------------------------------------------------
# gather_candidate_clusters — broad flow
# ---------------------------------------------------------------------------


def test_gather_candidate_clusters_runs_a_query_per_plan_and_clusters_results(monkeypatch):
    executed_queries = []
    # Deliberately dissimilar titles per query -- cluster_results groups by
    # title similarity, so near-identical titles (e.g. "Result for X") would
    # collapse into one cluster regardless of which query produced them.
    titles_by_query = {
        "query one": "Company files for bankruptcy after decades of growth",
        "query two": "Startup wins award nobody expected it to win",
    }

    def fake_execute(query, timeout=8.0):
        executed_queries.append(query)
        return [
            SearchResult(
                title=titles_by_query[query], url=f"https://reuters.com/{query}", content="c"
            )
        ]

    monkeypatch.setattr(ideation, "_execute_searxng_query", fake_execute)

    request_type, clusters = ideation.gather_candidate_clusters(
        "motivational story", client=_FakeClient([_broad_plans_payload()])
    )

    assert request_type == "broad"
    assert executed_queries == ["query one", "query two"]
    assert len(clusters) == 2  # distinct titles -> distinct clusters


def test_gather_candidate_clusters_filters_low_quality_domains_before_clustering(monkeypatch):
    def fake_execute(query, timeout=8.0):
        return [
            SearchResult(title="Good source", url="https://reuters.com/a", content="c"),
            SearchResult(title="Spam source", url="https://some.blogspot.com/x", content="c"),
        ]

    monkeypatch.setattr(ideation, "_execute_searxng_query", fake_execute)

    _request_type, clusters = ideation.gather_candidate_clusters(
        "motivational story", client=_FakeClient([_broad_plans_payload()])
    )

    all_titles = {r.title for cluster in clusters for r in cluster.results}
    assert "Good source" in all_titles
    assert "Spam source" not in all_titles


def test_gather_candidate_clusters_caps_results_per_cluster(monkeypatch):
    def fake_execute(query, timeout=8.0):
        return [
            SearchResult(title="Same story", url="https://reuters.com/a", content="c1"),
            SearchResult(title="Same story", url="https://apnews.com/b", content="c2"),
            SearchResult(title="Same story", url="https://bbc.com/c", content="c3"),
        ]

    monkeypatch.setattr(ideation, "_execute_searxng_query", fake_execute)

    _request_type, clusters = ideation.gather_candidate_clusters(
        "motivational story",
        num_results_per_cluster=2,
        client=_FakeClient([_broad_plans_payload()]),
    )

    assert len(clusters[0].results) <= 2


def test_candidate_cluster_representative_is_the_first_result():
    cluster = ideation.CandidateCluster(
        results=[
            SearchResult(title="A", url="https://reuters.com/a", content="c"),
            SearchResult(title="B", url="https://reuters.com/b", content="c"),
        ]
    )
    assert cluster.representative.title == "A"


# ---------------------------------------------------------------------------
# gather_candidate_clusters — specific flow
# ---------------------------------------------------------------------------


def test_gather_candidate_clusters_uses_specific_flow_for_named_subjects(monkeypatch):
    def fake_execute(query, timeout=8.0):
        return [SearchResult(title=f"Result {query}", url="https://reuters.com/x", content="c")]

    monkeypatch.setattr(ideation, "_execute_searxng_query", fake_execute)

    discovery_payload = {
        "axis": "axis_1_events",
        "documented_event_count_estimate": 3,
        "rationale": "r",
        "candidate_events": ["Event A", "Event B", "Event C"],
    }
    plans_payload = [
        {"query": "q1", "angle_type": "comeback", "rationale": "r", "event_name": "Event A"},
        {"query": "q2", "angle_type": "pivot", "rationale": "r", "event_name": "Event B"},
        {"query": "q3", "angle_type": "downfall", "rationale": "r", "event_name": "Event C"},
    ]

    request_type, clusters = ideation.gather_candidate_clusters(
        "Snapchat", client=_FakeClient([discovery_payload, plans_payload])
    )

    assert request_type == "specific"
    assert len(clusters) >= 1


# ---------------------------------------------------------------------------
# The ONE_LINER_PROMPT boundary — reserved for the human, see module
# docstring. Must fail fast, before any search/Gemini round trip.
# ---------------------------------------------------------------------------


def test_generate_candidate_one_liners_is_blocked_until_the_human_writes_the_prompt():
    with pytest.raises(NotImplementedError, match="ONE_LINER_PROMPT"):
        ideation.generate_candidate_one_liners("any topic")
