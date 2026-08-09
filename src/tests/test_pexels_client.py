import logging

import requests

from backend.clients import pexels_client as pexels_module
from backend.clients.pexels_client import PexelsClient


def test_pexels_client_logs_when_no_api_key(monkeypatch, caplog):
    """Downgraded from a warning to an info log 2026-08-09: a missing key is
    no longer expected to cause failures (see the live-confirmed note in
    pexels_client.py's module docstring), so caplog needs to be told to
    capture below its default WARNING threshold."""

    monkeypatch.delenv("PEXELS_API_KEY", raising=False)
    with caplog.at_level(logging.INFO):
        PexelsClient(api_key=None)
    assert any("PEXELS_API_KEY is not set" in r.message for r in caplog.records)


def test_search_images_returns_empty_list_when_request_fails(monkeypatch):
    """Graceful degradation on a failed request.

    Rewritten 2026-08-07: this previously used a deliberately-bad API key and
    assumed the call would 401 into the empty-list path. It does not — Pexels'
    search endpoint was verified to return HTTP 200 with real photos for a
    fake key AND for no Authorization header at all, so the test was asserting
    a failure that never happened. (A prior session guessed this was a sandbox
    network artifact; it isn't — the responses come from real Cloudflare/Pexels.)

    A bad key is not a reliable failure injection, so force the failure
    directly instead. This also makes the test deterministic and offline.
    """

    def _boom(*_args, **_kwargs):
        raise requests.RequestException("forced failure")

    monkeypatch.setattr(pexels_module.requests, "get", _boom)

    client = PexelsClient(api_key="fake-key-not-real")
    assert client.search_images_for_scene("lighthouse", per_page=1) == []


def test_search_images_parses_a_real_response_shape(monkeypatch):
    """Guards the parsing path, which had no coverage at all — every previous
    test only exercised the failure branch."""

    class _FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "photos": [
                    {
                        "id": 123,
                        "photographer": "Someone",
                        "url": "https://www.pexels.com/photo/123/",
                        "alt": "a lighthouse",
                        "src": {"large": "https://images.pexels.com/photos/123/large.jpg"},
                    }
                ]
            }

    monkeypatch.setattr(
        pexels_module.requests, "get", lambda *a, **k: _FakeResponse()
    )

    results = PexelsClient(api_key="k").search_images_for_scene("lighthouse")
    assert len(results) == 1
    assert results[0].photo_id == 123
    assert results[0].src_large.endswith("large.jpg")
    assert results[0].alt == "a lighthouse"
