"""
Verification/scoring data shapes shared by Call A (verification) and Call B
(structuring) in gemini_client.py, plus the platform-owned suppression policy.

See CLAUDE.md > "Search, verification & trust model" before changing anything
here. Two rules this module exists to enforce in code, not just in docs:

1. Suppression is the ONLY exception to "always show top 3 regardless of
   score" — and it is limited to outright fabrications, satire, and
   AI-content-farms. A suppressed candidate is never dropped from the
   response; it is always returned with `suppressed=True` and a
   `suppression_reason`.
2. Confidence score and binary flags are two separate signals. A thinly
   sourced (but not contradicted) story is `single source only`, not the
   same thing as `sources conflict`. Never conflate the two into one number.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class VerificationFlag(str, Enum):
    """Binary flags — orthogonal to the x/10 confidence score.

    Per CLAUDE.md: "thinly-sourced is not the same as contradicted, and
    flags tell the creator exactly what to go check."
    """

    SOURCES_CONFLICT = "sources conflict"
    SINGLE_SOURCE_ONLY = "single source only"
    UNVERIFIED_ORIGIN = "unverified origin"
    CLAIM_NOT_FOUND_IN_PRIMARY_SOURCES = "claim not found in primary sources"


class SuppressionReason(str, Enum):
    """The ONLY grounds on which a candidate/source may be suppressed.

    Deliberately narrow. Low confidence alone is never a valid suppression
    reason — see module docstring.
    """

    FABRICATION = "fabrication"
    SATIRE = "satire"
    AI_CONTENT_FARM = "ai_content_farm"


# Score band + tag vocabulary is deliberately deferred (CLAUDE.md: "bands/
# vocabulary deliberately deferred until real SearXNG output exists"). Keep
# `tag` as a free-form short string from Call A for now, not an enum, so we
# don't lock in a vocabulary before there's real output to calibrate against.


@dataclass
class VerifiedSource:
    """Mirrors one entry of the ScenePaper.sources[] schema field.

    This is Call A's unit of output. Call B receives these as a fixed,
    already-scored input — it renders them, it does not recompute them.
    """

    title: str
    type: str
    date: str | None
    verified: bool
    confidence_score: float  # out of 10
    tag: str
    flags: list[VerificationFlag] = field(default_factory=list)
    suppressed: bool = False
    suppression_reason: SuppressionReason | None = None
    source_url: str | None = None

    def __post_init__(self) -> None:
        if self.suppressed and self.suppression_reason is None:
            raise ValueError(
                "A suppressed source must always carry a suppression_reason — "
                "silent suppression is explicitly disallowed by CLAUDE.md's "
                "trust model."
            )
        if not (0 <= self.confidence_score <= 10):
            raise ValueError(
                f"confidence_score must be in [0, 10], got {self.confidence_score}"
            )


@dataclass
class VerificationResult:
    """Full output of Call A for one candidate story.

    `overall_confidence_score` and `overall_tag` are Call A's judgment of the
    candidate as a whole; `sources` is the per-source breakdown. Call B
    receives this whole object as a required, fixed input (see
    gemini_client.structure_scene_paper) — there is no field on Call B's
    request or response that can alter any value here.
    """

    overall_confidence_score: float
    overall_tag: str
    overall_flags: list[VerificationFlag]
    sources: list[VerifiedSource]
    hook_overstatement_warning: str | None = None
    """Set when Call B's compression-distortion check (CLAUDE.md: 'does the
    hook overstate what sources actually support') flags the hook. Read-only
    from Call B's perspective — it can only report this, not use it to touch
    the score above."""


def enforce_always_show_top_three(
    ranked_candidates: list[VerificationResult],
) -> list[VerificationResult]:
    """No-op filter that documents/enforces the "always top 3" rule in code.

    Per CLAUDE.md: "always show top 3 regardless of score — suppressing low
    scorers silently narrows the library ... The only suppression is outright
    fabrications, satire, and AI-content-farms." This function exists so any
    future caller that's tempted to add a `if score < threshold: drop it`
    filter has to delete this call (and its docstring) to do so — a visible
    speed bump, not just a comment.

    Suppressed candidates are NOT removed here; suppression is per-source
    (`VerifiedSource.suppressed`) and is decided by Call A, never by this
    function threshold-filtering on score.
    """

    return ranked_candidates[:3] if len(ranked_candidates) > 3 else ranked_candidates
