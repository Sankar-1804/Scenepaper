# mcp-agent — Plan (written 2026-08-07)

Written as part of a full plan-file pass across all 4 active agents before
simultaneous deployment. Read `CLAUDE.md`'s Agent Loop Strategy first — and
note this agent's scope explicitly depends on Phases 1-4 landing (each MCP
tool wraps an already-built function), so most of this plan is sequencing
and one shared blocker, not code to write yet.

## Real current state

- **Genuinely zero MCP server code anywhere in the repo** (confirmed via a
  repo-wide grep across all 6 worktrees for `fastmcp`, `mcp.server`,
  `@mcp.tool`, `ModelContextProtocol` — zero hits). `agents/mcp-agent.md`'s
  framing is accurate, not stale.
- Worktree was 2 commits behind `main` — fast-forward synced this session
  (`37b20d0` → `8cf8676`), clean, no local changes lost.
- Issue #12 (Phase 5 tracking) is OPEN, all 9 checklist items unchecked.

## Shared blocker with catalyst-agent — issue #3 (API Gateway route)

This is the same underlying gap documented in catalyst-agent's
`ai-docs/plan.md` work item 2: the Catalyst MCP's
`Configure_API_Gateway_Route` tool rejects its own documented `target` enum
values, and the CLI has no route-creation command at all (only
`apig:enable/disable/status`, confirmed by reading `catalyst --help`
directly this session). **A real route has to be created by hand in the
Catalyst console** — target `scenepaper_pipeline` (Advanced I/O Function).
This is a **hil** item, not something either agent's session can resolve
unattended. mcp-agent cannot answer its own architecture question (below)
until this exists and has been exercised with one real HTTP call.

## The architecture decision mcp-agent needs, once the route exists

`agents/mcp-agent.md` frames this as "don't assume the architecture until
#3 is answered" — the actual open question is:

- **Option A**: MCP server runs as its own process (could be local for the
  demo, e.g. a Python `fastmcp`/`mcp` SDK server), and each tool call is an
  HTTP request to the now-reachable `scenepaper_pipeline` Advanced I/O
  Function via its Gateway route.
- **Option B**: MCP server logic runs inside Catalyst itself (e.g. another
  Advanced I/O Function speaking the MCP protocol directly), no separate
  process to deploy/manage.

This is a **hil** decision for the user, not something to pick unattended —
flag it rather than guessing. (Leaning note, not a decision: Option A is
simpler to stand up for a hackathon demo and matches how most MCP servers
are actually deployed — a thin process wrapping HTTP calls — but this is
the user's call once the route is live and testable.)

## Work item — MCP server scaffold + 7 tools (BLOCKED until architecture
decision + Phases 1-4 land on `main`)

Per `CLAUDE.md`'s MCP tools list, once unblocked:
- `search_story_ideas(topic)` → wraps `POST /ideate`
- `get_scene_paper(topic)` → wraps `GET /paper/:id`
- `verify_source(paper_id)` → surfaces `sources[]`/verification_status
- `generate_scene_paper(source_url)` → wraps `POST /generate`
- `generate_voiceover(paper_id)` → wraps the TTS regeneration path
- `list_available_stories(category)` → wraps the `category_index` query
- `get_usage_status(user_id)` → wraps the free-tier/export-lock counters

Each is a thin wrapper — the real logic already lives in
catalyst-agent's/api-integration-agent's functions. Tag: **afk** once the
architecture decision is made and at least catalyst-agent's routes are
live, since the wrapping itself has no open judgment calls.

## Order for a fresh session executing this file

1. Do NOT start the 7-tool scaffold yet — everything below is blocked.
2. Check whether issue #3's route has been created (ask the user / check
   `catalyst apig:status` and try hitting the function's URL directly).
3. If the route exists: surface the architecture decision (Option A vs B)
   to the user before writing any server code.
4. Only after both of the above: scaffold the MCP server + first tool
   (`search_story_ideas`, since catalyst-agent's `/ideate` route already
   has a real (stubbed-search) implementation to wrap), then the rest.
