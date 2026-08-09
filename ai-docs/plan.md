# api-integration-agent — Plan (rewritten 2026-08-09, ~20:00)

**You are the `api-integration-agent`, working in `scenepaper-api` on branch
`feature/api-integration`. Read `agents/api-integration-agent.md` for your
role and `CLAUDE.md` for the project rules before touching code.**

This supersedes the earlier version of this file entirely — the situation
changed a lot on 2026-08-09 and most of the old blockers are gone.

## First action: commit this plan file

Before any other work, commit **this file only** to `feature/api-integration`:

```
git add ai-docs/plan.md
git commit -m "Add api-integration-agent plan for the pipeline integration push"
git push
```

It is the record of what you were asked to do, so it should exist in git
before the work starts. This one commit does not need a checkpoint — it is
a doc file the user has already approved. **Everything after it does.**

## Follow the loop in CLAUDE.md

ORIENT → PLAN → ACT → VERIFY → **CHECKPOINT** → COMMIT. Step 5 is
non-negotiable: present the diff and wait for explicit approval before
committing. Do not commit or push without it.

Stay inside this worktree. Do not edit `scenepaper-catalyst`,
`scenepaper-ui`, or `scenepaper-mcp` — other sessions own those.

---

## What is already true (verified live, don't re-derive)

**Everything below has been tested against real services today. Trust it.**

### Gemini works
- `gemini_client.py` Call A (verify) and Call B (structure) both run live and
  return good output. Prompts are written.
- `GEMINI_MODELS` is a **fallback chain** — it walks models, then API keys, on
  429/quota and 404/retired. `gemini-2.5-flash` is dead on our account (404),
  `gemini-2.0-flash` has a free-tier limit of 0. Primary is `gemini-3.6-flash`.
- **Quota is the scarce resource: RPD 20 per model, per key.** Failed calls
  still consume it. Budget your live testing; prefer fake clients in tests.
  Add `GEMINI_API_KEY_2`/`_3` to `.env` if the user has provided them.

### SearXNG is running
- Live at **`http://localhost:8888`**, JSON enabled. `.env` already points at it.
- Restart if needed: `~/Desktop/Personal/Projects/searxng/start-scenepaper.sh --bg`
- Verified working: `_execute_searxng_query` returns ~28 results;
  `score_domain_quality` discriminates correctly (BBC 0.90, blogs 0.40);
  `cluster_results` collapses 28 → 16 clusters.
- Engines `wikidata`/`brave`/`startpage` fail or CAPTCHA; `duckduckgo` and
  `google cse` carry it. That's fine — don't chase it.

### Voicebox is running
- The Mac app ships its own server — no CLI install needed.
- **Use the port the GUI app itself is running on, NOT a server you start
  yourself.** The app runs `voicebox-server` with
  `--data-dir "~/Library/Application Support/sh.voicebox.app"`, and that data
  dir is where the voice profiles live. A server started without it sees an
  empty profile list and looks broken. Find the live port with:
  `ps aux | grep voicebox-server` — look for the one with `--data-dir`.
  As of 2026-08-09 it was **port 17493**, but it changes between app launches,
  so detect it rather than hardcoding.
- A voice profile named **"Vivian"** exists (CustomVoice, `en`, engine
  `qwen_custom_voice`). Fetch its real id from `GET /profiles`.
- **The real API is `POST /generate` with `{profile_id, text, instruct, ...}`**,
  then `GET /generate/{id}/status` and `GET /audio/{generation_id}`.
- `voicebox_client.py` currently assumes `/api/tts`, **which does not exist**.
  That is a real bug to fix.
- `instruct` maps naturally onto our per-line `direction` field — use it.
- Do NOT test against port 8000 — a stale `python -m http.server` squats there
  and returns 200, which has already caused one false positive.

### The Catalyst backend is live
Base URL: `https://scenepaper-60081628315.development.catalystserverless.in`

| Route | Notes |
|---|---|
| `POST /ideate` | works; returns stub candidates (yours to make real) |
| `POST /generate` | works; returns 202 + `job_id` + `paper_id`, job completes |
| `GET/PUT/DELETE /paper?id=<id>` | works; **query param, NOT a path segment** |

The Gateway cannot carry a changing ID in a path, hence `?id=`. Use that form.

### Schema (settled — do not re-litigate)
Rule 5 has **two mechanisms**, deliberately:
- `hooks[].text` → `[{text, verified}]` inline spans
- `scenes[].claims[]` → `[{text, verified, sources[]}]`, and
  `scenes[].script[].line` is a **plain string**

This matches the web client exactly. `CALL_B_RESPONSE_SCHEMA` already emits it.

---

## Work item 1 — Make `/ideate` real (highest value, fully unblocked)

The ideation pipeline is **already written** in `searxng_client.py` —
`classify_query`, `generate_broad_queries`, `discover_specific_axis`,
`generate_specific_queries`, `_execute_searxng_query`, `score_domain_quality`,
`cluster_results`, `fetch_top_results_per_cluster`, `ShowMeMoreSession`. It has
simply never been run end to end against a live SearXNG, which now exists.

**Tag: hil** — candidate quality is a judgment call, and the query-generation
prompts need tuning against real output.

Steps:
1. Write one function that takes a topic and returns 3–4 candidate one-liners,
   chaining the pieces above. Put it somewhere obvious, e.g.
   `src/backend/ideation.py`.
2. Run it against real topics. Read the actual candidates. Are they genuinely
   distinct stories, or near-duplicates? Tune the query-generation prompts
   until the angles differ structurally (era/industry/failure-vs-success),
   not just in wording.
3. Always return the top 3 regardless of score. The only suppression is
   fabrication/satire/AI-content-farm, and suppressed candidates are still
   returned with their reason. See CLAUDE.md's trust model.
4. Watch quota — every query-generation call is a Gemini call.

## Work item 2 — Build the orchestrator (the keystone)

**Nothing currently calls Call A or Call B.** `verify_and_score_candidate` and
`structure_scene_paper` have zero callers outside tests, and
`profile_parser.build_profile_preferences_as_data()` — the injection defense —
is never invoked. This is the single most important missing piece: it is what
`catalyst-agent` will import to make the job function real.

**Tag: afk** for the wiring; **hil** for reading the first real output.

Write `src/backend/orchestrator.py` exposing roughly:

```python
def generate_scene_paper(topic, candidate, profile_md_text=None) -> dict:
    # 1. fetch source material for the chosen candidate (SearXNG + fetch)
    # 2. Call A: verify_and_score_candidate(candidate_summary, sources)
    # 3. profile_parser.build_profile_preferences_as_data(profile_md_text)
    # 4. Call B: structure_scene_paper(source_material, verification, framed)
    # 5. return a dict shaped like CLAUDE.md's ScenePaper entity
```

Hard requirements, all already enforced in code — do not weaken them:
- Call A must never receive profile content (it has no parameter for it).
- Call B receives Call A's `VerificationResult` as a fixed input.
- Profile text must go through `build_profile_preferences_as_data()`;
  `structure_scene_paper` will raise if handed unframed strings.
- Surface `parsed.warnings` / `dropped_sections` rather than discarding them.

Design it so `catalyst-agent` can import and call it from the Job function
with minimal ceremony. Keep it importable under **Python 3.9** — that is the
Catalyst runtime cap.

## Work item 3 — Fix `voicebox_client.py` and wire TTS

**Tag: afk** once a voice profile exists.

1. Replace the assumed `/api/tts` with the real `POST /generate`
   (`profile_id` + `text`, plus `instruct` from the scene's `direction`).
2. Handle the async shape: submit → poll `GET /generate/{id}/status` →
   fetch `GET /audio/{generation_id}`.
3. Read the profile id from `GET /profiles` rather than hardcoding it.

## Work item 4 — Images

**Tag: afk.** `pexels_client.py` works. Note: Pexels' search endpoint returns
results **without** an API key — verified live — so the docstring claiming
401s is wrong. Fix that comment while you're there. Wire per-scene keyword →
image into whatever the orchestrator returns.

---

## Verification before any checkpoint

```
cd /Users/sankara-17600/Desktop/Personal/Projects/scenepaper-api
PYTHONPATH=src python3.9 -m pytest src/tests/ -o testpaths= -q
```
61 tests currently pass. Keep them passing. Prefer fake clients over live
calls in tests — real calls burn the daily quota the demo depends on.

## Order

1. Work item 2 (orchestrator) — **do this first**, catalyst-agent is waiting on it.
2. Work item 1 (real ideation).
3. Work items 3 and 4 as time allows.
