# ScenePaper — Project Walkthrough

Read this top to bottom whenever you feel like you've lost the thread. It's written
to answer "what are we actually doing, why, and in what order" — not a reference doc
you dip into, a narrative you read straight through once and then use `docs/task-breakdown.md`
+ the GitHub issues for the day-to-day mechanics.

---

## 1. What ScenePaper actually is, in one paragraph

A creator types a topic. The app finds 3-4 *real, verifiable* story candidates about
that topic (not made up), the creator picks one, and the app turns that one real story
into a fully-structured "scene paper" — a hook, scene-by-scene pacing, delivery notes,
a source list, a voiceover, and matching images. The creator walks away with something
recording-ready in minutes instead of 3-5 hours of manual research and structuring.

## 2. Why this and not just "an AI script generator"

Every competitor generates a script from a prompt — that's commoditized, anyone can
build it, and it isn't defensible. ScenePaper's whole bet is: **every story is pulled
from a real, checkable source, verified before it's structured, and always shaped into
the same fixed format.** That verification step is the actual product — not a nice-to-have,
the *point*. If a shortcut anywhere would skip verification to save time, that shortcut is
wrong, even under hackathon pressure.

The second bet: this ships its own **MCP server**, so the pipeline is usable as tool
calls by any AI agent, not just through a web page. That's the hackathon's actual
differentiator on the grading checklist — more so than how polished the UI looks.

## 3. The setting: a 4-day internal hackathon, checklist-graded

Zoho's internal AI hackathon, 4 days, graded against 8 required outputs (CRUD app,
AI-usage docs, models used, token usage, skills, a custom agent, IDE/AI tooling used,
app documentation) — not just "does the demo look good." That's why so much of this
session has been about documentation and issue tracking, not just code: **the
paperwork is a scored deliverable, not overhead.**

Day 1 = idea + full CRUD + one agent + one MCP connection + pushed to remote.
Day 2 = live 10-minute showcase.
Day 3 = apply panel feedback yourself (this explicitly wins over any stretch work).
Day 4 = 10-minute retro + final push.

## 4. The three tiers — and why the order is non-negotiable

- **Tier 1** — the stuff that has to work, live, on Day 2. Topic-to-candidates,
  structuring, voiceover, images, full CRUD, mocked free/paid gates, the MCP server.
- **Tier 2** — stretch, Day 3 only, and *only* if Tier 1 is bulletproof: video
  slideshow export, per-scene pacing-aware voice delivery, multiple voice profiles,
  and now the Rust mobile core for iOS/Android.
- **Tier 3** — explicitly not touched during the hackathon at all (AI-generated
  imagery, real payments, full video editing) — product-roadmap-only.

The reason this order is locked: every hour spent on Tier 2 before Tier 1 is
demo-safe is an hour of real risk on the thing that's actually graded. If Day 1 runs
long, Android drops first, then the video slideshow — the MCP server is the last
thing to ever get cut, because that's the actual differentiator.

## 5. What's already been decided (so it doesn't feel like it happened invisibly)

- **Runtime LLM: Google Gemini API** (`gemini-2.5-flash`). We ruled out Zoho's
  internal PlatformAI (it needs your product to already be a registered internal
  Zoho service with real onboarding — not feasible in 4 days) and compared Gemini
  against OpenRouter, Groq, Cerebras, Mistral, Together.ai, Fireworks, DeepInfra.
  Gemini won on two things that matter most here: it's genuinely free with zero
  card/billing risk, and its native `response_schema` feature is the strongest
  guarantee found anywhere that the model's output will actually match ScenePaper's
  strict JSON schema — which is the single biggest live-demo risk (a malformed
  structuring response, on stage, in front of the panel).
- **Images: Pexels** over Unsplash — simple auth, generous free limit, no strong
  reason to prefer the alternative.
- **Mobile: a shared Rust core** (via FFI, e.g. UniFFI) reused by iOS and Android,
  gated behind Tier 1 being fully done — this is new scope added mid-hackathon, and
  it only makes sense once Tier 1 isn't at risk anymore.
- **Web client** stays simple: renders the direct JSON from the Python API via JS,
  no Rust, no extra layer.
- Full detail and reasoning for all of this lives in `docs/api-notes.md`.

## 6. Everything still open, waiting on you specifically

- Your Gemini API key exists in `.env` but the file is still **empty** — you need to
  paste the real key in yourself (`GEMINI_API_KEY=...`).
- Three "spike" checks need you to log into the Zoho Catalyst console/CLI
  (`catalyst login`) and look at actual settings — I can't do these, they need your
  credentials:
  - Does Catalyst's DataStore actually support the column types the schema needs?
  - What's Catalyst's function execution timeout (the pipeline could run 60+ seconds)?
  - Can a Catalyst function even host MCP tool calls at all?
- Each agent's exact working style needs a final confirmation pass (issue #6), and
  the actual agent definition files need to be written into `agents/` (issue #7,
  currently just an empty placeholder folder).

## 7. How the work is tracked, in plain terms

No project board anymore — we tried that, it added confusion instead of removing it.
**Just flat GitHub issues.** Every issue has a label telling you which bucket it's in:

- `prerequisite` — has to happen before real coding starts
- `tier-1` / `tier-2` / `tier-3` — which tier the work belongs to

Work through them roughly in issue-number order within each label. Each issue's
description has a checklist inside it — you (or an agent) tick off the granular
items one at a time, then close the issue when it's done. That's the entire system:
open an issue, work the checklist, close it, move to the next one.

## 8. The phases themselves, in the order you'll actually hit them

### Prerequisites (before any real code)
- **#6 — Confirm each agent's working style.** Each of the 8 agents in `agents/`
  needs a settled scope: what it owns, what it must never touch, whether its default
  mode is AFK (runs unattended) or HIL (needs you watching). Getting this wrong means
  an agent quietly wandering into another agent's territory later.
- **#7 — Write the actual agent files.** Right now `agents/` is empty. This turns
  the roles into real files Claude Code sessions read before touching code.
- **#1, #2, #3 — The Catalyst spikes**, listed above. These aren't busywork — if
  the answer to any of them is bad news (e.g. Catalyst can't host MCP), it changes
  the architecture, so better to know on day one than discover it live.

### Phase 1 — Backend Foundation (`catalyst-agent`, issue #8)
The foundation everything else sits on: the DataStore table for `ScenePaper` and
`UserProfile`, and the skeleton of the Advanced I/O Function that will eventually
run the whole pipeline (routes for create/read/update/delete). Blocked on the
DataStore-column-types spike (#1) — don't build the schema on a guess.

### Phase 2 — Content Pipeline (`api-integration-agent`, issue #9)
This is the actual product moat. Two calls: **ideation** (topic → 3-4 real,
verified candidate stories) and **structuring** (one chosen story → the full rich
schema — hooks, scenes with pacing tags, delivery notes, sources, a call-to-action).
The structuring prompt specifically is flagged as the single highest-leverage piece
of creative work in the whole build — worth writing yourself first, not delegating
blind, because it's what makes the demo look finished before any audio even plays.

### Phase 3 — Voice & Media (`api-integration-agent`, issue #10)
Turning the structured text into something recordable: a voiceover (via Voicebox,
running locally on your Mac) with pauses at natural breath points, and real stock
photos (Pexels) matched per scene. Get a working voiceover first — don't let
pacing-aware tuning (that's Tier 2) block getting *a* voiceover out at all.

### Phase 4 — Product Layer / Web UI (`ui-agent`, issue #11)
The actual web app: topic input, the candidate picker, the full scene-paper view,
playback, and the mocked free/paid gate UI. This is what the panel sees first, so
the "visual/demo-polish" pass on this one is explicitly HIL — it's a judgment call,
not something to run unattended.

### Phase 5 — MCP Layer (`mcp-agent`, issue #12)
Wrapping everything above as MCP tool calls — this is the actual hackathon
differentiator. It deliberately depends on Phases 1-4 already existing, since each
tool call is just a thin wrapper around a function that already works. Don't start
this before the rest is real.

### Phase 6 — Integration & Demo Readiness (issue #13)
Entirely hands-on, no exceptions: merging every worktree's work together in the
right order, running the whole pipeline live yourself end to end, and rehearsing
the actual demo script. This is where two agents' work silently not fitting
together would otherwise hide until the worst possible moment.

### Tier 2 — only once Tier 1 is solid
- **#5 — Rust mobile core**, shared between iOS and Android via FFI.
- **#14 — Video slideshow export**, assembled with `moviepy` from the audio +
  images that already exist by this point — not a new pipeline, just packaging.
- **#15 — Pacing-aware voice + multiple voice profiles** — the refinement layer on
  top of the Phase 3 voiceover.

### Tier 3 — issue #16, a placeholder only
Nothing gets built here during the hackathon. It exists purely so the list of
"things we deliberately said no to" doesn't get silently forgotten.

## 9. What "done" looks like for the hackathon

A live demo where: you type a topic, get real verified candidates, pick one, watch
it turn into a full scene paper with a voiceover and images, see the mocked
free/paid gates work honestly, and show the same pipeline being called through MCP
tools instead of the UI. Everything else (mobile, video export, voice tuning) is
genuinely optional polish on top of that.

## 10. Where to go after reading this

Come back to this conversation and we'll pick up right where we left off: drafting
the 8 agent definition files to close out issues #6 and #7. Everything above should
already match what you remember deciding — if anything here reads like a surprise,
that's the thing to flag before we go further, not something to quietly work around.
