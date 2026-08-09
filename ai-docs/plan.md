# mcp-agent — Plan (rewritten 2026-08-09, ~20:00)

**You are the `mcp-agent`, working in `scenepaper-mcp` on branch
`feature/mcp-server`. Read `agents/mcp-agent.md` for your role and `CLAUDE.md`
for the project rules before touching code.**

**You are unblocked as of tonight.** Issue #3 is resolved — the API Gateway
question that gated your entire scope has been answered, and there are three
live routes to wrap.

## First action: commit this plan file

Before any other work, commit **this file only** to `feature/mcp-server`:

```
git add ai-docs/plan.md
git commit -m "Add mcp-agent plan for the pipeline integration push"
git push
```

It is the record of what you were asked to do, so it should exist in git
before the work starts. This one commit does not need a checkpoint — it is
a doc file the user has already approved. **Everything after it does.**

## Follow the loop in CLAUDE.md

ORIENT → PLAN → ACT → VERIFY → **CHECKPOINT** → COMMIT. Present the diff and
wait for explicit approval before committing.

Stay inside this worktree. Do not edit `scenepaper-api`,
`scenepaper-catalyst`, or `scenepaper-ui`.

## Why this matters more than it looks

`CLAUDE.md` is explicit: *"MCP connection must be used during actual
development AND the product itself ships its own MCP server — this is the
hackathon differentiator, do not treat it as optional."* It is checklist-graded
and currently has **zero code**. Of everything outstanding, this is the item
most likely to cost marks by simply not existing.

---

## The architecture question is now answerable

The old blocker was "can a Catalyst function host MCP tool calls at all?"
What we now know:

- The API Gateway is **REST-only** — no streaming/SSE anywhere in its schema.
- Advanced I/O functions cap at **30 seconds**; the real pipeline runs as a Job
  (15-min budget) and returns a `job_id` immediately.
- Three live REST routes exist and are verified working.

**Recommended: run the MCP server as its own process** (Python, `mcp` SDK) that
makes HTTP calls to the Gateway routes. Rationale: it's how most MCP servers
are actually deployed, it sidesteps the 30s cap entirely, and each tool call
stays short because the slow work is already asynchronous behind `/generate`.
Hosting MCP *inside* Catalyst would fight both the REST-only gateway and the
timeout for no real benefit.

**Confirm this with the user before building** — it's an architecture decision,
and `agents/mcp-agent.md` tells you not to assume it.

Useful precedent: the Voicebox desktop app ships `voicebox-mcp` and mounts MCP
at `/mcp` on its own server. Worth a look at how it's structured, and worth
mentioning in the demo as a second real MCP integration.

---

## The live backend you're wrapping

Base URL: `https://scenepaper-60081628315.development.catalystserverless.in`

| Route | Behaviour |
|---|---|
| `POST /ideate` | `{"topic": "..."}` → candidate one-liners |
| `POST /generate` | `{"topic":..., "candidate":{...}}` → **202** + `job_id` + `paper_id` |
| `GET/PUT/DELETE /paper?id=<id>` | ScenePaper CRUD |

Three things that will trip you up:

1. **`?id=` is not `/paper/<id>`.** The Gateway rewrites each rule to a fixed
   path and cannot carry a per-request id.
2. **`/generate` is async.** It returns before the paper exists. A tool that
   claims to have generated a paper must either poll `GET /paper?id=` or
   honestly report "started, not finished" — do not pretend it's done.
3. **Generation takes 15–30+ seconds.** Keep each individual tool call short;
   never block an MCP call on the whole pipeline.

---

## Work item 1 — Scaffold the server (do this first)

**Tag: afk** once the architecture is confirmed.

Create a minimal MCP server that starts, registers one tool
(`list_available_stories` or `get_usage_status` — both are simple reads), and
responds to a real client. Prove the round trip before writing seven tools
against an unproven scaffold.

Keep the HTTP base URL configurable via env var, not hardcoded.

## Work item 2 — The seven tools

Per `CLAUDE.md`, each a thin wrapper over an existing route:

| Tool | Backing |
|---|---|
| `search_story_ideas(topic)` | `POST /ideate` |
| `generate_scene_paper(source_url)` | `POST /generate` (async — see above) |
| `get_scene_paper(topic)` | `GET /paper?id=` |
| `verify_source(paper_id)` | `GET /paper?id=`, surface `sources[]` + status |
| `generate_voiceover(paper_id)` | needs api-integration's TTS work first |
| `list_available_stories(category)` | needs a category-filtered list route |
| `get_usage_status(user_id)` | needs the UserProfile counter |

The last three depend on work not yet built. **Build the first four now**, and
have the others fail honestly with "not implemented yet" rather than returning
fabricated data. A tool that lies is worse than a tool that's missing —
especially in a product whose entire pitch is verification.

## Work item 3 — End-to-end validation

**Tag: hil.** Every tool called from a real MCP client, results checked by a
human. This is a demo moment: showing the pipeline driven entirely through
MCP tool calls, with no UI, is a strong differentiator.

---

## Verification before any checkpoint

Each tool exercised against the live routes, plus offline tests with a fake
HTTP layer so the suite doesn't depend on Catalyst being up.

## Order

1. Confirm the architecture (Option A vs B) with the user.
2. Work item 1 — scaffold and prove one tool.
3. Work item 2 — the four buildable tools.
4. Revisit the remaining three as their dependencies land.
