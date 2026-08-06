from backend.clients.pexels_client import PexelsClient


def test_pexels_client_warns_when_no_api_key(monkeypatch, caplog):
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    PexelsClient(api_key=None)
    assert any("PEXELS_API_KEY is not set" in r.message for r in caplog.records)


def test_search_images_returns_empty_list_when_request_fails(monkeypatch):
    client = PexelsClient(api_key="fake-key-not-real")
    # No live Pexels key tonight (issue #10) — this call is expected to fail
    # (network error or 401) and should degrade to an empty list, not raise.
    results = client.search_images_for_scene("lighthouse", per_page=1)
    assert results == []
