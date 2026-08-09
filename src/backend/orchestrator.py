"""
Orchestrator — wires the isolated Call A / Call B split (gemini_client.py)
into the single entry point catalyst-agent's Job function imports.

Per docs/task-breakdown.md Tasklist 2.2 and CLAUDE.md's "Search, verification
& trust model": nothing before this module called verify_and_score_candidate()
or structure_scene_paper() outside tests, and profile_parser's whitelist /
data-framing defense was implemented but never invoked anywhere. This module
is the one place all three come together, in the one order the injection
defense requires:

    Call A (verification, isolated) -> profile_parser (whitelist + frame) ->
    Call B (structuring: sees framed profile prefs + Call A's fixed score)

Deliberately does NOT do ideation search/fetch itself (docs/task-breakdown.md
Work item 1, ordered after this one) -- `candidate` arrives with its source
material already resolved, i.e. by whatever already showed the user 3-4
one-liners and let them pick one. Keeping this module's only job "wire Call
A/B" keeps it a thin, catalyst-importable seam rather than re-implementing
ideation's fetch/cluster logic here too.

Must stay importable under Python 3.9 -- the Catalyst Advanced I/O Function
runtime cap (CLAUDE.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend import profile_parser
from backend.clients.gemini_client import (
    SourceMaterial,
    structure_scene_paper,
    verify_and_score_candidate,
)


@dataclass(frozen=True)
class Candidate:
    """The one candidate one-liner the user picked, plus its already-fetched
    source material. Building this is ideation's job (searxng_client.py /
    the not-yet-written ideation.py), not this module's -- see module
    docstring."""

    summary: str
    sources: list[SourceMaterial] = field(default_factory=list)


def _render_source_material(candidate: Candidate) -> str:
    """Render candidate.sources into the plain-text block Call B expects as
    `verified_source_material`.

    Mirrors the source_block Call A builds internally in
    gemini_client.verify_and_score_candidate -- Call B needs the same
    material, just as a single string rather than a list of SourceMaterial,
    since its prompt is assembled differently.
    """

    if not candidate.sources:
        return candidate.summary

    source_block = "\n\n".join(
        f"[{i + 1}] title: {s.title}\n"
        f"    type: {s.source_type}\n"
        f"    date: {s.date or 'unknown'}\n"
        f"    url: {s.url}\n"
        f"    content: {s.snippet_or_text}"
        for i, s in enumerate(candidate.sources)
    )
    return f"Candidate one-liner: {candidate.summary}\n\nSources:\n{source_block}"


def generate_scene_paper(
    topic: str,
    candidate: Candidate,
    profile_md_text: str | None = None,
    *,
    gemini_client=None,
) -> dict:
    """The pipeline's single entry point: Call A -> profile framing -> Call B.

    `gemini_client` is an optional injected SDK client, threaded through to
    both calls unchanged -- tests pass a fake here; real callers can omit it
    and let each call build its own real client (and its own model-fallback
    walk, see gemini_client.GEMINI_MODELS).

    Hard requirements enforced by construction, not just by convention here:
    - Call A (`verify_and_score_candidate`) has no parameter for profile
      content, so `profile_md_text` structurally cannot reach it.
    - Call B (`structure_scene_paper`) receives `verification` as a required
      positional argument and raises if handed profile strings that were not
      produced by `profile_parser.build_profile_preferences_as_data()`.

    Returns a dict shaped like CLAUDE.md's ScenePaper entity schema, plus
    `topic` and the profile parser's audit trail (`profile_warnings` /
    `profile_dropped_sections` / `profile_truncated_fields`) -- CLAUDE.md
    requires dropped/truncated profile.md sections be shown to the user, not
    silently discarded.
    """

    verification = verify_and_score_candidate(
        candidate.summary, candidate.sources, client=gemini_client
    )

    framed_preferences, parsed_profile = profile_parser.build_profile_preferences_as_data(
        profile_md_text or ""
    )

    draft = structure_scene_paper(
        _render_source_material(candidate),
        verification,
        framed_preferences,
        client=gemini_client,
    )

    draft["topic"] = topic
    draft["profile_warnings"] = parsed_profile.warnings
    draft["profile_dropped_sections"] = parsed_profile.dropped_sections
    draft["profile_truncated_fields"] = parsed_profile.truncated_fields
    return draft
