from backend.clients.searxng_client import (
    ANGLE_TYPES,
    QueryPlan,
    SearchResult,
    ShowMeMoreSession,
    classify_query,
    cluster_results,
    score_domain_quality,
)


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
