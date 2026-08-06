# mcp-agent

## Role
Wraps the already-built pipeline as MCP tool calls. This is the hackathon's
actual differentiator on the grading checklist — more so than how polished the
UI looks — so treat it as core work, not a final nice-to-have.

## Worktree
`feature/mcp-server` (`../scenepaper-mcp`)

## Owns
- The MCP server scaffold itself
- Each of the 7 tool wrappers: `search_story_ideas`, `get_scene_paper`,
  `verify_source`, `generate_scene_paper`, `generate_voiceover`,
  `list_available_stories`, `get_usage_status`
- End-to-end validation that each tool call actually works against the real
  pipeline, not just a mock

## Never touches
- The underlying pipeline logic — every tool call should be a thin wrapper
  around an already-working function from `catalyst-agent` /
  `api-integration-agent`, never a reimplementation
- Web UI code

## Follows these decisions (don't re-litigate)
- **Deliberately depends on Phases 1-4 landing first** — don't start wrapping
  functions that don't exist yet or are still changing shape.
- Whether a Catalyst function can host MCP at all is an **open spike (#3)** —
  don't assume the architecture until that's answered. The CLI surfaced an API
  Gateway feature (`apig:enable`) as a possible mechanism — check whether it
  supports the persistent/streaming connection MCP actually needs before
  building on top of it.
- If #3 comes back negative, the fallback (a thin separate process hosting MCP
  rather than the Catalyst function itself) is a real architecture change —
  flag it, don't quietly route around it.

## Default mode
Mostly AFK once Phases 1-4 are stable (each tool is a mechanical wrapper).
End-to-end validation of every tool call is HIL — this is exactly the kind of
thing that looks fine in isolation and breaks in the actual demo.

## Tracked issues
#3 (MCP-on-Catalyst feasibility — spike, blocks everything here), #12 (Phase 5
— MCP Layer)
