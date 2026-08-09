# ui-agent — Plan (rewritten 2026-08-09, ~20:00)

**You are the `ui-agent`, working in `scenepaper-ui` on branch
`feature/web-ui`. Read `agents/ui-agent.md` for your role and `CLAUDE.md` for
the project rules before touching code.**

This supersedes the earlier version of this file — the screens you were asked
to rebuild are done, and there is now a real backend to talk to.

## First action: commit this plan file

Before any other work, commit **this file only** to `feature/web-ui`:

```
git add ai-docs/plan.md
git commit -m "Add ui-agent plan for the pipeline integration push"
git push
```

It is the record of what you were asked to do, so it should exist in git
before the work starts. This one commit does not need a checkpoint — it is
a doc file the user has already approved. **Everything after it does.**

## Follow the loop in CLAUDE.md

ORIENT → PLAN → ACT → VERIFY → **CHECKPOINT** → COMMIT. Present the diff and
wait for explicit approval before committing.

Stay inside this worktree. Do not edit `scenepaper-api`,
`scenepaper-catalyst`, or `scenepaper-mcp`.

---

## What is already done

All screens are built and working against mock data: topic input, candidate
picker (scores, flags, show-more, exhaustion and failure states, suppressed
candidates with their reason), paper detail, scene detail (script lines,
speaker variants, pause pills, claims list), playback at both paper and scene
scope, the mocked usage counter and export toggle, plus a generation-progress
screen.

**Your `claims[]` design won.** The schema fork you flagged rather than
resolving alone was taken to the user, who adopted your shape as canonical.
`CALL_B_RESPONSE_SCHEMA` and `CLAUDE.md` now match the web client:

- `hooks[].text` → `[{text, verified}]` inline spans
- `scenes[].claims[]` → `[{text, verified, sources[]}]`
- `scenes[].script[].line` → **plain string**

No UI change needed for that — the backend moved to you. Flagging it instead
of silently picking one was the right call.

---

## The backend is now real

Base URL: `https://scenepaper-60081628315.development.catalystserverless.in`

| What you call | Route |
|---|---|
| search candidates | `POST /ideate` — body `{"topic": "..."}` |
| generate a paper | `POST /generate` — body `{"topic": ..., "candidate": {...}}` |
| fetch a paper | `GET /paper?id=<paper_id>` |
| update / delete | `PUT` / `DELETE /paper?id=<paper_id>` |

**Read this carefully — it will bite you otherwise:**

1. **Papers use `?id=`, NOT `/paper/<id>`.** The API Gateway rewrites each rule
   to a fixed path and cannot carry a per-request id, so the query-param form
   is the only one that works. Do not "fix" this to look more RESTful.
2. **`POST /generate` is asynchronous.** It returns **202** immediately with
   `{job_id, paper_id, status: "accepted"}` — the paper does **not** exist yet.
   You must poll `GET /paper?id=<paper_id>` until it appears. Your existing
   generation-progress screen is exactly the right home for this.
3. **Generation is slow — expect 15–30+ seconds.** The structuring call alone
   is ~15s. Design the poll interval and the progress copy around that, and
   make sure a slow run doesn't look like a hang.
4. `/ideate` currently returns `[stub] Candidate A/B/C`. That's expected —
   `api-integration-agent` is making it real. Build against the real shape and
   the stubs will simply become good data.
5. No authentication. Don't add auth handling.

---

## Work item 1 — Switch off mock data (your main task)

**Tag: hil** — this is the first time the UI meets a real backend, and things
will be uneven.

`mockApi.js` has `USE_MOCK_DATA = true` and three functions that throw
`"Real API not wired up yet"`. Wire them to the routes above.

Steps:
1. Put the base URL in one place, overridable, so it isn't scattered.
2. Implement the real paths for `searchStoryIdeas`, `generateScenePaper`, and
   the paper fetch. **Keep the mock path working** behind the flag — a
   backend outage 20 minutes before a demo should not leave you with nothing
   to show. This is deliberate demo insurance, not indecision.
3. Implement polling for `POST /generate` → `GET /paper?id=` on the progress
   screen, with a sane timeout and an honest failure state.
4. Handle real error shapes: the backend returns
   `{"status":"error","message":"..."}` with 400/404/502/503. Surface the
   message rather than a generic failure.
5. Verify in a real browser, not just by reading code. The `run` skill's prior
   approach (a scratch Playwright install) worked well.

## Work item 2 — Decide where the design files live

Three files are sitting **untracked at the repo root**: `Design README.md`,
`ScenePaper.dc.html`, `nocturne-styles.css`. `CLAUDE.md` calls the repo layout
"fixed and non-negotiable" (`README.md`, `ai-docs/`, `docs/`, `agents/`,
`src/`), so root-level files break it. `ScenePaper.dc.html` also references
`./support.js` and `_ds/` paths that don't exist, so it isn't functional.

Move them under `docs/` or add them to `.gitignore` — ask the user which, and
don't commit them to root either way.

## Work item 3 — Visual polish (deferred, HIL)

Explicitly a judgment call per `agents/ui-agent.md`. Do work item 1 first —
a polished UI showing fake data is worth less than a plain one showing real
data. Get the user to look at the real end-to-end flow before spending more
time here.

---

## Verification before any checkpoint

```
node --check src/web/js/app.js
node --check src/web/js/mockApi.js
node --check src/web/js/splash.js
```
Then actually run it and click through: topic → candidates → generate →
progress → paper → scene detail.

## Housekeeping

`src/web/public/mock-voiceover.wav` (1.8 MB) is committed and referenced by
`mockApi.js` — keep it. It's your fallback if real TTS isn't ready by demo
time, and the player already handles it.

Two dead refs in `app.js` (`els.status`, `els.submitButton`) are captured but
never used — harmless leftovers from the Screen 1 rebuild, clean up if you're
in the area.
