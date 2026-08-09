"""
Voicebox client — local TTS for voiceover generation.

Voicebox (voicebox.sh) is a local, open-source voice studio app running
entirely on the builder's Mac (MLX/Metal), exposing a REST + WebSocket API
and its own MCP server. No cloud calls, no built-in authentication — must
stay behind a tunnel/VPN if ever exposed beyond localhost, never the open
internet.

Decision already made (per agents/api-integration-agent.md): **Voicebox
runs locally for the actual demo, called directly from the machine running
the pipeline** — not through a cloud tunnel. Skips voice cloning entirely;
only preset voice profiles are used.

Everything below marked "live-confirmed" was verified against a real running
Voicebox instance on 2026-08-09 (ai-docs/plan.md), replacing an earlier
version of this module written entirely against assumed field names
(`/api/tts`, `voice_id`/`personality_id`) that do not exist in the real API
and would have failed outright at demo time.

Live-confirmed facts that shape this module:
  - The GUI app's own server logs its real port on the command line
    (`--port <N>`), which changes between launches — see
    `_detect_voicebox_base_url()`. Do NOT trust a fixed default; a stale
    `python -m http.server` has previously squatted on port 8000 and
    returned 200, producing a false "it's up" positive.
  - `POST /generate` requires an explicit `engine` field that MATCHES the
    target profile's engine — omitting it does not fall back to the
    profile's own engine. Confirmed live: posting without `engine` against a
    `qwen_custom_voice` preset profile 400s with "Preset profile ... only
    supports engine 'qwen_custom_voice', not 'qwen'". So `engine` is always
    read off the profile dict, never hardcoded or omitted.
  - `GET /generate/{id}/status` is a Server-Sent-Events STREAM (repeated
    `data: {...}` JSON lines), not a single-shot poll — `GET /generate/{id}`
    (no `/status`) 404s, confirmed live. `_wait_for_completion()` consumes
    the stream directly.
  - The exact terminal status string was never actually observed live (a
    cold model load ran past several minutes still reporting
    "loading_model" without completing in-session) — success/failure is
    therefore judged from the `error` field, which IS confirmed present on
    every status payload, rather than matching an unconfirmed success
    string.
  - `GET /audio/{generation_id}` is real per its own routing, but its
    response was never actually reached live in this session (no generation
    reached a terminal state within the testing window) — treat as
    real-but-unconfirmed.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

VOICEBOX_BASE_URL = os.environ.get("VOICEBOX_BASE_URL", "http://localhost:8000")


def _detect_voicebox_base_url() -> str | None:
    """Find the live Voicebox GUI app's actual port by inspecting running
    processes for its own `voicebox-server` (identified by `--data-dir`
    pointing at the app's support directory, per ai-docs/plan.md) and
    reading its `--port` argument straight off the command line.

    Best-effort: returns None (never raises) if `ps` isn't available or no
    matching process is found, so callers fall back to VOICEBOX_BASE_URL --
    which may be stale, since the port changes between app launches.
    """

    try:
        output = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=3.0, check=True
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return None

    for line in output.splitlines():
        if "voicebox-server" not in line or "--data-dir" not in line:
            continue
        match = re.search(r"--port\s+(\d+)", line)
        if match:
            return f"http://localhost:{match.group(1)}"

    return None


# Only one real Voicebox profile exists so far ("Vivian", a preset voice) --
# see module docstring. Per-category personality profiles (suspense/
# cautionary/warm/curious) don't exist yet in Voicebox. Voice personality
# tuning is HIL work (agents/api-integration-agent.md "Default mode") -- do
# not invent new profile names here; this maps every category to the one
# real profile as an honest placeholder, not a design decision.
DEFAULT_VOICE_PROFILE_NAME = "Vivian"

VOICE_PROFILE_NAME_BY_CATEGORY = {
    "suspense": DEFAULT_VOICE_PROFILE_NAME,
    "cautionary": DEFAULT_VOICE_PROFILE_NAME,
    "human_interest": DEFAULT_VOICE_PROFILE_NAME,
    "curious": DEFAULT_VOICE_PROFILE_NAME,
}


def voice_profile_name_for_category(category: str) -> str:
    name = VOICE_PROFILE_NAME_BY_CATEGORY.get(category)
    if name is None:
        logger.warning(
            "No documented Voicebox profile mapping for category=%r -- "
            "falling back to %r. See TODO(human, issue #10/#15) in "
            "voicebox_client.py.",
            category,
            DEFAULT_VOICE_PROFILE_NAME,
        )
        return DEFAULT_VOICE_PROFILE_NAME
    return name


def _engine_for_profile(profile: dict) -> str | None:
    """A profile's engine for `POST /generate`'s required `engine` field.
    Preset voices carry it as `preset_engine`; non-preset/designed voices
    (not used here -- voice cloning is skipped) would carry `default_engine`
    instead, so both are checked."""

    return profile.get("preset_engine") or profile.get("default_engine")


@dataclass
class VoiceoverResult:
    audio_bytes: bytes
    content_type: str = "audio/wav"


# Statuses observed or documented as in-progress. Everything else is treated
# as terminal -- see module docstring on why an exact success string isn't
# matched instead.
_IN_PROGRESS_STATUSES = {"queued", "loading_model", "generating"}


class VoiceboxClient:
    """Thin wrapper over Voicebox's local REST API.

    Skips voice cloning entirely (decision already made — use preset voices
    only, see agents/api-integration-agent.md).
    """

    def __init__(self, base_url: str | None = None, timeout: float = 60.0):
        self.base_url = base_url or _detect_voicebox_base_url() or VOICEBOX_BASE_URL
        self.timeout = timeout

    def health_check(self) -> bool:
        """Best-effort check that a local Voicebox instance is actually
        reachable. Returns False (never raises) if it isn't."""

        try:
            response = requests.get(self.base_url, timeout=3.0)
            return response.status_code < 500
        except requests.RequestException:
            logger.warning(
                "Voicebox health check failed — is the app running locally? "
                "(base_url=%r)",
                self.base_url,
                exc_info=True,
            )
            return False

    def list_profiles(self) -> list[dict]:
        """GET /profiles -- live-confirmed shape (id, name, voice_type,
        preset_engine, default_engine, ...). Returns the raw dicts rather
        than a dataclass; the real schema carries more fields than this
        client currently needs, and wrapping it would just be one more
        place to keep in sync as Voicebox's own schema evolves."""

        try:
            response = requests.get(f"{self.base_url}/profiles", timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            logger.warning(
                "Voicebox list_profiles() failed — is the app running "
                "locally? (base_url=%r)",
                self.base_url,
                exc_info=True,
            )
            return []

    def find_profile_by_name(self, name: str) -> dict | None:
        for profile in self.list_profiles():
            if profile.get("name") == name:
                return profile
        return None

    def synthesize(
        self,
        text: str,
        profile: dict,
        instruct: str | None = None,
        *,
        max_wait: float = 180.0,
    ) -> VoiceoverResult | None:
        """Generate voiceover audio for `text` using `profile` (a dict from
        `list_profiles()`/`find_profile_by_name()` -- not just a bare
        profile_id, because `engine` must be read off the profile; see
        module docstring on why it can't be omitted or guessed).

        `text` should already have breath-point pause tags inserted (see
        `insert_breath_pauses` below) before being passed in here. `instruct`
        maps onto our per-line `direction` field (CLAUDE.md's script schema)
        -- pass that scene line's direction text through as-is.

        Submits, waits for the SSE status stream to reach a terminal state
        (up to `max_wait` seconds), then fetches the resulting audio.
        Returns None on any failure -- never raises for a normal
        network/generation failure, only logs and returns None.
        """

        engine = _engine_for_profile(profile)
        if engine is None:
            logger.warning(
                "Voicebox profile %r has neither preset_engine nor "
                "default_engine -- cannot synthesize.",
                profile.get("name"),
            )
            return None

        payload = {"profile_id": profile["id"], "text": text, "engine": engine}
        if instruct:
            payload["instruct"] = instruct

        try:
            response = requests.post(
                f"{self.base_url}/generate", json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            generation = response.json()
        except requests.RequestException:
            logger.warning(
                "Voicebox synthesize() failed to submit for profile=%r.",
                profile.get("name"),
                exc_info=True,
            )
            return None

        generation_id = generation.get("id")
        if not generation_id:
            logger.warning(
                "Voicebox /generate response had no 'id' field: %r", generation
            )
            return None

        final_status = self._wait_for_completion(generation_id, max_wait=max_wait)
        if final_status is None or final_status.get("error"):
            logger.warning(
                "Voicebox generation %r did not complete successfully: %r",
                generation_id,
                final_status,
            )
            return None

        return self._fetch_audio(generation_id)

    def _wait_for_completion(self, generation_id: str, max_wait: float) -> dict | None:
        """Consume the `/generate/{id}/status` SSE stream until a terminal
        status is reached or `max_wait` elapses. See module docstring: this
        is a stream, not a single-shot poll."""

        deadline = time.monotonic() + max_wait
        try:
            response = requests.get(
                f"{self.base_url}/generate/{generation_id}/status",
                timeout=self.timeout,
                stream=True,
            )
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                if time.monotonic() > deadline:
                    logger.warning(
                        "Voicebox generation %r did not complete within %.0fs.",
                        generation_id,
                        max_wait,
                    )
                    response.close()
                    return None
                if not raw_line or not raw_line.startswith("data:"):
                    continue
                payload = json.loads(raw_line[len("data:") :].strip())
                if payload.get("status") not in _IN_PROGRESS_STATUSES:
                    response.close()
                    return payload
        except requests.RequestException:
            logger.warning(
                "Voicebox status stream failed for generation %r.",
                generation_id,
                exc_info=True,
            )
            return None

        return None

    def _fetch_audio(self, generation_id: str) -> VoiceoverResult | None:
        """GET /audio/{generation_id} -- real endpoint, response shape
        unconfirmed live (see module docstring)."""

        try:
            response = requests.get(
                f"{self.base_url}/audio/{generation_id}", timeout=self.timeout
            )
            response.raise_for_status()
        except requests.RequestException:
            logger.warning(
                "Voicebox fetch_audio() failed for generation %r.",
                generation_id,
                exc_info=True,
            )
            return None

        return VoiceoverResult(
            audio_bytes=response.content,
            content_type=response.headers.get("Content-Type", "audio/wav"),
        )


# ---------------------------------------------------------------------------
# Breath-point pause insertion
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_LONG_SENTENCE_WORD_THRESHOLD = 25


def insert_breath_pauses(
    text: str,
    pause_tag: str = "[pause]",
    long_sentence_word_threshold: int = _LONG_SENTENCE_WORD_THRESHOLD,
) -> str:
    """Insert Voicebox paralinguistic `[pause]` tags at natural breath
    points in `text`, ahead of Tier-1 voiceover generation.

    Tier 1 scope only (CLAUDE.md): "a single consistent voice reading
    story_body, with pauses inserted at breath points ... Per-scene
    pacing-tag-aware delivery ... is a refinement, not a Day-1 requirement."
    This function works on a flat story_body string, not per-scene — that
    per-scene refinement is Tier 2 (see video-agent/pacing work, issue #15).

    Heuristic (deliberately simple, not model-driven):
      - A breath point after every sentence (end of `.`/`!`/`?`).
      - An additional mid-sentence breath point at the first comma past the
        midpoint of any sentence longer than `long_sentence_word_threshold`
        words — long unbroken sentences read run-on without one.
    """

    sentences = [s for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s]
    paused_sentences = []

    for sentence in sentences:
        words = sentence.split()
        if len(words) > long_sentence_word_threshold and "," in sentence:
            comma_positions = [i for i, ch in enumerate(sentence) if ch == ","]
            midpoint = len(sentence) // 2
            split_at = next((p for p in comma_positions if p >= midpoint), comma_positions[-1])
            sentence = f"{sentence[: split_at + 1]} {pause_tag}{sentence[split_at + 1:]}"
        paused_sentences.append(sentence)

    # A breath point after every sentence, including the last one.
    return f" {pause_tag} ".join(paused_sentences) + f" {pause_tag}"
