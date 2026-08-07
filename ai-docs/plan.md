# api-integration-agent — Plan (written 2026-08-07)

Written as part of a full plan-file pass across all 4 active agents before
simultaneous deployment. Read `CLAUDE.md`'s Agent Loop Strategy first.

## Real current state (verified directly against code, not task-breakdown's
stale checkboxes)

- **Isolation architecture (Call A/B) is real and structurally enforced**,
  not aspirational: `verify_and_score_candidate()` has no `profile`
  parameter at all (asserted via `inspect.signature` in tests);
  `structure_scene_paper()` requires `VerificationResult` as a required
  positional arg; `CALL_B_RESPONSE_SCHEMA` has zero score/confidence/flag
  fields (also asserted in tests).
- `profile_parser.py`, `verification.py`, `searxng_client.py` (query
  classification, clustering, domain-quality scoring) — real logic, no
  network needed to test, all passing.
- `voicebox_client.py`, `pexels_client.py` — real HTTP client code, but the
  Voicebox endpoint path/payload shape is explicitly flagged as an
  unverified assumption.
- **This session (2026-08-07): `VERIFICATION_RULES_PROMPT` and
  `STRUCTURING_PROMPT` were drafted collaboratively with the user and
  written into `src/backend/clients/gemini_client.py`** — this was the
  single blocker keeping Call A/B from running at all (both raised
  `NotImplementedError` before today). Both calls are now callable
  end-to-end against a real Gemini key, pending real input to feed them.
- **`CALL_B_RESPONSE_SCHEMA` was also updated this session** to match
  CLAUDE.md's session-2 schema addendum, which the code had drifted from:
  `scenes[]` now has a real `script[]` (`{speaker, line, direction}`)
  instead of a plain `description` string, and `hooks[].text` /
  `scenes[].script[].line` are now `{text, verified}` span arrays instead
  of plain strings. A `_text_span_schema()` helper was added for this.
  `tests/test_gemini_client.py` was updated to match (3 obsolete
  placeholder-guard tests replaced with fake-client tests that exercise
  the real call path; all 6 tests pass).
- **Environment gotcha found and fixed this session**: this worktree's
  `python3.9` environment is the same **global** Homebrew Python 3.9 used
  by `scenepaper-catalyst` (not a per-worktree venv). Installing
  `google-genai` bumped `typing-extensions` past what `zcatalyst-sdk==1.3.0`
  wants, breaking imports across both worktrees until re-pinned. Fixed for
  now (`typing-extensions>=4.14.1` — google-genai's pydantic-core needs
  this; `zcatalyst_sdk` still imports fine despite the version-conflict
  warning pip prints). **Real recommendation, not yet acted on**: give each
  worktree its own venv (`python3.9 -m venv .venv`) instead of sharing
  global site-packages — the next dependency add in either worktree will
  hit this exact collision again otherwise.

## Work item 1 — Test the real prompts against the live Gemini key (UNBLOCKED)

Tag: **hil** (first real output needs a human read, per CLAUDE.md's
calibration philosophy — you want to see if an 8/10 output actually looks
like an 8/10).

1. Hand-construct 1-2 `SourceMaterial` lists for a real story you know
   well enough to judge the output against (bypasses SearXNG entirely —
   this doesn't need issue #21 resolved to test Call A/B in isolation).
2. Call `verify_and_score_candidate(candidate_summary, sources)` for real
   (needs `GEMINI_API_KEY` populated in `.env` — confirmed present, len 53).
3. Feed its `VerificationResult` into `structure_scene_paper(...)` and read
   the actual scene script / hook / span output.
4. Judge: does the score feel calibrated (not flattering)? Does the
   structuring voice match the category tone rules? Are `{text, verified}`
   spans landing on the right clauses? Adjust the two prompt strings
   directly based on this — they're a first pass, not final.

## Work item 2 — SearXNG hosting (issue #21, still genuinely open)

No Docker, no Homebrew formula, no pip package for SearXNG on this
machine — confirmed exhaustively in a prior session. The only real path is
a manual/source install (clone, Python venv, `pip install`, configure
`settings.yml`). Default port `8888` already matches `.env.example`. This
is a **hil** decision (where does this actually run — locally for the
demo, or a small always-on host) before a fresh session should attempt the
install unattended. Blocks: the ideation search step (`/ideate`'s real
implementation, replacing catalyst-agent's `_stub_run_ideation_search`).

## Work item 3 — Voicebox verification (still genuinely open)

Desktop app installed and runs; CLI not installed. Unconfirmed whether the
GUI app alone exposes the REST API Voicebox needs, and on what port —
last check found no listening process. **hil**: launch Voicebox, find its
real listening port, hit its actual endpoint, update
`VOICEBOX_BASE_URL` + `voicebox_client.py`'s assumed `/api/tts` path to
match reality.

## Known test-suite caveat

`test_pexels_client.py::test_search_images_returns_empty_list_when_request_fails`
fails in this sandboxed environment (a fake-key call reached
api.pexels.com and got real data back, when it should have failed/returned
`[]`) — flagged in a prior research pass as possibly a sandbox network
artifact rather than reproducible on the real dev machine. Re-run this one
test on the actual dev machine before trusting either the pass or the
fail.

## Order for a fresh session executing this file

1. Work item 1 (unblocked, most valuable, do this first — validates the
   whole two-call architecture end-to-end for the first time).
2. Work items 2/3 are both **hil** and independent of each other and of
   item 1 — surface them to the user rather than attempting either
   unattended.
