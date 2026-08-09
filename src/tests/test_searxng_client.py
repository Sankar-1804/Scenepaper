from backend.clients import gemini_client
from backend.clients.searxng_client import (
    ANGLE_TYPES,
    QueryPlan,
    SearchResult,
    ShowMeMoreSession,
    classify_query,
    cluster_results,
    discover_specific_axis,
    generate_broad_queries,
    score_domain_quality,
)


class _FakeModels:
    """Mirrors test_gemini_client.py's fake -- kept local rather than shared
    so this file stays self-contained, same convention as the other test
    modules in this repo."""

    def __init__(self, parsed, fail_models=None):
        self._parsed = parsed
        self._fail_models = fail_models or {}
        self.attempted_models = []

    def generate_content(self, **kwargs):
        model = kwargs.get("model")
        self.attempted_models.append(model)
        if model in self._fail_models:
            raise _FakeAPIError(self._fail_models[model])
        return type("FakeResponse", (), {"parsed": self._parsed})()


class _FakeAPIError(Exception):
    def __init__(self, code):
        super().__init__(f"fake API error {code}")
        self.code = code


class _FakeClient:
    def __init__(self, parsed, fail_models=None):
        self.models = _FakeModels(parsed, fail_models=fail_models)


# ---------------------------------------------------------------------------
# Regression coverage for a real bug caught by a live smoke test: both
# generate_broad_queries (via _generate_query_plans) and discover_specific_axis
# used to call gemini_client.models.generate_content(model="gemini-2.5-flash")
# directly, bypassing gemini_client's model-fallback chain entirely -- exactly
# the model that 404s on this account (gemini_client.py's GEMINI_MODELS
# comment). Any live ideation call would have failed outright.
# ---------------------------------------------------------------------------


def test_generate_broad_queries_never_hardcodes_the_retired_model():
    payload = [{"query": "q1", "angle_type": "underdog", "rationale": "r"}]
    client = _FakeClient(payload)

    generate_broad_queries("topic", client=client)

    assert "gemini-2.5-flash" not in client.models.attempted_models


def test_generate_broad_queries_falls_back_to_the_next_model_on_quota_exhaustion():
    payload = [{"query": "q1", "angle_type": "underdog", "rationale": "r"}]
    client = _FakeClient(payload, fail_models={gemini_client.GEMINI_MODELS[0]: 429})

    plans = generate_broad_queries("topic", client=client)

    assert plans[0].query == "q1"
    assert client.models.attempted_models == list(gemini_client.GEMINI_MODELS[:2])


def test_discover_specific_axis_falls_back_to_the_next_model_on_quota_exhaustion():
    payload = {
        "axis": "axis_2_framings",
        "documented_event_count_estimate": 1,
        "rationale": "r",
        "candidate_events": [],
    }
    client = _FakeClient(payload, fail_models={gemini_client.GEMINI_MODELS[0]: 429})

    result = discover_specific_axis("topic", client=client)

    assert result.axis == "axis_2_framings"
    assert client.models.attempted_models == list(gemini_client.GEMINI_MODELS[:2])


def test_classify_query_broad_hint_phrase():
    assert classify_query("motivational story about founders") == "broad"


def test_classify_query_short_named_entity_is_specific():
    assert classify_query("Snapchat") == "specific"


def test_classify_query_empty_defaults_to_broad():
    assert classify_query("   ") == "broad"


def test_classify_query_multi_word_proper_noun_is_specific():
    assert classify_query("Elizabeth Holmes") == "specific"


def test_query_plan_accepts_controlled_angle_type():
    plan = QueryPlan(query="x", angle_type="comeback", rationale="r")
    assert plan.angle_type in ANGLE_TYPES


def test_query_plan_warns_but_allows_uncontrolled_angle_type(caplog):
    QueryPlan(query="x", angle_type="not-a-real-angle", rationale="r")
    assert any("not in the controlled ANGLE_TYPES" in record.message for record in caplog.records)


def test_score_domain_quality_known_high_quality_domain():
    assert score_domain_quality("https://www.reuters.com/some/article") >= 0.9


def test_score_domain_quality_low_quality_hint():
    assert score_domain_quality("https://someuser.blogspot.com/post") < 0.4


def test_score_domain_quality_unknown_domain_gets_neutral_default():
    score = score_domain_quality("https://totally-unknown-site.example")
    assert 0.0 < score < 0.9


def test_score_domain_quality_gov_domain_gets_bonus():
    gov_score = score_domain_quality("https://www.archives.gov/some/record")
    unknown_score = score_domain_quality("https://totally-unknown-site.example")
    assert gov_score > unknown_score


def test_cluster_results_groups_similar_titles():
    results = [
        SearchResult(title="Snapchat's rise and fall in 2013", url="https://reuters.com/a", content="..."),
        SearchResult(title="Snapchat's rise and fall in 2013!", url="https://apnews.com/b", content="..."),
        SearchResult(title="A completely unrelated story about penguins", url="https://bbc.com/c", content="..."),
    ]
    clusters = cluster_results(results, similarity_threshold=0.8)
    assert len(clusters) == 2


def test_cluster_results_filters_by_min_domain_score():
    results = [
        SearchResult(title="a", url="https://reuters.com/a", content="..."),
        SearchResult(title="b", url="https://someuser.blogspot.com/b", content="..."),
    ]
    clusters = cluster_results(results, min_domain_score=0.5)
    all_urls = [r.url for cluster in clusters for r in cluster]
    assert "https://someuser.blogspot.com/b" not in all_urls
    assert "https://reuters.com/a" in all_urls


def test_show_me_more_session_records_exhaustion_on_full_overlap():
    session = ShowMeMoreSession(topic="Snapchat")
    plans = [QueryPlan(query="q1", angle_type="comeback", rationale="r")]
    clusters = [[SearchResult(title="t", url="https://reuters.com/a", content="c")]]

    session.record_round_results(plans, clusters)
    assert not session.exhausted  # first round: no prior overlap possible

    session.record_round_results(plans, clusters)
    assert session.exhausted
    assert session.exhaustion_reason is not None


def test_show_me_more_session_tracks_angle_types_across_rounds():
    session = ShowMeMoreSession(topic="Snapchat")
    plans = [QueryPlan(query="q1", angle_type="comeback", rationale="r")]
    session.record_round_results(plans, [])
    assert "comeback" in session.already_surfaced_angle_types
