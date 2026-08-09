"""
Tests for voicebox_client.py, including the real-API rewrite (2026-08-09):
port auto-detection, /profiles lookup, and the /generate -> SSE status
stream -> /audio flow. All network calls are faked -- see
`_FakeResponse`/monkeypatched `requests.get`/`requests.post`, same pattern
as the other client test modules in this repo.
"""

import requests

from backend.clients import voicebox_client
from backend.clients.voicebox_client import (
    VoiceboxClient,
    insert_breath_pauses,
    voice_profile_name_for_category,
)


class _FakeResponse:
    def __init__(self, json_data=None, content=b"", headers=None, status_code=200, lines=None):
        self._json = json_data
        self.content = content
        self.headers = headers or {}
        self.status_code = status_code
        self._lines = lines or []

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self):
        return self._json

    def iter_lines(self, decode_unicode=True):
        return iter(self._lines)

    def close(self):
        pass


VIVIAN_PROFILE = {
    "id": "accf5061-5497-412e-a707-9637691588b1",
    "name": "Vivian",
    "voice_type": "preset",
    "preset_engine": "qwen_custom_voice",
    "default_engine": "qwen_custom_voice",
}


def test_insert_breath_pauses_adds_tag_after_each_sentence():
    text = "This is one sentence. This is another sentence."
    result = insert_breath_pauses(text)
    assert result.count("[pause]") == 2


def test_insert_breath_pauses_adds_mid_sentence_pause_for_long_sentences():
    long_sentence = (
        "This is a very long sentence that goes on and on, well past the "
        "point where a real narrator would need to take a breath before "
        "finishing it, because it just keeps going and going and going."
    )
    result = insert_breath_pauses(long_sentence, long_sentence_word_threshold=10)
    assert result.count("[pause]") == 2  # one mid-sentence + one at the end


# ---------------------------------------------------------------------------
# Category -> profile name (only one real profile exists so far, "Vivian")
# ---------------------------------------------------------------------------


def test_voice_profile_name_for_category_known_category():
    assert voice_profile_name_for_category("suspense") == "Vivian"


def test_voice_profile_name_for_category_unmapped_falls_back(caplog):
    name = voice_profile_name_for_category("not_a_real_category")
    assert name == "Vivian"
    assert any("No documented Voicebox profile mapping" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Port auto-detection -- live-confirmed the port changes between app
# launches and a stale server can squat on the naive default port.
# ---------------------------------------------------------------------------


def test_detect_voicebox_base_url_parses_port_from_ps_output(monkeypatch):
    ps_output = (
        "sankara-17600  90508  0.0  0.2  ??  S  8:18PM  0:19.06 "
        "/Applications/Voicebox.app/Contents/MacOS/voicebox-server "
        '--data-dir "/Users/sankara-17600/Library/Application Support/sh.voicebox.app" '
        "--port 17493 --parent-pid 90408\n"
    )
    monkeypatch.setattr(
        voicebox_client.subprocess,
        "run",
        lambda *a, **kw: type("R", (), {"stdout": ps_output})(),
    )
    assert voicebox_client._detect_voicebox_base_url() == "http://localhost:17493"


def test_detect_voicebox_base_url_returns_none_when_no_match(monkeypatch):
    monkeypatch.setattr(
        voicebox_client.subprocess,
        "run",
        lambda *a, **kw: type("R", (), {"stdout": "no voicebox process here\n"})(),
    )
    assert voicebox_client._detect_voicebox_base_url() is None


def test_client_prefers_an_explicit_base_url_over_detection(monkeypatch):
    monkeypatch.setattr(voicebox_client, "_detect_voicebox_base_url", lambda: "http://localhost:99999")
    client = VoiceboxClient(base_url="http://localhost:12345")
    assert client.base_url == "http://localhost:12345"


def test_client_falls_back_to_detected_port_when_no_explicit_url(monkeypatch):
    monkeypatch.setattr(voicebox_client, "_detect_voicebox_base_url", lambda: "http://localhost:17493")
    client = VoiceboxClient()
    assert client.base_url == "http://localhost:17493"


# ---------------------------------------------------------------------------
# /profiles
# ---------------------------------------------------------------------------


def test_list_profiles_returns_parsed_json(monkeypatch):
    monkeypatch.setattr(
        voicebox_client.requests, "get", lambda *a, **kw: _FakeResponse(json_data=[VIVIAN_PROFILE])
    )
    client = VoiceboxClient(base_url="http://localhost:17493")
    assert client.list_profiles() == [VIVIAN_PROFILE]


def test_find_profile_by_name_matches_on_name(monkeypatch):
    monkeypatch.setattr(
        voicebox_client.requests, "get", lambda *a, **kw: _FakeResponse(json_data=[VIVIAN_PROFILE])
    )
    client = VoiceboxClient(base_url="http://localhost:17493")
    assert client.find_profile_by_name("Vivian") == VIVIAN_PROFILE
    assert client.find_profile_by_name("Nobody") is None


# ---------------------------------------------------------------------------
# synthesize() -- engine must come from the profile (live-confirmed: a
# request without it 400s against a qwen_custom_voice preset profile).
# ---------------------------------------------------------------------------


def test_synthesize_reads_engine_from_the_profile_not_hardcoded(monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["payload"] = json
        return _FakeResponse(json_data={"id": "gen-1", "status": "generating", "error": None})

    monkeypatch.setattr(voicebox_client.requests, "post", fake_post)
    monkeypatch.setattr(
        VoiceboxClient, "_wait_for_completion", lambda self, gid, max_wait: {"error": None}
    )
    monkeypatch.setattr(
        VoiceboxClient,
        "_fetch_audio",
        lambda self, gid: voicebox_client.VoiceoverResult(audio_bytes=b"audio"),
    )

    client = VoiceboxClient(base_url="http://localhost:17493")
    result = client.synthesize("hello", VIVIAN_PROFILE, instruct="flat delivery")

    assert captured["payload"]["engine"] == "qwen_custom_voice"
    assert captured["payload"]["profile_id"] == VIVIAN_PROFILE["id"]
    assert captured["payload"]["instruct"] == "flat delivery"
    assert result.audio_bytes == b"audio"


def test_synthesize_refuses_a_profile_with_no_known_engine(caplog):
    client = VoiceboxClient(base_url="http://localhost:17493")
    result = client.synthesize("hello", {"id": "x", "name": "Mystery"})
    assert result is None
    assert any("neither preset_engine nor default_engine" in r.message for r in caplog.records)


def test_synthesize_returns_none_when_generation_reports_an_error(monkeypatch):
    monkeypatch.setattr(
        voicebox_client.requests,
        "post",
        lambda *a, **kw: _FakeResponse(json_data={"id": "gen-1", "status": "generating"}),
    )
    monkeypatch.setattr(
        VoiceboxClient,
        "_wait_for_completion",
        lambda self, gid, max_wait: {"error": "model crashed"},
    )

    client = VoiceboxClient(base_url="http://localhost:17493")
    assert client.synthesize("hello", VIVIAN_PROFILE) is None


# ---------------------------------------------------------------------------
# _wait_for_completion -- SSE stream, not a single-shot poll (live-confirmed:
# GET /generate/{id} without /status 404s).
# ---------------------------------------------------------------------------


def test_wait_for_completion_parses_sse_lines_and_stops_on_terminal_status(monkeypatch):
    lines = [
        'data: {"id": "gen-1", "status": "loading_model", "error": null}',
        "",
        'data: {"id": "gen-1", "status": "generating", "error": null}',
        "",
        'data: {"id": "gen-1", "status": "completed", "error": null, "audio_path": "/x.wav"}',
    ]
    monkeypatch.setattr(
        voicebox_client.requests,
        "get",
        lambda *a, **kw: _FakeResponse(lines=lines),
    )

    client = VoiceboxClient(base_url="http://localhost:17493")
    final = client._wait_for_completion("gen-1", max_wait=10.0)

    assert final["status"] == "completed"
    assert final["error"] is None


def test_wait_for_completion_judges_failure_via_the_error_field_not_a_status_string(monkeypatch):
    """The exact terminal status string was never confirmed live -- success
    vs failure is judged from `error`, which IS confirmed present on every
    payload, not from matching an assumed status value."""

    lines = [
        'data: {"id": "gen-1", "status": "failed", "error": "out of memory"}',
    ]
    monkeypatch.setattr(
        voicebox_client.requests,
        "get",
        lambda *a, **kw: _FakeResponse(lines=lines),
    )

    client = VoiceboxClient(base_url="http://localhost:17493")
    final = client._wait_for_completion("gen-1", max_wait=10.0)

    assert final["error"] == "out of memory"
