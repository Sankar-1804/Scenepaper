# ui-agent — Plan (written 2026-08-07)

Written as part of a full plan-file pass across all 4 active agents before
simultaneous deployment. Read `CLAUDE.md`'s Agent Loop Strategy first.

## Real current state (as of commit `05231f5`, just made this session)

- **Screen 1 (topic input) was rebuilt with a new dark visual system**:
  new theme (`src/web/css/styles.css`), splash-to-hero SVG logo handoff
  (`src/web/js/splash.js`, `src/web/public/scenepaper-splash.svg`),
  auto-growing textarea, example-topic chips, localStorage-backed recent
  searches. Internally consistent, `node --check` clean on all 3 JS files,
  no dangling DOM refs.
- **This was a deliberate staged redesign, and it deleted working
  functionality on the way in.** Before this commit (`05231f5~1`, i.e. the
  merged PR #22 baseline), `mockApi.js` had `searchStoryIdeas()`,
  `generateScenePaper()`, `getUsageStatus()`, `setExportUnlocked()` and
  `app.js` rendered a full candidate picker (Screen 2) and full ScenePaper
  detail view (Screen 3) — hooks[], scenes[] with pacing badges,
  sources[] including a suppressed-source example with its
  `suppression_reason`, a disabled/honest playback stub, and the mocked
  usage counter + export lock/unlock toggle. All of that is gone from the
  working tree right now; submitting a topic on Screen 1 just shows a stub
  message ("handing off to the generation screen ... not built yet").
- **User's explicit decision (2026-08-07): continue the rebuild-from-
  scratch approach and restore Screens 2/3 after**, accepting the
  temporary regression rather than retrofitting the new theme onto the old
  screens. Committed and pushed as-is this session
  (`feature/web-ui`, `05231f5`).
- `getUsageStatus` still exists in the current `mockApi.js` but nothing in
  `app.js` calls it yet — reserved, per its own comment, for a future
  Settings screen. Leave as-is, don't wire it prematurely.

## Work item 1 — Rebuild Screen 2 (candidate picker) in the new theme

Tag: **afk** — spec is fully defined (CLAUDE.md entity schema + the prior
working implementation as direct reference), success is visually/
functionally checkable against that reference, doesn't touch another
agent's files.

Reference implementation to port forward (do not copy verbatim — reimplement
in the new dark visual language): `git show 05231f5~1:src/web/js/mockApi.js`
for `searchStoryIdeas(topic)` and `git show 05231f5~1:src/web/js/app.js` for
how the candidate picker was rendered (confidence_score/tag/flags display,
suppressed-source framing).

Steps:
1. Re-add `searchStoryIdeas(topic)` to `mockApi.js` (mock data path only —
   `USE_MOCK_DATA` stays `true`, real `fetch()` calls stay commented out
   per the existing convention in this file, since there's no live backend
   endpoint yet).
2. Build the candidate-picker screen in the new dark theme/component style
   established by Screen 1 (reuse the chip/card visual language already
   built for example-topic chips where it fits).
3. Wire Screen 1's topic submit to actually transition to this screen
   instead of the current stub status message.
4. Verify headlessly (the `run` skill's prior approach — scratch Playwright
   install — worked well last session for this) before calling it done.

## Work item 2 — Rebuild Screen 3 (paper detail) in the new theme

Tag: **afk**, same reasoning as item 1. Depends on item 1 (candidate
picker needs to hand off to this screen).

Reference: `git show 05231f5~1:src/web/js/mockApi.js` for
`generateScenePaper(candidate)` / `getUsageStatus()`, and `app.js` for the
full-schema render — this is the important one to get right, since it's
"what makes the demo look finished" per CLAUDE.md. Must render:
- `hooks[]` (now `{text, verified}` span arrays per the session-2 schema
  addendum — check with api-integration-agent's plan.md / CLAUDE.md before
  assuming plain strings)
- `scenes[]` with pacing-tag badges and the real per-line `script[]`
  (`{speaker, line, direction}`, `line` also span arrays)
- `sources[]`, including at least one suppressed-source example rendered
  with its `suppression_reason` (this is a real demo moment per the trust
  model, don't drop it)
- disabled/honest playback stub
- mocked usage counter + export lock/unlock toggle (`setExportUnlocked`)

## Work item 3 — Visual polish pass (deferred, HIL)

Explicitly a judgment call per `agents/ui-agent.md` ("does this look
finished") — not for a fresh session to self-judge. Do items 1/2 first,
then have the user look at the full flow before spending more time on
visual refinement.

## Order for a fresh session executing this file

1. Work item 1, then item 2 (item 2 depends on item 1's hand-off existing).
2. Checkpoint with the user (screenshot or headless-run confirmation) before
   considering issue #11 demo-ready again.
3. Work item 3 only after the user has actually looked at 1+2 restored.
