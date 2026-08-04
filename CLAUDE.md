# ScenePaper — Project Context

This file is the shared source of truth for every Claude Code session working on this
repo, across every worktree. Read this fully before doing any work.

**This file supplements, not replaces, your global `~/.claude/CLAUDE.md`.** Global
conventions (tooling defaults, personal workflow preferences, handoff protocol, review
checkpoint discipline) still apply here unless something below explicitly overrides
them for this project. If the two ever conflict, project rules in this file win for
work inside this repo; everything else defers to global.

## What this is

**ScenePaper** is a tool for short-form content creators (YouTube Shorts, Instagram
Reels) that takes them from zero to recording-ready fast. Instead of 3–5 hours of
research and structuring per video, the creator submits a topic, gets a real,
source-verified story pre-structured into a "scene paper" — hook, pacing marks, breath
points, delivery notes — plus a generated voiceover and supporting images.

**This is being built for two purposes simultaneously:**
1. A 4-day internal Zoho AI hackathon submission (checklist-graded, see constraints below)
2. A real product — this is not throwaway hackathon code, treat it like the start of an
   actual MVP

**The actual differentiator — protect this:** the moat is the curated, *verified* story
library and the fixed scene-paper output format, not the AI generation step itself. The
moment this becomes "paste a prompt, get a script," it's commoditized like every other
AI writing tool. Every structuring step must be gated by real source verification, and
the output must always conform to the scene-paper schema, not free-form text.

## Hackathon constraints (hard rules — do not violate)

- 4 days total. Checklist-graded against 8 required outputs — not just app quality.
- Backend: Zoho Catalyst preferred (DataStore, Advanced I/O Functions, File Store,
  Auth). If any Catalyst service is skipped, document why in `docs/catalyst-notes.md`.
- Language: Python (Catalyst supports Python up to 3.9 for Advanced I/O Functions —
  verify any library against this before adding it).
- Scope: ONE primary entity (`ScenePaper`), full CRUD, demoable live. No secondary
  entities until this is airtight.
- Repo layout is fixed and non-negotiable: `README.md, ai-docs/, docs/, agents/, src/`
- Never commit secrets/API keys. Confirm `.gitignore` covers `.env` before first commit.
- Every external API call documented in `docs/api-notes.md` (endpoint, purpose, auth).
- Custom agent(s) live in `agents/` with a clearly stated role, not a raw prompt dump.
- MCP connection must be used during actual development AND the product itself ships
  its own MCP server — this is the hackathon differentiator, do not treat it as optional.
- AI tooling: Claude (Enterprise) is primary. GitHub Copilot for inline autocomplete.
  Sahaa deliberately for small/low-risk tasks only. Log usage after every session to
  `ai-docs/token-log.md` — this is a required deliverable, not optional bookkeeping.
- Day 1 exit bar: idea locked (done), CRUD working, 1 agent + 1 MCP used, pushed to remote.
- Day 3 rule: I drive every change myself with agent/Sahaa/Claude as tools. Checkpoint
  before applying any panel feedback — no unreviewed auto-apply.
- Two 10-minute talks are real deliverables: Day 2 pitch, Day 4 retro. Draft scripts
  early, don't write them cold.

## Product flow (the real shape, not just CRUD)

1. User has a lightweight `UserProfile` (about_me / niche description) that informs
   ideation — not full multi-user auth for the hackathon, effectively single-user.
2. User submits a topic. The ideation step searches for **verified candidate stories**
   (Wikipedia / a structured news API — same verification bar as the main pipeline,
   do not loosen this at the ideation stage) and returns 3–4 one-liner options.
   Candidates are ephemeral — do not persist them as their own CRUD entity, this stays
   within the "one primary entity" rule. `ScenePaper` remains the only DataStore table.
3. User picks one candidate. Only then does the full structuring pipeline run and a
   `ScenePaper` row gets created.
4. Free/paid gate: **first 10 `ScenePaper` generations (text) are free, total, then
   each further paper is paid.** Audio/video export is a **separate gate, always paid**,
   even for papers generated within the free 10.
5. Hackathon demo: **no real payment gateway.** Mock both gates — real counters, real
   "Unlock" UI states, no actual charge, no Razorpay/Stripe integration. Label mocked
   actions honestly in the UI rather than faking a real checkout flow.

## Entity schema

```
ScenePaper
  id
  paper_number             # "041"
  title
  category                 # enum: suspense / cautionary / human_interest / curious
  dek                       # 1-2 sentence summary
  verification_status
  runtime_estimate          # "57-63s"
  hook_window               # "0-3s"
  peak_tension_window       # "18-30s"
  payoff_window             # "48-55s"
  hooks[]                   # [{label, type, text, best_for_note}]
  scenes[]                  # [{scene_number, title, description, pacing_tag, time_range}]
  delivery_notes[]          # [{label, note}] -- tied to scene numbers or "CTA"
  cta_text
  sources[]                 # [{title, type, date, verified}]
  voiceover_url
  image_set[]               # [{segment_id, image_url, credit_source}]
  video_url                 # slideshow export, only present once unlocked
  media_status               # pending / generating / ready
  export_status               # locked / unlocked (mocked toggle, no real payment)
  created_at

UserProfile                 # lightweight, effectively single-user for the demo
  id
  about_me                  # niche/channel description, feeds ideation personalization
  scenepapers_generated_count
  free_limit                 # = 10, hardcoded constant for hackathon
```

`pacing_tag` values: `FAST` / `BUILD` / `SLOW` / `WARM` — matches the validated mock
format. All nested fields (`hooks`, `scenes`, `delivery_notes`, `sources`, `image_set`)
store as JSON within the single `ScenePaper` row in Catalyst DataStore — this keeps
the design compliant with the hackathon's "one primary entity" rule while still
carrying the full product-grade structure.

## Feature tiers (do not build out of order)

**Tier 1 — Core, must work Day 1–2 (this is what gets demoed live):**
- Topic → 3–4 verified candidate stories (one-liners) → user picks one
- Structuring call: verified source → full rich schema (hooks[], scenes[] with pacing
  tags, delivery_notes[], sources[], cta_text) — get this exactly right first, it's
  what makes the demo look finished even before any audio plays
- Voiceover generation (TTS) — a single consistent voice reading `story_body`, with
  pauses inserted at breath points. Per-scene pacing-tag-aware delivery (speeding up
  on FAST, slowing on SLOW) is a refinement, not a Day-1 requirement — get a working
  voiceover first, tune its pacing-awareness after, don't let tuning block progress.
- Supporting images: real stock photos (Pexels or Unsplash API) matched per scene
  keyword — NOT AI-generated images, too unreliable for a live demo on this timeline
- Full CRUD on ScenePaper including its media
- Mocked free/paid gates (10-free counter, always-paid export toggle) — no real
  payment gateway
- MCP server exposing the pipeline as tool calls

**Tier 2 — Stretch, Day 3 only, only if Tier 1 is bulletproof:**
- Video export as a **synced slideshow** (not a full editor): scene images shown in
  sequence, timed against that scene's portion of the audio, simple crossfade between
  them. Build with `moviepy` once audio + images from Tier 1 already exist — this is
  assembly on top of proven pieces, not a new pipeline.
- Per-scene pacing-tag-aware voiceover delivery (the refinement noted above)
- Multiple voice options matched to category tone (Voicebox personality profiles:
  `narrator_suspense`, `narrator_cautionary`, `narrator_warm` — see docs/voice-notes.md)
- Mobile (SwiftUI) client hitting the same media endpoints

**Tier 3 — Explicitly out of scope for the hackathon, product roadmap only:**
- AI-generated custom imagery
- Auto-captioning / burned-in subtitles
- Real payment integration (Razorpay/Stripe), real multi-user accounts/auth
- Full non-linear video editing beyond the synced slideshow

If unsure whether to build something, check which tier it's in. Never pull Tier 3 work
into hackathon time.

## MCP tools to expose

- `search_story_ideas(topic)` — returns 3–4 verified candidate one-liners
- `get_scene_paper(topic)` — retrieve a full paper including media URLs
- `verify_source(paper_id)` — returns source URL + verification status
- `generate_scene_paper(source_url)` — triggers the full structuring pipeline
- `generate_voiceover(paper_id)` — regenerate audio independently
- `list_available_stories(category)` — browse without the UI
- `get_usage_status(user_id)` — returns free-tier count remaining + export lock state

## Catalyst service mapping

- **DataStore** — the `ScenePaper` table
- **Advanced I/O Function (Python)** — orchestrates: topic in → Wikipedia fetch →
  verify → LLM structuring call → TTS call → image fetch → write to DataStore → return
- **File Store** — serves generated audio/image files; confirm this works cleanly
  before relying on it mid-demo
- **Auth** — explicitly out of scope for hackathon unless time allows; note as
  "not implemented, out of scope" rather than leaving it silently missing

## Agents (in `agents/`)

| Agent | Role |
|---|---|
| `catalyst-agent` | DataStore schema (ScenePaper + UserProfile) + Advanced I/O Function skeleton |
| `api-integration-agent` | Ideation search, Wikipedia/source verification, structuring call, TTS call, image API, secrets handling |
| `ui-agent` | Web client — topic input, candidate picker, paper view, playback, mocked paywall UI |
| `video-agent` | Tier 2 only — moviepy slideshow assembly, scene-timed crossfades |
| `feedback-agent` | Day 3 only — turns panel feedback into a checkpointed backlog |
| `docs-agent` | Keeps README, ai-docs/, token-log, api-notes, voice-notes in sync every session |

## Skills to build (none exist in-org yet — creating these is itself a scored deliverable)

- `catalyst-crud-scaffold` — reusable DataStore + Function boilerplate pattern
- `token-usage-logger` — appends usage estimate to `ai-docs/token-log.md` per session
- `demo-script-builder` — drafts/updates Day 2 and Day 4 talk outlines from git log + ai-docs

## Working conventions in this repo

- This project uses `git worktree` — see `docs/github-workflow.md` for the full setup.
  Each active worktree corresponds to one agent's scope. Do not do cross-cutting work
  in a worktree scoped to a single agent; open an issue and switch worktrees instead.
- Every unit of work should trace to a GitHub Issue. Reference the issue number in
  commit messages (`#12`).
- Before ending a session: update `ai-docs/token-log.md`, confirm the relevant
  `docs/*.md` file reflects what changed, and leave a short handoff note in the
  issue if work isn't finished.

## Context-limit handoff

When context in a session is running low (approaching the point where quality would
degrade, not right at the hard limit), stop new feature work and do the following
in order:

1. Invoke the handoff skill to produce a structured handoff note — current state,
   what's done, what's next, any blockers or decisions pending.
2. Write that note into the relevant open Issue as a comment (not just locally),
   so the next session — yours or another agent's — has it without you re-explaining.
3. Commit any in-progress work on the current worktree branch, even if incomplete,
   with a clear WIP commit message referencing the issue.
4. Only then hand off: either resume yourself in a fresh session in the same
   worktree, or, if the remaining work belongs to a different agent's scope, note
   in the issue which agent/worktree should pick it up next.

Do not let a session run to the point of degraded output before handing off —
the handoff should happen proactively, not as a last resort once things are
already going wrong.

## What NOT to do

- Do not build a WYSIWYG resume/script editor or any UI complexity beyond what's
  needed to demo the pipeline live.
- Do not attempt AI-generated imagery — stock photo APIs only, for reliability.
- Do not let Tier 2/3 features start before Tier 1 is fully working and demo-safe.
- Do not skip source verification to save time — this is the actual product moat,
  cutting it defeats the point of the build.
