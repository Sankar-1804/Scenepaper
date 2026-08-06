# Session Handoff — ScenePaper Hackathon Project

This is a full handoff from a planning conversation (Claude web/mobile chat) to a new
Claude Code CLI session. Read this completely before doing anything. It captures every
decision made, why it was made, what's confirmed vs. unconfirmed, and what to check
first. Do not re-litigate settled decisions without a real reason — but do flag
anything below marked UNCONFIRMED before building on top of it.

If `CLAUDE.md` already exists in this repo, read that too — it's the condensed,
canonical version of most of what's below, and is confirmed up to date as of this
handoff (see section 12). This document has more history and reasoning; `CLAUDE.md`
has the operating rules. Where they conflict, `CLAUDE.md` wins.

---

## 0. BLOCKERS AND RISKS — READ THIS FIRST

These were surfaced in a final review pass at the very end of the planning session,
after everything else below was already written. Several of them could invalidate
parts of the architecture described later in this document. **Work through these
before writing real pipeline code** — do not treat sections 1–14 as safe to build on
until these are resolved.

### 0.1 — BLOCKER: no LLM API key for the product's own runtime calls

The structuring call (and the ideation call) are the *application* making programmatic
LLM API calls at runtime. This is **completely separate** from the user's Claude Code
Enterprise access, which is a development tool, not a runtime API credential. Nothing
in the planning session confirmed the user has an API key for this.

This also brushes against the hackathon's "do not buy extra paid-plan tokens this
month" rule. Options to explore, in rough order of fit:
- Sahaa's API, if it exposes one — would neatly satisfy the guide's "Sahaa preferred"
  guidance and sidestep the token-purchase rule entirely
- Whether the Enterprise plan includes API credits usable for this
- A free-tier LLM API from another provider (note the model honestly in
  `ai-docs/token-log.md` if so)

**The entire pipeline is blocked on this.** Resolve it before Day 1 build starts, not
during.

### 0.2 — SPIKE: Catalyst function execution timeout vs. the chained pipeline

The Advanced I/O Function as designed does Wikipedia fetch → verify → LLM structuring
→ TTS → image fetch → DataStore write, all inside one request. That could plausibly
run 60+ seconds. Serverless platforms impose execution time limits and **Catalyst's
was never verified**.

If it times out, the fix is an async job pattern — return a job ID immediately, poll
for status, do the work in the background. That's a **meaningfully different
architecture**, not a small patch, and it would ripple into the web/iOS clients and
the MCP tool contracts. **Check Catalyst's function timeout limit on Day 1, before
building the chained version.**

### 0.3 — SPIKE: can a Catalyst function host MCP tool calls at all?

Already covered in section 6, restated here because it's one of the two highest-risk
unknowns. MCP servers typically expect a persistent process (stdio) or a proper
HTTP/SSE endpoint; nothing confirmed a serverless Catalyst function can serve MCP
correctly. Run a minimal "hello world" MCP tool call through a bare Catalyst function
before building real pipeline logic on top of it. Fallback (if it fails) is not yet
decided — likely hosting the MCP layer as a thin separate process.

### 0.4 — SPIKE: Catalyst DataStore column types

Also already in section 4, restated for priority. Nested fields were originally
assumed to store as native JSON; that's probably wrong. Verify actual available
column types in the Catalyst console before writing the DataStore setup script.

### 0.5 — Day 3 is double-booked, and feedback wins

The hackathon explicitly grades Day 3 as "apply panel feedback yourself." But the
plan below also puts iOS client, video slideshow, and voice tuning as Day 3 stretch
work. These compete directly for the same hours.

**Decision: panel feedback application wins every time.** Tier 2 stretch work is
genuinely optional and yields immediately if feedback is substantial. The Tier 2 list
in section 5 should be read as "if there's slack," not "expected."

### 0.6 — The source strategy doesn't match the target output format

The validated sample scene paper cites **three verified primary sources** (Forbes
interview, SEC S-1 filing, WSJ report). Wikipedia alone will not produce that. If the
demo generates a paper showing one Wikipedia link where the reference format shows
three primary sources, **the output will look visibly thinner than the format being
pitched** — a gap a panel would notice immediately.

Either add a second source type (a news API alongside Wikipedia), or accept the gap
and state it explicitly during the demo as a known limitation. Do not discover this
mismatch live on stage.

### 0.7 — moviepy is likely a dead end on serverless

Video rendering is CPU/memory heavy with long runtimes — the worst possible fit for
serverless. If Tier 2's slideshow gets attempted, **plan to run it locally** (same as
Voicebox), not inside a Catalyst function. Also verify moviepy actually works on
Python 3.9, since that's Catalyst's cap.

### 0.8 — Branch protection can lock the user out of their own AFK workflow

If "require approvals" is enabled on `main`, GitHub may block the user from approving
their own PRs — which would break the entire overnight-PR-review loop that AFK mode
depends on. **Enable "require a pull request before merging" but NOT "require
approvals."** The user is solo on this repo.

### 0.9 — AFK has far less runway than it sounds

Across a 4-day event there are realistically **two** overnight windows: the night of
Day 1 (immediately before the Day 2 showcase) and the night of Day 3. Do not plan as
if AFK is a nightly multiplier. The Day 1 night in particular needs careful scoping —
whatever is half-finished at 9am on Day 2 is going into the showcase as-is.

---

## 1. The hackathon itself

Internal Zoho AI hackathon, 4 days, checklist-graded against 8 required outputs, not
just app quality:
1. CRUD app — full C/R/U/D on one primary entity, demoed live
2. AI markdowns — `ai-docs/` (this file belongs here)
3. Models used and for which tasks
4. Approximate token usage / quota pressure
5. Skills used or created
6. Custom agent name, role, location in repo
7. IDE used, which AI features relied on
8. App documentation — setup, API/Catalyst notes, demo steps

Fixed repo layout (non-negotiable): `README.md, ai-docs/, docs/, agents/, src/`

Day-by-day: Day 1 = idea + full CRUD + API + agent + MCP + git push, exit bar is a
demoable path by evening. Day 2 = 10-min live showcase (problem, live CRUD demo,
AI usage, ask for feedback). Day 3 = apply panel feedback yourself — organizers
explicitly will not build it for you; agents are tools you drive, not autopilot.
Day 4 = 10-min retro (what changed, mistakes, one token/model honesty note, one
recommendation), final push.

Secrets must never be committed. Catalyst is "preferred" for backend — if any Catalyst
service gets skipped, document why rather than silently dropping it.

**AI tooling decision:** Sahaa was suggested by the guide to protect shared token
pools, but it's not mandatory. Using **Claude (Enterprise)** as primary — ~50% of a
$1000/3-month budget still available — for agent design, Catalyst scaffolding, core
logic, and review. **GitHub Copilot** for inline autocomplete. **Sahaa** deliberately
for small/low-risk tasks only. Log usage honestly in `ai-docs/token-log.md` — the
Day 4 talk should include this exact reasoning as the "honest token/model note."

---

## 2. The product: ScenePaper

A tool for short-form content creators (YouTube Shorts, Instagram Reels) that replaces
hours of story research and structuring with a real, source-verified story,
pre-structured into a "scene paper" — hooks, scene-by-scene pacing, delivery notes,
and a full source list — plus a generated voiceover and matched images.

**This is not just a hackathon entry.** It's the start of a real product the user is
already committed to building on weekends, separate from any job-switch plans. Treat
hackathon hours as genuine product progress, not throwaway demo code.

**The actual differentiator, protect this:** every competitor in this space (VEED,
GravityWrite, Videotok, QuillBot-style tools) generates a script from a prompt.
ScenePaper doesn't — every story is pulled from a real, checkable source and gated by
verification *before* it's structured. The moat is the curated, verified pipeline and
the fixed output format, not the generation step. If this ever becomes "paste a
prompt, get a script," it's commoditized and has lost its point.

The user showed two screenshots of a rich, fully-designed scene paper mock (story:
"The Man Who Turned Down $3 Billion from Zuckerberg," business-failure category,
footer branded "scenepaper.io"). **UNCONFIRMED:** I assumed this was the user's own
Phase-0 validation mockup (matches their original plan to "build a mock scene paper in
Notion or Figma" before writing code) and said so — the user never explicitly
confirmed or denied this. Worth a quick clarifying check with the user if it matters
later (e.g. if attribution or a live scenepaper.io site ever becomes relevant), but
the format itself was adopted as the real target schema regardless of its origin.

---

## 3. Product flow (the real shape)

1. User has a lightweight `UserProfile` (`about_me` — a niche/channel description)
   that personalizes ideation. Not full multi-user auth for the hackathon — treat as
   effectively single-user (the builder testing their own product).
2. User submits a topic. Ideation searches for **verified candidate stories** — same
   verification bar as the main pipeline, Wikipedia/a structured news API, NOT open
   web search (open web is harder to verify and would weaken the core moat) — and
   returns 3–4 one-liner options.
3. Candidates are **ephemeral** — do not persist them as their own DataStore entity.
   `ScenePaper` remains the only primary table, keeping this compliant with the
   hackathon's "one primary entity" rule.
4. User picks one candidate. Only then does the full structuring pipeline run and a
   `ScenePaper` row gets created.
5. **Free/paid gate (confirmed, exact wording matters):** first 10 `ScenePaper`
   generations (text) are free, **total**, then each further paper is paid.
   Audio/video **export is a separate gate, always paid**, even for papers generated
   within the free 10.
6. **Hackathon demo: no real payment gateway.** Both gates are mocked — real counters,
   real "Unlock" UI states, no actual charge, no Razorpay/Stripe integration. Label
   mocked actions honestly in the UI (e.g. "Simulated for demo") rather than faking a
   real checkout flow — a panel respects an honest mock more than a fake-real one.
7. **README.md language note:** the public-facing README was deliberately rewritten to
   describe #5 and #6 in neutral technical terms ("usage is tracked... gated by a
   lightweight access-limit system") rather than explicit "free/paid" business-model
   language, and any pricing hypothesis / target-market / monetization framing from
   the original product brief was stripped from README on purpose. `CLAUDE.md` still
   carries the full explicit detail since it's an internal working doc, not
   public-facing — that split was intentional, don't collapse it back together.

---

## 4. Entity schema (final, as of last update)

```
ScenePaper
  id
  paper_number             # e.g. "041"
  title
  category                 # enum: suspense / cautionary / human_interest / curious
  dek                       # 1-2 sentence summary
  verification_status
  runtime_estimate          # e.g. "57-63s"
  hook_window                # e.g. "0-3s"
  peak_tension_window        # e.g. "18-30s"
  payoff_window               # e.g. "48-55s"
  hooks[]                     # [{label, type, text, best_for_note}]
  scenes[]                    # [{scene_number, title, description, pacing_tag, time_range}]
  delivery_notes[]            # [{label, note}] -- tied to scene numbers or "CTA"
  cta_text
  sources[]                    # [{title, type, date, verified}]
  voiceover_url
  image_set[]                  # [{segment_id, image_url, credit_source}]
  video_url                     # slideshow export, only present once unlocked
  media_status                   # pending / generating / ready
  export_status                   # locked / unlocked (mocked toggle, no real payment)
  created_at

UserProfile                     # lightweight, effectively single-user for the demo
  id
  about_me                       # niche/channel description, feeds ideation
  scenepapers_generated_count
  free_limit                      # = 10, hardcoded constant for hackathon
```

`pacing_tag` values: `FAST` / `BUILD` / `SLOW` / `WARM`.

**CORRECTION MADE LATE IN PLANNING — important, don't miss this:** nested fields
(`hooks`, `scenes`, `delivery_notes`, `sources`, `image_set`) were originally described
as storing "natively as JSON" in Catalyst DataStore. That was **not verified** and is
probably wrong — Catalyst's own docs describe columns with defined types, created from
the console, with row inserts passing column-name/value pairs; there's no confirmed
native JSON/object column type the way Postgres has `jsonb`. **The safer assumption:
store each nested field as a JSON-serialized string in a Text/Multi-line-text column**,
serialize on write and `json.loads()` on read in the Python function. **This must be
verified against the actual Catalyst console before writing the DataStore setup
script** — check what column types are genuinely available first.

---

## 5. Feature tiers — build strictly in this order, do not skip ahead

**Tier 1 — Core, must work Day 1–2, this is what gets demoed live:**
- Topic → 3–4 verified candidate one-liners → user picks
- Structuring call: verified source → full rich schema (hooks[], scenes[] with pacing
  tags, delivery_notes[], sources[], cta_text) — **get this exactly right first**, it's
  what makes the demo look finished even before any audio plays. This structuring
  prompt is the single highest-leverage piece of creative work in the whole build —
  write the first version yourself (HIL), don't delegate blind.
- Voiceover: a single consistent voice reading `story_body`-equivalent content, with
  pauses inserted at breath points. **Per-scene pacing-tag-aware delivery (speeding up
  on FAST, slowing on SLOW, exact 1.5–2s pauses per delivery_notes) is a Tier 2
  refinement, not a Day 1 requirement.** Get a working voiceover first; tune its
  pacing-awareness after. Do not let perfectionism on this block Day 1 progress —
  but do NOT drop voiceover entirely either, it's core to the product, not optional.
- Images: real stock photos (Pexels or Unsplash — **exact choice between the two was
  never finalized**, pick one and note it in `docs/api-notes.md`) matched per scene
  keyword. Explicitly NOT AI-generated images — too unreliable for a live demo on
  this timeline, and generated images fit the "verified/sourced" philosophy worse
  than real photos anyway.
- Full CRUD on `ScenePaper` including its media fields
- Mocked free/paid gates (10-free counter, always-paid export toggle) — no real
  payment gateway, see section 3
- MCP server exposing the pipeline as tool calls (see section 6)

**Tier 2 — Stretch, Day 3 only, only if Tier 1 is fully working and demo-safe:**
- **Video export as a synced slideshow** (user's own framing: "like a paper clip") —
  NOT a full video editor. Scene images shown in sequence, timed against that scene's
  portion of the audio, simple crossfade between them. Build with `moviepy` once
  Tier 1's audio + images already exist — this is assembly on top of proven pieces,
  not a new pipeline.
- Per-scene pacing-tag-aware voiceover delivery (the refinement noted above)
- Multiple Voicebox voice/personality profiles matched to category tone (see section 7)
- Mobile (SwiftUI) client hitting the same media endpoints — **iOS is a committed
  platform for this build, not optional.** Sequenced for Day 3 (after Tier 1 is solid
  and the API contract is frozen), and may run in parallel with other Day 3 work if
  there's capacity. The user is an iOS developer by trade, so this is genuinely
  low-risk for them specifically once the API contract is stable. **Android is the
  actual stretch** — only attempted if there's real slack after everything else, and
  drops first of all if time runs short.

**Tier 3 — Explicitly out of scope for the hackathon, product roadmap only. Never pull
these into hackathon time even if there's slack:**
- AI-generated custom imagery
- Auto-captioning / burned-in subtitles
- Real payment integration (Razorpay/Stripe), real multi-user accounts/auth
- Full non-linear video editing beyond the synced slideshow

**Cut-line if Day 1 runs long:** Android drops first, then the video slideshow, before
the MCP wrapper ever does. A missing Android client reads as good prioritization in
the Day 4 talk; a missing MCP-as-product is the actual differentiator lost. iOS is
committed rather than droppable, but if Day 3 feedback is heavy, it yields to feedback
work per section 0.5.

---

## 6. MCP tools to expose (this is the hackathon's real differentiator)

- `search_story_ideas(topic)` — returns 3–4 verified candidate one-liners
- `get_scene_paper(topic)` — retrieve a full paper including media URLs
- `verify_source(paper_id)` — returns source URL + verification status
- `generate_scene_paper(source_url)` — triggers the full structuring pipeline
- `generate_voiceover(paper_id)` — regenerate audio independently
- `list_available_stories(category)` — browse without the UI
- `get_usage_status(user_id)` — returns free-tier count remaining + export lock state

**UNVERIFIED, HIGH PRIORITY TO CHECK FIRST — this is the single biggest architectural
risk in the whole plan:** whether a Zoho Catalyst Advanced I/O Function (serverless)
can actually host/serve MCP tool calls at all. MCP servers typically expect either a
persistent process (stdio transport) or a proper HTTP/SSE endpoint. Nothing in this
planning session confirmed Catalyst functions can serve MCP-over-HTTP correctly. **Do
a minimal spike — one "hello world" MCP tool call through a bare Catalyst function —
before writing any real pipeline logic on top of this assumption.** If it doesn't
work cleanly, the fallback (not yet decided) would need to be figured out — possibly
hosting the MCP layer as a thin separate process rather than inside the Catalyst
function itself.

During development, the user's Claude Code sessions can also call **Voicebox's own
built-in MCP server** directly (see section 7) — that's a legitimate second MCP
connection used during dev, on top of the one the product itself ships. Worth a line
in `docs/mcp-notes.md`.

---

## 7. Voice / TTS — Voicebox setup

Using **Voicebox** (voicebox.sh) — a local, open-source voice studio app, downloaded
for macOS Apple Silicon. Runs entirely on the user's Mac (MLX/Metal-accelerated),
nothing goes to the cloud. Has 7 TTS engines (Qwen3-TTS, Qwen CustomVoice, LuxTTS,
Chatterbox Multilingual, Chatterbox Turbo, HumeAI TADA, Kokoro), zero-shot voice
cloning or 50+ preset voices, 23 languages, paralinguistic tags (`[pause]`, `[sigh]`,
`[laugh]`) for expressive delivery, post-processing effects, a REST + WebSocket API,
and its own MCP server.

**Architecture wrinkle:** Voicebox runs locally; the pipeline is meant to be
orchestrated by a cloud Catalyst function. A cloud function can't reach `localhost`
directly. Two paths: (1) Voicebox's "Remote Mode" + a Cloudflare Tunnel exposing the
local backend (the user has done this exact pattern before for their Fynlo home-server
setup, so no new learning curve) — documented as the real intended architecture but
**not attempted for the live demo**, and (2) for the actual Day 2 demo, **run the
whole pipeline locally and call Voicebox directly from the machine** — lower risk,
one less network hop to fail live. Mention the tunnel-based cloud integration as the
"next step" in the Day 4 talk. **Decision: option 2 for the demo, option 1 documented
as intent.** Voicebox's local API has no built-in authentication — must stay behind a
tunnel/VPN if ever exposed, never the open internet.

**Setup already walked through with the user:**
- Download from voicebox.sh, install to Applications, bypass Gatekeeper via right-click
  → Open on first launch
- Pick **one** TTS engine to start, not all 7 — Kokoro for fast iteration (lightweight,
  English-first), or Chatterbox Multilingual / Qwen3-TTS for higher-quality demo audio
- **Skip voice cloning entirely** for the hackathon — needs sample audio and setup time
  not available; use a preset voice instead
- Test the local REST API with curl before wiring anything into Python
- Write a standalone ~10-line Python script that POSTs text to the local endpoint and
  saves the returned audio, and get that working **before** touching Catalyst at all

**Voice profile screen reviewed (screenshot):** Under the Qwen CustomVoice engine,
preset voices are mostly tagged for other languages — Vivian/Serena/Uncle Fu/Dylan/Eric
are `zh`, Ono Anna is `ja`, Sohee is `ko`. **Only Ryan and Aiden are tagged `en`**
(both male). Recommended the user also check the Kokoro engine's preset list, since
it's English-first and likely has more `en` options with a wider tone range, before
committing to just Ryan/Aiden. **UNCONFIRMED whether the user checked Kokoro, or which
of Ryan/Aiden they ended up preferring** — test samples (a slower suspense-style
passage with `[pause]` tags, and a brisker business-failure passage) were given to
compare the two, but no result was reported back before this handoff.

**Description vs. Personality field (from the Voicebox "Create Voice" screen):**
Description is just reference metadata. **Personality is the functional one** — it
drives the Compose button and the in-character rewrite toggle on the generate page.
Draft personality text was written for a shared/default narrator voice, and then
refined into **three category-specific personality profiles**:
- `narrator_suspense` — measured, unhurried, real pauses at breath points, voice drops
  slightly before a reveal, never theatrical
- `narrator_cautionary` — brisk, confident, fact-forward, slight urgency, clean on
  numbers/specifics
- `narrator_warm` (human_interest) — moderate pace, gentle lift toward resolution,
  sincere not sentimental

A small Python config (not a DataStore table) maps category → Voicebox profile:
```python
VOICE_PROFILES = {
    "suspense": {"voice_id": "ryan", "personality_id": "narrator_suspense"},
    "cautionary": {"voice_id": "aiden", "personality_id": "narrator_cautionary"},
    "human_interest": {"voice_id": "ryan", "personality_id": "narrator_warm"},
}
```
Can reuse one base voice across categories and let personality do the differentiation
(cheaper/faster), or pair distinct voices per category — **decision deferred to
testing**, not yet locked.

**Content categorization decision:** category is classified as part of the same
structuring LLM call that produces the rest of the schema — not a separate step —
constrained to the fixed enum (`suspense` / `cautionary` / `human_interest` /
`curious`), validated on the response, never free text. Start with the first three
categories for the hackathon; add `curious` only if there's genuine slack.

---

## 8. Catalyst service mapping

- **DataStore** — the `ScenePaper` and `UserProfile` tables. See the column-type
  correction in section 4 — verify actual available types before building the schema.
- **Advanced I/O Function (Python)** — orchestrates: topic in → Wikipedia/news fetch →
  verify → LLM structuring call → TTS call → image fetch → write to DataStore → return.
  Confirmed via Catalyst docs: Python is supported for Advanced I/O Functions, **capped
  at Python 3.9** — check any library choice against this before adding it.
- **File Store** — intended to serve generated audio/image files. **Not yet confirmed
  working** — test this before relying on it mid-demo.
- **Auth** — explicitly out of scope for the hackathon unless there's real slack. Note
  as "not implemented, out of scope" in `docs/catalyst-notes.md` rather than leaving
  it silently missing.
- Route paths for the Function (`POST /ideate`, `POST /generate`, `GET/PUT/DELETE
  /paper/:id`) are the user's/Claude's own API design choice, not a Catalyst
  requirement — reasonable, but not verified against Catalyst's actual routing
  conventions for Python functions specifically.
- Deliberately **did not** wire Catalyst deployment into GitHub Actions — credential
  risk under time pressure. Deploy manually during the hackathon; "CI/CD to Catalyst"
  is a stated Day 4 "what's next" item, framed as good judgment rather than a gap.

---

## 9. Agents (`agents/` folder)

| Agent | Role |
|---|---|
| `catalyst-agent` | DataStore schema (ScenePaper + UserProfile) + Advanced I/O Function skeleton |
| `api-integration-agent` | Ideation search, Wikipedia/source verification, structuring call, TTS call, image API, secrets handling |
| `ui-agent` | Web client — topic input, candidate picker, paper view, playback, mocked paywall UI |
| `video-agent` | Tier 2 only — moviepy slideshow assembly, scene-timed crossfades |
| `feedback-agent` | Day 3 only — turns panel feedback into a checkpointed backlog |
| `docs-agent` | Keeps README, ai-docs/, token-log, api-notes, voice-notes in sync every session |

## Skills

None existed in the org's plugin/skill catalog when searched — creating these is
itself a scored deliverable ("Skills you used or created"), not just internal tooling:
- `catalyst-crud-scaffold` — reusable DataStore + Function boilerplate pattern
- `token-usage-logger` — appends usage estimate to `ai-docs/token-log.md` per session
- `demo-script-builder` — drafts/updates Day 2 and Day 4 talk outlines from git log
  + ai-docs

The user already has an existing **global handoff skill** (not new — predates this
project) — it's referenced by the Context-limit handoff behavior in `CLAUDE.md`, don't
recreate it.

---

## 10. Agent loop strategy (in `CLAUDE.md` — operating discipline for every session)

```
1. ORIENT     — read CLAUDE.md + the linked GitHub issue fully before touching code
2. PLAN       — state concrete steps for this issue only, no scope creep into other
                agents' territory
3. ACT        — small, reviewable chunks, not the whole issue in one diff
4. VERIFY     — run lint/tests locally (same checks as .github/workflows/lint-test.yml)
5. CHECKPOINT — stop, present the diff, wait for explicit approval before commit.
                Non-negotiable for normal (non-AFK) issues. This is the step most
                likely to get skipped under time pressure — don't skip it.
6. COMMIT     — reference the issue number, push to the worktree's feature branch
                only, never directly to main (branch protection enforces this)
7. LOOP OR HANDOFF — return to step 3 if unfinished; invoke the existing handoff
                skill proactively if context is running low, write the handoff note
                into the relevant GitHub issue as a comment, commit in-progress work,
                note which agent/worktree should pick it up next
```

**AFK mode** (issues explicitly labeled `afk` only): may skip the live checkpoint on
intermediate commits, but must still self-verify (lint/tests) before committing, must
**never merge to main** (push to feature branch, open a PR — the PR sitting ready for
review the next morning *is* the checkpoint, just deferred), and must **stop and
comment on the issue** rather than guess if any judgment call arises that isn't
already fully specified. Unlabeled or `hil`-labeled issues always require the live
checkpoint. Default to `hil` when uncertain which an issue is.

---

## 11. Task breakdown (Phase → Tasklist → Task, AFK/HIL tagged)

Full detail lives in `docs/task-breakdown.md`. Summary:

- **Phase 1 — Backend Foundation** (`catalyst-agent`) — DataStore schema, Function
  routing skeleton, local test harness. **All AFK.**
- **Phase 2 — Content Pipeline** (`api-integration-agent`) — Wikipedia search wrapper
  (AFK), source verification (AFK), ideation prompt tuning (**HIL**), structuring
  prompt (**HIL** — highest-leverage creative task), schema validation (AFK),
  category classification (AFK).
- **Phase 3 — Voice & Media** (`api-integration-agent`) — Voicebox script (AFK),
  breath-point pauses (AFK), personality tuning (**HIL**), image fetch + fallback
  logic (AFK).
- **Phase 4 — Product Layer** (`ui-agent`) — topic input/candidate picker (AFK),
  paper detail view (AFK), playback + usage indicator (AFK), visual/demo-polish pass
  (**HIL**), mocked usage-gate logic (AFK).
- **Phase 5 — MCP Layer** (`mcp-agent`) — mostly AFK, but **depends on Phases 1–4
  landing first** since each tool call wraps an already-built function. End-to-end
  validation of each tool call is **HIL**.
- **Phase 6 — Integration & Demo Readiness** — **entirely HIL, no exceptions.**
  Merge order: 1 → 2/3/4 → 5. Full live pipeline run. Demo script rehearsal.

**Two spikes flagged as highest priority, to run before real build time on either:**
1. Confirm Catalyst DataStore's actual available column types in the console (section 4)
2. Confirm a Catalyst function can serve MCP tool calls at all (section 6)
Both should become the literal first two issues, both tagged `hil` since a failed
assumption needs human judgment on the fallback. **The user had not yet confirmed
wanting these written as formal issues before this handoff was requested — this is
open, do it early in the new session.**

---

## 12. GitHub repo state — what's confirmed vs. not

**Confirmed done by the user:**
- Repo created at `github.com/Sankar-1804/scenepaper`, private
- Git identity fixed to personal email (`sankaranarayanan180402@gmail.com`) / name
  (`Sankar-1804`), set **locally for this repo only**, not global — office email
  (`sankaranarayanan.st@zohocorp.com`) should have zero trace after the repo was
  fully deleted and recreated from a clean local init
- Branch renamed `master` → `main`
- Initial commit pushed (project structure, `CLAUDE.md`, `docs/github-workflow.md`,
  `README.md`, `.gitignore`)
- `.gitignore` covers `.env`, `.env.local`, `__pycache__/`, `*.pyc`, `.DS_Store`,
  `node_modules/`
- **`CLAUDE.md` is up to date in the working directory** — includes the agent loop
  strategy, the AFK mode section, and the DataStore JSON-serialization correction.
  Confirmed by the user as of this handoff update; no longer treat this as at-risk
  from the earlier identity-fix reset.
- **`docs/task-breakdown.md` is up to date in the working directory** — the full
  Phase → Tasklist → Task breakdown with AFK/HIL tags from section 11. Also
  confirmed current, not stale.

**NOT CONFIRMED — check these explicitly in the new session before assuming they
exist:**
  actually created and pushed
- **Whether the four worktrees (`feature/catalyst-backend`, `feature/api-integration`,
  `feature/web-ui`, `feature/mcp-server`) still exist.** These were created via
  instructions given *before* the local folder got deleted and recreated during the
  git-identity cleanup. Worktrees share the parent repo's `.git` history — deleting
  and reinitializing the main folder would have orphaned or broken any worktrees
  created against the old history. **Treat these as needing to be recreated from
  scratch**, don't assume they're intact.
- Whether labels (`afk`, `hil`, `tier-1`, `tier-2`, `agent:catalyst`, `agent:api`,
  `agent:ui`, `agent:mcp`, `agent:video`) were created
- Whether milestones (Day 1–4) were created
- Whether a GitHub Project board was created
- Whether branch protection on `main` (require PR before merge) was set up via the
  GitHub UI — this was recommended but is a manual web UI step, not something run
  from the CLI, so it's easy to have been skipped
- Whether any real Day 1 issues (from the ~12-item seed list or the fuller
  phase/task breakdown) were actually created via `gh issue create`. **Intentional —
  the user decided to discuss and scrutinize each task in the CLI session itself
  before creating its issue, rather than bulk-creating issues from this planning
  conversation.** This is a deliberate sequencing choice, not an oversight — issues
  should be created with real technical grounding as they're actually tackled, not
  drafted blind ahead of time. Just make sure an issue exists *before* starting real
  implementation on something, and definitely before letting anything run in AFK mode
  unattended overnight.
- **No API keys have been obtained or configured as far as this conversation shows**
  — not for an LLM provider for the structuring call, not for Pexels/Unsplash, not
  any Catalyst project credentials. `gh secret set` commands were given but not
  confirmed run, and the actual key values were never discussed since the user
  hadn't gotten that far.
- Pexels vs. Unsplash — never finalized, pick one
- Ryan vs. Aiden (or a Kokoro-engine alternative) — voice test was set up, result
  never reported back

**First thing to do in the new session:** since `CLAUDE.md` and `docs/task-breakdown.md`
are now confirmed current, the remaining ground-truth check is narrower — run
`git log --pretty=format:"%h %an <%ae> %s"` and `git worktree list` to confirm the
push history and check whether the worktrees survived the earlier identity-fix reset,
plus `ls .github/workflows/` to check whether the Actions files exist. Don't assume
anything on the "NOT CONFIRMED" list above without checking it directly.

---

## 13. Ideas explored and explicitly rejected — do not resurface these

For context, so a fresh session doesn't waste time re-suggesting things already
considered and set aside:

- **Internal Instagram/Reels clone for Zoho visibility** — rejected: over-built
  video infrastructure for 4 days, doesn't fit the MCP-as-product angle well, reads
  as the most obvious/crowded pitch for an internal hackathon. A narrower reframe
  ("Work Broadcast" — MCP-native visibility tool) was floated but not pursued once
  ScenePaper won out.
- **Kathai** — generic "AI + human creativity" story-writing platform — rejected as
  a crowded, vague AI-wrapper category. A narrowed version (Tamil/vernacular
  folk-story structuring + narration) was suggested as more interesting but has zero
  validation done and was explicitly tabled for later, not part of this project.
- **Job Application Tracker + ATS scoring** — genuinely good idea, kept, but
  **demoted to a personal side project for the user's own job-switch prep, not the
  hackathon submission.** Entity (`JobApplication`), API sourcing (Adzuna/JSearch —
  Naukri/JustDial/LinkedIn confirmed to have no usable public APIs), and an ATS
  scoring engine as the real differentiator were all scoped, but none of this work
  is part of `scenepaper` — it would live in a separate repo entirely, whenever the
  user has slack for it.
- A dozen developer-tooling ideas (agent registry, session handoff vault, usage
  ledger, MCP test harness, config sync checker, prompt/spec history, parallel
  session conflict detector, agent attribution/blame layer, notification/hook
  registry, skill effectiveness tracker, local-fallback router, agent ROI ledger)
  were brainstormed in depth but none were selected — ScenePaper was chosen instead.
  Worth remembering these exist as a rich idea bank if ScenePaper ever needs a
  pivot, but not relevant to current execution.
- A GitHub link (`github.com/hamilton061996/storyboard`) was shared and returned a
  404 — never resolved, not relevant to anything going forward.

---

## 14. Immediate next actions for the new CLI session

In rough priority order:

1. **Read section 0 first.** Resolve the LLM API key blocker (0.1) — nothing in the
   pipeline can be built without it.
2. Run the four spikes from section 0 before writing real pipeline code: Catalyst
   function timeout (0.2), MCP-on-Catalyst feasibility (0.3), DataStore column types
   (0.4), and decide the source strategy question (0.6). All are HIL; any of them
   failing could force an architecture change.
3. Establish ground truth on repo state (section 12) — don't assume anything beyond
   what's explicitly confirmed there.
4. Recreate the worktrees if `git worktree list` shows they don't exist.
5. Set branch protection correctly per 0.8 — require PR, do NOT require approvals.
6. Decide Pexels vs. Unsplash, and confirm/re-test the Ryan vs. Aiden (or Kokoro)
   voice choice.
7. Only then start on Phase 1 (Backend Foundation) issues, following the agent loop
   strategy in section 10.
