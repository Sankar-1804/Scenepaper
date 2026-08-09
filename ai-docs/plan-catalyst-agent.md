# catalyst-agent — Plan (updated 2026-08-10)

**You are the `catalyst-agent`, working in `scenepaper-catalyst` on branch
`feature/catalyst-backend`. Read `agents/catalyst-agent.md` for your role and
`CLAUDE.md` for the project rules before touching code.**

## Follow the loop in CLAUDE.md

ORIENT → PLAN → ACT → VERIFY → **CHECKPOINT** → COMMIT. Present the diff and
wait for explicit approval before committing. Never push to `main`.

Stay inside this worktree. Do not edit `scenepaper-api`, `scenepaper-ui`, or
`scenepaper-mcp`.

---

## What is done (verified live — don't redo it)

**The full end-to-end pipeline works against the real Catalyst project.**

Base URL: `https://scenepaper-60081628315.development.catalystserverless.in`

| Route | Status |
|---|---|
| `POST /ideate` | 200, returns real SearXNG+Gemini candidates (~25.2s — see timing risk below) |
| `POST /generate` | 202 + `job_id` + `paper_id`; Job runs to SUCCESS, writes a full ScenePaper to NoSQL |
| `GET/PUT/DELETE /paper?id=<id>` | reads NoSQL with correct 400/404 |

**Last confirmed working paper:** `3a6d29ff-cb6e-49b4-a666-42f5397aa913` ("The Failure That Built Slack", 6.0/10, 2026-08-10).

**What the pipeline actually does end to end:**
1. `POST /ideate` → classify topic → SearXNG queries → domain-quality filter → cluster → Gemini one-liners → 3-4 candidates
2. `POST /generate` → Advanced I/O function submits a Job, returns `{job_id, paper_id}` immediately
3. Job function: Call A (Gemini verification/scoring) → Call B (Gemini structuring → full schema) → Pexels images per scene → NoSQL write
4. `GET /paper?id=` → reads the document, normalizes types (Decimal→float, "true"/"false"→bool)

**Latest commits on `feature/catalyst-backend`:**
- `9e2847e` — Fix NoSQL type round-trip: Decimal→float, BOOL str→bool in GET response
- `3371fb4` — Wire real ideation + Pexels images; harden job function pipeline

**Test suite:** `python3.9 tests/test_scenepaper_pipeline_routes.py` — 37/37 pass, fully offline (in-memory fake SDK). Never require live credentials for the test suite.

### Hard-won gotchas — these cost real time, don't rediscover them

1. **`job_name` is capped at 20 characters.** Longer values make Catalyst
   reject the *entire* job submission with `INVALID_INPUT`. Pinned by a check in the test harness.
2. **The SDK must be initialized with the request.**
   `zcatalyst_sdk.initialize(req=request)` at the top of `handler()` is load-bearing — every NoSQL call and job submission inherits the credentials from this. Never move it.
3. **`.job` is a `@property`, not a method.** `app.job_scheduling().job` —
   calling it as `.job()` raises `TypeError: 'Job' object is not callable`.
4. **The API Gateway rewrites each rule to a fixed target path**, so it cannot
   carry a per-request id. That's why `/paper` takes `?id=`. `catalyst deploy` does **not** touch Gateway rules.
5. **Never let a NoSQL failure return silently.** Keep failures logged.
6. `catalyst functions:add` defaults `requirements.txt` to `zcatalyst-sdk==1.4.0` (Python ≥3.10). **Always repin to `1.3.0`.**
7. **`_floats_to_decimal` + `_drop_null_values` must both run before `to_nosql()`**. Floats raise TypeError in TypeSerializer; None raises INVALID_INPUT from Catalyst.
8. **`_normalize_nosql_item` must run on every GET response** — Catalyst may return `{"BOOL": "true"}` (JSON string, not JSON boolean), and TypeDeserializer passes it through unchanged. Without normalization, every verified-false span renders as verified fact in the UI.

---

## Open work items

### Item A — Deploy + live type verification (pending, next step)

The type fix (`_normalize_nosql_item`) is committed and pushed but **not yet deployed**. The live backend still has the old behavior.

```
catalyst deploy --only functions
```

Then: one `POST /generate` call to confirm `confidence_score` is a JSON number
and `verified` is a JSON boolean in the GET response. Each live run costs
**2 Gemini calls against a 20/day/model quota** — budget carefully.

### Item B — ONE_LINER_PROMPT review (DRAFT, human-in-the-loop required)

`functions/scenepaper_pipeline_job/backend/ideation.py`'s `ONE_LINER_PROMPT` is
marked DRAFT pending user review — per `docs/task-breakdown.md` Tasklist 2.1
("Ideation prompt tuning" is a `hil` item). Do not finalize it without the user
reviewing it against real SearXNG output.

### Item C — /ideate timing risk (known, do not fix by trimming quality)

`POST /ideate` runs in ~25.2s against the 30s Advanced I/O cap. Intermittent
timeouts are expected. **Correct fix:** move ideation into its own Job function
with polling (matching the `/generate` pattern). Do not trim search quality as
a shortcut — it destroys the verification moat. See `docs/catalyst-notes.md`
"Operational risks" for the full note.

### Item D — SEARXNG_BASE_URL is an ngrok tunnel URL

The `SEARXNG_BASE_URL` Cache value is an ngrok URL that dies on tunnel restart.
If `/ideate` fails for no apparent reason, check this first — update the Cache
value to the new tunnel URL. See `docs/catalyst-notes.md` for the full note.

### Item E — Vendored backend/ sync

`functions/*/backend/` are vendored copies of `scenepaper-api/src/backend/`.
As of 2026-08-10 the vendored copies are **ahead** (5xx retry logic, ideation.py
not yet on scenepaper-api's main). Those changes must land on scenepaper-api or
the copies are the authoritative source, which is backwards. See
`docs/catalyst-notes.md` "Operational risks" for the full rule.

### Item F — UserProfile (only if there's real slack)

No route touches `UserProfile` yet. The free-tier counter
(`scenepapers_generated_count`, `free_limit = 10`) needs somewhere to live.
Coordinate with `ui-agent` on what it needs rather than inventing an API.

---

## Verification before any checkpoint

```
cd /Users/sankara-17600/Desktop/Personal/Projects/scenepaper-catalyst
python3.9 tests/test_scenepaper_pipeline_routes.py
```
This is a standalone script, **not** pytest-discoverable — run it directly.
All checks pass offline. Keep it that way.

To deploy: `catalyst deploy --only functions` from this directory.
