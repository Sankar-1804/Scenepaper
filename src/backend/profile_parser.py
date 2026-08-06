"""
profile.md parser — the whitelist defense described in CLAUDE.md's
"Search, verification & trust model" section.

`profile.md` is a user-editable file (NOT the `UserProfile` DB entity) that
controls FORMAT ONLY: scene structure, categories, runtime target, tone, and
an avoid-list. It must never be able to touch verification rules (source
hierarchy, reliability weights, suppression thresholds) — those stay
platform-owned. This module is the first line of defense: anything not in
ALLOWED_FIELDS is dropped, loudly, before the file's contents go anywhere
near a prompt.

Second line of defense (also implemented here): values are framed as DATA
when interpolated into Call B's prompt, never as raw instruction text — see
`format_as_data_for_prompt()`. That framing is what keeps an injected
instruction inside profile.md from being executed rather than just quoted.

This module does not import gemini_client, and gemini_client's Call A
(verification) does not import this module at all — Call A structurally
never sees any of this. See gemini_client.py's module docstring.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# The only sections profile.md is allowed to declare. Anything else is
# dropped with a visible warning — never silently merged in, never silently
# dropped without a trace either.
ALLOWED_FIELDS = {
    "domain",
    "scene_structure",
    "runtime_target",
    "categories",
    "tone",
    "avoid",
}

# Free-text fields get a length cap so a single field can't smuggle in a
# huge block of injected instruction text. List-shaped fields
# (scene_structure, categories, avoid) are capped per-item instead, below.
FREE_TEXT_LENGTH_CAP = 500
LIST_ITEM_LENGTH_CAP = 200
MAX_LIST_ITEMS = 20


@dataclass
class ParsedProfile:
    """Result of parsing profile.md: the sanitized whitelist fields, plus a
    visible audit trail of anything dropped or truncated so the caller (and
    the demo, if needed) can show exactly what happened to the input."""

    fields: dict[str, object] = field(default_factory=dict)
    dropped_sections: list[str] = field(default_factory=list)
    truncated_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def get(self, key: str, default=None):
        return self.fields.get(key, default)


def _truncate(value: str, cap: int, field_name: str, result: ParsedProfile) -> str:
    if len(value) > cap:
        result.truncated_fields.append(field_name)
        msg = (
            f"profile.md field '{field_name}' exceeded {cap} chars "
            f"({len(value)} chars) — truncated."
        )
        logger.warning(msg)
        result.warnings.append(msg)
        return value[:cap]
    return value


def _parse_sections(raw_text: str) -> dict[str, str]:
    """Split a profile.md into `## section_name` -> raw body text blocks.

    Deliberately simple: profile.md is a small, flat, user-editable config,
    not a full document format. Headings are matched case-insensitively;
    body text is everything until the next heading.
    """

    sections: dict[str, list[str]] = {}
    current: str | None = None

    for raw_line in raw_text.splitlines():
        line = raw_line.strip()
        if line.startswith("#"):
            heading = line.lstrip("#").strip().lower().replace(" ", "_").replace("-", "_")
            current = heading
            sections.setdefault(current, [])
            continue
        if current is not None:
            sections[current].append(raw_line)

    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def _parse_list_field(body: str) -> list[str]:
    """`- item` / `* item` bullet lines, or comma-separated, whichever the
    section actually contains. Blank lines and stray prose are ignored."""

    items: list[str] = []
    for line in body.splitlines():
        stripped = line.strip().lstrip("-*").strip()
        if stripped:
            items.append(stripped)

    if not items and body.strip():
        # Fall back to comma-separated on one line.
        items = [part.strip() for part in body.split(",") if part.strip()]

    return items


def parse_profile_md(raw_text: str) -> ParsedProfile:
    """Parse raw profile.md text into the whitelisted, sanitized field set.

    Unrecognized sections are dropped and recorded in `dropped_sections` +
    `warnings` — never silently merged into the output. This is the whole
    point of the whitelist: a user (or an injected instruction hiding inside
    the file) cannot introduce a new field that some downstream code might
    later be tempted to treat as an instruction.
    """

    result = ParsedProfile()
    raw_sections = _parse_sections(raw_text)

    for name, body in raw_sections.items():
        if name not in ALLOWED_FIELDS:
            result.dropped_sections.append(name)
            msg = f"profile.md section '{name}' is not in ALLOWED_FIELDS — dropped."
            logger.warning(msg)
            result.warnings.append(msg)
            continue

        if not body:
            continue

        if name in ("scene_structure", "categories", "avoid"):
            items = _parse_list_field(body)[:MAX_LIST_ITEMS]
            capped_items = [
                _truncate(item, LIST_ITEM_LENGTH_CAP, f"{name}[]", result)
                for item in items
            ]
            result.fields[name] = capped_items
        else:
            # domain, runtime_target, tone: single free-text values.
            result.fields[name] = _truncate(body, FREE_TEXT_LENGTH_CAP, name, result)

    return result


def format_as_data_for_prompt(field_name: str, value: object) -> str:
    """Frame a parsed profile.md value as DATA for Call B's prompt — never
    as an instruction.

    Per CLAUDE.md: "frame passed-through values as data (\"the user's stated
    tone preference is: <value>\"), never as raw instructions." Call B's
    prompt should interpolate the *output* of this function, never the raw
    field value directly.
    """

    label = {
        "domain": "the user's stated content domain/niche",
        "scene_structure": "the user's stated preferred scene structure",
        "runtime_target": "the user's stated target runtime",
        "categories": "the user's stated preferred categories",
        "tone": "the user's stated tone preference",
        "avoid": "the user's stated avoid-list",
    }.get(field_name, f"the user's stated value for '{field_name}'")

    return f'{label} is: "{value}"'
