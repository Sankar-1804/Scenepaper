# catalyst-agent — Plan (rewritten 2026-08-09, ~20:00)

**You are the `catalyst-agent`, working in `scenepaper-catalyst` on branch
`feature/catalyst-backend`. Read `agents/catalyst-agent.md` for your role and
`CLAUDE.md` for the project rules before touching code.**

This supersedes the earlier version of this file — your previous work item is
done, and the API Gateway blocker is resolved.

## First action: commit this plan file

Before any other work, commit **this file only** to `feature/catalyst-backend`:

```
git add ai-docs/plan.md
git commit -m "Add catalyst-agent plan for the pipeline integration push"
git push
```

It is the record of what you were asked to do, so it should exist in git
before the work starts. This one commit does not need a checkpoint — it is
a doc file the user has already approved. **Everything after it does.**

## Follow the loop in CLAUDE.md

ORIENT → PLAN → ACT → VERIFY → **CHECKPOINT** → COMMIT. Present the diff and
wait for explicit approval before committing. Never push to `main`.

Stay inside this worktree. Do not edit `scenepaper-api`, `scenepaper-ui`, or
`scenepaper-mcp`.

---

## What is already done (verified live — don't redo it)

**Your Phase 1 work is complete and deployed.** The whole HTTP surface works
against the real Catalyst project:

Base URL: `https://scenepaper-60081628315.development.catalystserverless.in`

| Route | Status |
|---|---|
| `POST /ideate` | 200, returns candidates, rejects a missing topic with 400 |
| `POST /generate` | 202 + `job_id` + `paper_id`; the job runs and reports SUCCESS |
| `GET/PUT/DELETE /paper?id=<id>` | reads NoSQL, correct 400/404 |

- **NoSQL CRUD is real** and reads are confirmed working against the live
  `ScenePaper` table (partition key `id`, secondary index `category_index`).
- **Job submission works**: Advanced I/O → Job Pool `scenepaper_job_pool`
  (`59024000000020001`) → Job function `scenepaper_pipeline_job`
  (`59024000000021001`). Verified: `job_status: SUCCESS`, 1.6s.
- Issues **#1, #2, #3** are resolved.

### Hard-won gotchas — these cost real time, don't rediscover them

1. **`job_name` is capped at 20 characters.** Longer values make Catalyst
   reject the *entire* job submission with `INVALID_INPUT`. Nothing in the SDK
   signals this. Pinned by a check in the test harness.
2. **The SDK must be initialized with the request.**
   `zcatalyst_sdk.initialize(req=request)` runs `parse_headers_from_request`,
   which establishes the invocation's credentials. Called bare, every job
   submission and every NoSQL call fails. It is now initialized once at the
   top of `handler()`; downstream bare calls inherit it. **Keep it that way.**
3. **`.job` is a `@property`, not a method.** `app.job_scheduling().job` —
   calling it (`.job()`) raises `TypeError: 'Job' object is not callable`.
   Note the asymmetry: `job_scheduling()` *is* a method.
4. **The API Gateway rewrites each rule to a fixed target path**, so it cannot
   carry a per-request id. That's why `/paper` takes `?id=`, not `/paper/<id>`.
   Three Gateway rules exist (`/ideate`, `/generate`, `/paper`), each with its
   Target URL suffix set. `catalyst deploy` does **not** touch Gateway rules.
5. **Never let a NoSQL failure return silently.** A bare
   `except: return None` makes a real outage indistinguishable from "not
   found". Failures are logged now — keep them logged.
6. `catalyst functions:add` defaults `requirements.txt` to
   `zcatalyst-sdk==1.4.0`, which needs Python ≥3.10 and breaks the 3.9 runtime.
   **Always repin to `1.3.0`.**

---

## Work item 1 — Make the Job function real (your main task)

`functions/scenepaper_pipeline_job/main.py` runs correctly but all **five
stages are stubs** — it returns `"[stub] {topic}"` and never touches Gemini,
SearXNG, TTS, images, or NoSQL. Making these real is what turns a working
skeleton into a working product.

**This depends on `api-integration-agent` landing `src/backend/orchestrator.py`
on `main` first.** Check whether it exists before starting. If it doesn't yet,
do work item 2 instead and come back.

Steps once the orchestrator exists:
1. Import the orchestrator into the Job function and replace the search +
   verify + structure stages with a single call to it.
2. Replace the final stage with a real NoSQL write of the returned ScenePaper
   document, keyed on the `paper_id` passed in as a job param.
3. Keep everything inside the Job function's 15-minute budget (the Advanced
   I/O front door is capped at 30s, which is why this split exists — and Call
   B alone takes ~15s, so the split is load-bearing, not optional).
4. Preserve `context.close_with_success()` / `close_with_failure()` semantics.
5. **Verify end to end for real:** `POST /generate`, then poll
   `GET /paper?id=<paper_id>` until the document appears. That round trip
   working is the definition of done for this item.

Dependency note: the Job function runs on **Python 3.9**. Anything the
orchestrator imports must be 3.9-compatible, and any new dependency must be
added to the function's own `requirements.txt` (keeping `zcatalyst-sdk==1.3.0`).

## Work item 2 — Prove NoSQL writes (small, unblocked, do this if blocked above)

Reads are confirmed. **Writes are not** — no route currently creates a
document (`_create_scenepaper` exists but nothing calls it), so the write path
has never run against real Catalyst.

Two things flagged and still unverified:
- `update_value: {'value': v}` comes from the SDK type stubs, not a live call.
- The SDK deserializes responses but sends requests raw, so writes may need
  typed values (e.g. `{'S': 'text'}`) for non-scalar fields.

Write one throwaway probe that inserts a small document, reads it back, updates
it, and deletes it, against the real table. Report what the real payload shape
has to be. That finding directly de-risks work item 1's final stage.

## Work item 3 — UserProfile (only if there's slack)

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
All checks currently pass and it runs fully offline with an in-memory fake SDK.
Keep it that way: tests must not require live Catalyst credentials.

To deploy: `catalyst deploy --only functions` from this directory.

## Known cosmetic debt

`functions/scenepaper_pipeline_job/main.py` around lines 104–112 still carries
a `TODO(issue #1)` documenting the **wrong** API (`app.datastore().table(...)`
/ `insert_row`). Issue #1 is closed and the sibling file proves `nosql()` is
correct. Fix that comment as part of work item 1 so it stops misleading people.
