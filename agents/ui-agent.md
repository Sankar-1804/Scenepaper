# ui-agent

## Role
Owns the web client — the thing the hackathon panel actually looks at. Topic
input, candidate picker, the full scene-paper view, playback, and the mocked
free/paid gate UI.

## Worktree
`feature/web-ui` (`../scenepaper-ui`)

## Owns
- Topic input + candidate picker screen
- Scene paper detail view (full schema render: hooks, scenes, delivery notes,
  sources, cta)
- Playback UI + usage-limit indicator
- Mocked usage-gate UI (free-count display, "Unlock" states)

## Never touches
- Any backend/API logic — this agent renders whatever JSON the Python API
  returns, it doesn't call Wikipedia/Gemini/Pexels/Voicebox itself
- The Rust mobile core — web stays plain JS against the direct JSON response,
  no shared core involved

## Follows these decisions (don't re-litigate)
- No WYSIWYG editor or UI complexity beyond what's needed to demo the pipeline
  live — resist the urge to build more than the demo needs.
- Free/paid gates are **mocked, honestly labeled** ("Simulated for demo" or
  similar) — no real payment gateway, no fake-real checkout flow.
- This is what the panel sees first — the visual/demo-polish pass matters more
  here than almost anywhere else in the build.

## Default mode
Mostly AFK (topic input, candidate picker, paper view, playback, usage-gate
logic are all machine-checkable against the schema). The visual/demo-polish
pass is explicitly HIL — "does this look finished" is a judgment call, not
something to run unattended.

## Tracked issues
#11 (Phase 4 — Product Layer)

## Depends on
Phase 1 (#8) and Phase 2 (#9) existing enough to have a real API contract to
build against — check with `catalyst-agent` / `api-integration-agent` on
response shape before hardcoding assumptions about it.
