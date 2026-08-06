"""
Voicebox client — local TTS for voiceover generation.

Per `ai-docs/Handoff-session 1.md` section 7 (docs/api-notes.md does not yet
have a Voicebox section — TODO for docs-agent, not touched by this agent):
Voicebox (voicebox.sh) is a local, open-source voice studio app running
entirely on the builder's Mac (MLX/Metal), exposing a REST + WebSocket API
and its own MCP server. No cloud calls, no built-in authentication — must
stay behind a tunnel/VPN if ever exposed beyond localhost, never the open
internet.

Decision already made (per agents/api-integration-agent.md): **Voicebox
runs locally for the actual demo, called directly from the machine running
the pipeline** — not through a cloud tunnel for Day 2. The Cloudflare-Tunnel
"Remote Mode" path is documented as future intent only.

# TODO(issue #10): Voicebox's local setup status is unconfirmed for this
# session — is the app even installed/running right now? The exact REST
# endpoint path below (`/api/tts`) is an ASSUMPTION, not confirmed against
# real Voicebox docs/console — the source material available in this repo
# describes the *capabilities* (REST API, paralinguistic tags, voice profile
# selection) but not the literal endpoint path or request/response field
# names. Confirm both against the running app (or voicebox.sh's own API
# docs) before relying on this for the demo, and update this docstring +
# the endpoint constant once confirmed.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

VOICEBOX_BASE_URL = os.environ.get("VOICEBOX_BASE_URL", "http://localhost:8000")
# ASSUMED endpoint path — see module TODO above.
VOICEBOX_TTS_ENDPOINT_PATH = "/api/tts"

# Category -> voice/personality mapping, per ai-docs/Handoff-session 1.md
# section 7. Voice personality tuning is HIL work (agents/api-integration-agent.md
# "Default mode" section) — do not add/change entries here as an agent.
# "curious" has no documented mapping yet; falls back to a neutral default
# below rather than inventing a new personality choice.
VOICE_PROFILES = {
    "suspense": {"voice_id": "ryan", "personality_id": "narrator_suspense"},
    "cautionary": {"voice_id": "aiden", "personality_id": "narrator_cautionary"},
    "human_interest": {"voice_id": "ryan", "personality_id": "narrator_warm"},
}

# TODO(human, issue #10 / #15): no documented voice/personality choice exists
# for the "curious" category yet (voice personality tuning is hil work, see
# agents/api-integration-agent.md). Falling back to the human_interest
# profile is a placeholder, not a real design decision — replace once a
# narrator_curious personality is actually created in Voicebox.
_DEFAULT_VOICE_PROFILE = VOICE_PROFILES["human_interest"]


def voice_profile_for_category(category: str) -> dict:
    profile = VOICE_PROFILES.get(category)
    if profile is None:
        logger.warning(
            "No documented Voicebox voice profile for category=%r — falling "
            "back to the human_interest profile as a placeholder. See "
            "TODO(human, issue #10/#15) in voicebox_client.py.",
            category,
        )
        return _DEFAULT_VOICE_PROFILE
    return profile


@dataclass
class VoiceoverResult:
    audio_bytes: bytes
    content_type: str = "audio/wav"


class VoiceboxClient:
    """Thin wrapper over Voicebox's local REST API.

    Skips voice cloning entirely (decision already made — use preset voices
    only, see agents/api-integration-agent.md).
    """

    def __init__(self, base_url: str | None = None, timeout: float = 60.0):
        self.base_url = base_url or VOICEBOX_BASE_URL
        self.timeout = timeout

    def health_check(self) -> bool:
        """Best-effort check that a local Voicebox instance is actually
        reachable. Returns False (never raises) if it isn't.

        # TODO(issue #10): Voicebox's running status is unconfirmed tonight
        # — this will return False until the app is actually launched, which
        # is expected.
        """

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

    def synthesize(
        self,
        text: str,
        voice_id: str,
        personality_id: str | None = None,
    ) -> VoiceoverResult | None:
        """POST text to Voicebox's local TTS endpoint and return the
        generated audio.

        `text` should already have breath-point pause tags inserted (see
        `insert_breath_pauses` below) before being passed in here — this
        method does not do that itself, to keep pause-insertion testable in
        isolation from the network call.

        # TODO(issue #10): request payload field names below (`text`,
        # `voice_id`, `personality_id`) are the most natural mapping onto
        # what's documented, but are NOT confirmed against Voicebox's actual
        # API. No live instance to test against tonight.
        """

        payload = {
            "text": text,
            "voice_id": voice_id,
            "personality_id": personality_id,
        }

        try:
            response = requests.post(
                f"{self.base_url}{VOICEBOX_TTS_ENDPOINT_PATH}",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException:
            logger.warning(
                "Voicebox synthesize() failed (expected tonight — local "
                "setup unconfirmed, see issue #10). voice_id=%r",
                voice_id,
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
