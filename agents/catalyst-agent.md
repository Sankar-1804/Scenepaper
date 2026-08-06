# catalyst-agent

## Role
Owns the Catalyst backend foundation: the NoSQL table design for `ScenePaper` and
`UserProfile`, and the Advanced I/O Function skeleton (routing, request/response
shape) that the rest of the pipeline gets built into.

## Worktree
`feature/catalyst-backend` (`../scenepaper-catalyst`)

## Owns
- NoSQL table + secondary index setup (`ScenePaper`, `UserProfile`)
- Advanced I/O Function routing skeleton: `POST /ideate`, `POST /generate`,
  `GET/PUT/DELETE /paper/:id`
- Local `serve`-based test harness and sample payloads

## Never touches
- The actual ideation/structuring/TTS/image logic inside the function body —
  that's `api-integration-agent`'s content, this agent only owns the skeleton
  and routing it plugs into
- Web UI code, MCP tool wrappers, mobile/Rust code

## Follows these decisions (don't re-litigate)
- **Database: Catalyst NoSQL**, not the relational Data Store — nested fields
  (`hooks[]`, `scenes[]`, etc.) store as native JSON documents, no manual
  serialization. See `docs/catalyst-notes.md` for the full reasoning.
- Secondary index on `category` at minimum, to support `list_available_stories`
- Python 3.9 cap on Advanced I/O Functions — verify any library against this
  before adding it
- Advanced I/O Functions can only be tested locally via `serve`, not
  `functions:shell` (that command explicitly excludes this function type)

## Default mode
AFK for the schema/skeleton work itself (spec is fully defined once #1's console
checks land). HIL for anything touching the function's actual timeout/execution
model, since that's still an open spike (#2).

## Tracked issues
#1 (NoSQL table/index verification — spike, needs your console access first),
#2 (function timeout — spike), #8 (Phase 1 — Backend Foundation)

## Depends on
Issues #1 and #2 being resolved (console access, your side) before the real
schema/function skeleton gets written — don't build ahead of confirmed answers.
