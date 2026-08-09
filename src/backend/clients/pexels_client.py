"""
Pexels client — supporting images fetched per scene keyword.

Per CLAUDE.md/docs/api-notes.md: Pexels was chosen over Unsplash (simple
key-based auth, generous free rate limit, good per-keyword search). Real
stock photos only — Tier 1 explicitly rules out AI-generated imagery
("too unreliable for a live demo on this timeline").

Live-confirmed 2026-08-09 (ai-docs/plan.md): Pexels' `/v1/search` endpoint
returns real results with NO `Authorization` header at all, and even with a
bogus one -- both return 200 with genuine photo data, not a 401. A real
`PEXELS_API_KEY` is still configured and sent when present (a future rate
limit or endpoint may require it), but the client does not depend on it to
function today, and nothing here should assume a missing/invalid key means
failure.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

PEXELS_SEARCH_ENDPOINT = "https://api.pexels.com/v1/search"
PEXELS_API_KEY_ENV_VAR = "PEXELS_API_KEY"


@dataclass
class PexelsImage:
    photo_id: int
    photographer: str
    url: str  # Pexels page URL (credit link)
    src_large: str  # direct image URL, "large" size
    alt: str | None = None


class PexelsClient:
    """Thin wrapper over Pexels' Search API.

    Docs: https://www.pexels.com/api/documentation/#photos-search
    Auth: `Authorization: <API key>` header (not "Bearer <key>" — Pexels'
    own docs use the bare key as the header value).
    """

    def __init__(self, api_key: str | None = None, timeout: float = 8.0):
        self.api_key = api_key or os.environ.get(PEXELS_API_KEY_ENV_VAR)
        self.timeout = timeout
        if not self.api_key:
            logger.info(
                "%s is not set — proceeding without it. Live-confirmed "
                "2026-08-09: Pexels' search endpoint returns real results "
                "even with no Authorization header, so this is not expected "
                "to fail. See docs/api-notes.md.",
                PEXELS_API_KEY_ENV_VAR,
            )

    def search_images_for_scene(
        self, keyword: str, per_page: int = 3
    ) -> list[PexelsImage]:
        """Search for stock photos matching a scene's keyword."""

        headers = {"Authorization": self.api_key or ""}
        params = {"query": keyword, "per_page": per_page}

        try:
            response = requests.get(
                PEXELS_SEARCH_ENDPOINT, headers=headers, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException:
            logger.warning(
                "Pexels request failed for keyword=%r (expected tonight — no "
                "API key configured yet, see issue #10).",
                keyword,
                exc_info=True,
            )
            return []

        return [
            PexelsImage(
                photo_id=photo["id"],
                photographer=photo.get("photographer", "unknown"),
                url=photo.get("url", ""),
                src_large=photo.get("src", {}).get("large", ""),
                alt=photo.get("alt"),
            )
            for photo in payload.get("photos", [])
        ]

    def search_with_fallback(
        self, primary_keyword: str, fallback_keywords: list[str], per_page: int = 3
    ) -> list[PexelsImage]:
        """Try `primary_keyword` first; if no good match, fall back through
        `fallback_keywords` in order (e.g. scene-specific keyword -> broader
        category keyword -> category-level generic keyword).

        "No good match" here means zero results — Pexels doesn't return a
        relevance score in the free search endpoint to threshold on, so this
        is deliberately simple rather than pretending to a quality signal
        that isn't actually available.
        """

        results = self.search_images_for_scene(primary_keyword, per_page)
        if results:
            return results

        for fallback in fallback_keywords:
            results = self.search_images_for_scene(fallback, per_page)
            if results:
                logger.info(
                    "No Pexels match for %r — fell back to %r.", primary_keyword, fallback
                )
                return results

        logger.warning(
            "No Pexels match for %r or any fallback keyword %r.",
            primary_keyword,
            fallback_keywords,
        )
        return []
