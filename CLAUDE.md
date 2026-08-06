ScenePaper — Project Context

This file is the shared source of truth for every Claude Code session working on this repo, across every worktree. Read this fully before doing any work.

This file supplements, not replaces, your global ~/.claude/CLAUDE.md. Global conventions (tooling defaults, personal workflow preferences, handoff protocol, review checkpoint discipline) still apply here unless something below explicitly overrides them for this project. If the two ever conflict, project rules in this file win for work inside this repo; everything else defers to global.

Agent loop strategy (how every session should actually operate)

Every agent session in this repo — regardless of which worktree — follows this loop. This is not optional structure, it's what makes multiple parallel Claude Code sessions safe to run unsupervised for stretches of time.

1. ORIENT     — read this file + the linked GitHub issue in full before touching code.
                Confirm the issue's scope; do not silently expand into another agent's
                territory (e.g. api-integration touching UI files).
2. PLAN       — state the concrete steps for this issue only, before acting.
3. ACT        — implement in small, reviewable chunks. Not the whole issue in one
                giant diff — verification only works on changes small enough to
                actually review.
4. VERIFY     — run lint/tests locally (same checks as .github/workflows/lint-test.yml)
                before presenting anything as done. A change that would fail its own
                CI check is not finished.
5. CHECKPOINT — stop. Present the diff. Wait for explicit approval before committing.
                This step is non-negotiable — it is the human-in-the-loop point that
                makes unattended agent work trustworthy. Never skip it to save time.
6. COMMIT     — reference the issue number in the message. Push to this worktree's
                feature branch only. Never push directly to main — open a PR instead,
                branch protection on main requires this regardless.
7. LOOP OR HANDOFF — if the issue isn't complete, return to step 3. If context is
                running low, invoke the handoff skill (see Context-limit handoff
                below) rather than pushing through with degraded output.

Step 5 is the step most likely to get skipped under time pressure — don't skip it. An agent that commits without a checkpoint is not following this loop, even if the resulting code happens to work.

What this is

ScenePaper is a tool for short-form content creators (YouTube Shorts, Instagram Reels) that takes them from zero to recording-ready fast. Instead of 3–5 hours of research and structuring per video, the creator submits a topic, gets a real, source-verified story pre-structured into a "scene paper" — hook, pacing marks, breath points, delivery notes — plus a generated voiceover and supporting images.

This is being built for two purposes simultaneously:

A 4-day internal Zoho AI hackathon submission (checklist-graded, see constraints below)
A real product — this is not throwaway hackathon code, treat it like the start of an actual MVP

The actual differentiator — protect this: the moat is the curated, verified story library and the fixed scene-paper output format, not the AI generation step itself. The moment this becomes "paste a prompt, get a script," it's commoditized like every other AI writing tool. Every structuring step must be gated by real source verification, and the output must always conform to the scene-paper schema, not free-form text.

Hackathon constraints (hard rules — do not violate)
4 days total. Checklist-graded against 8 required outputs — not just app quality.
Backend: Zoho Catalyst preferred (NoSQL, Advanced I/O Functions, File Store, Auth). If any Catalyst service is skipped, document why in docs/catalyst-notes.md.
Language: Python (Catalyst supports Python up to 3.9 for Advanced I/O Functions — verify any library against this before adding it).
Scope: ONE primary entity (ScenePaper), full CRUD, demoable live. No secondary entities until this is airtight.
Repo layout is fixed and non-negotiable: README.md, ai-docs/, docs/, agents/, src/
Never commit secrets/API keys. Confirm .gitignore covers .env before first commit.
Every external API call documented in docs/api-notes.md (endpoint, purpose, auth).
Custom agent(s) live in agents/ with a clearly stated role, not a raw prompt dump.
MCP connection must be used during actual development AND the product itself ships its own MCP server — this is the hackathon differentiator, do not treat it as optional.
AI tooling: Claude (Enterprise) is primary. GitHub Copilot for inline autocomplete. Sahaa deliberately for small/low-risk tasks only. Log usage after every session to ai-docs/token-log.md — this is a required deliverable, not optional bookkeeping.
Day 1 exit bar: idea locked (done), CRUD working, 1 agent + 1 MCP used, pushed to remote.
Day 3 rule: I drive every change myself with agent/Sahaa/Claude as tools. Checkpoint before applying any panel feedback — no unreviewed auto-apply.
Two 10-minute talks are real deliverables: Day 2 pitch, Day 4 retro. Draft scripts early, don't write them cold.
Product flow (the real shape, not just CRUD)
User has a lightweight UserProfile (about_me / niche description) that informs ideation — not full multi-user auth for the hackathon, effectively single-user.
User submits a topic. The ideation step searches for verified candidate stories via **SearXNG** (self-hosted metasearch — decided in the session-2 addendum, supersedes the earlier Wikipedia/news-API framing) and returns 3–4 one-liner options, always the top 3 regardless of score (see Search, verification & trust model below). Candidates are ephemeral — do not persist them as their own CRUD entity, this stays within the "one primary entity" rule. ScenePaper remains the only NoSQL table.
User picks one candidate. Only then does the full structuring pipeline run (two separate LLM calls — verification, then structuring, see below) and a ScenePaper row gets created.
Free/paid gate: first 10 ScenePaper generations (text) are free, total, then each further paper is paid. Audio/video export is a separate gate, always paid, even for papers generated within the free 10.
Hackathon demo: no real payment gateway. Mock both gates — real counters, real "Unlock" UI states, no actual charge, no Razorpay/Stripe integration. Label mocked actions honestly in the UI rather than faking a real checkout flow.

Search, verification & trust model (session-2 addendum — full detail in ai-docs/, this is the working summary)

Search pipeline: user request → classify (broad vs. specific) → build query set → SearXNG → filter/rank → cluster into distinct candidates → summarize into one-liners. SearXNG is noisy (news/blogs/Reddit/SEO farms mixed together) — domain-quality scoring happens before clustering, and snippets alone are too thin to judge a story, so expect to fetch the top 1-2 results per cluster. SearXNG is self-hosted — hosting location is still an open decision (docker unavailable in this environment as of session 2; needs a resolution before Phase 2 is buildable — see docs/catalyst-notes.md).
Broad requests (e.g. "motivational story") fan out into 3-4 parallel SearXNG queries across sub-angles of the creator's niche, prompted for structurally different angles (era/industry/failure-vs-success), not near-synonyms.
Specific requests (e.g. "Snapchat") run a discovery step first: cluster by event, and prefer different-events-in-the-subject's-history (Axis 1) when >=3 documented events exist, falling back to different-framings-of-one-event (Axis 2) when they don't. Watch for subject ambiguity (resolve via profile/domain or ask) and over-told subjects (deliberately reach for a less-covered angle).
"Show me more": fresh search every round, no pre-fetch caching — cost scales with actual demand. Query generation runs against a growing exclusion context (already_surfaced[...]) with a controlled `angle_type` vocabulary (comeback, rejection, pivot, underdog, sacrifice, lucky-break, etc.) so round 2 mechanically avoids round 1's angle types rather than hoping the model varies on its own. Detect exhaustion (heavy overlap or dropping quality) and say so honestly rather than serving progressively worse candidates.

Verification scoring: always show top 3 regardless of score — suppressing low scorers silently narrows the library to well-SEO'd mainstream stories, the opposite of the product's value. The only suppression is outright fabrications, satire, and AI-content-farms — and suppressed candidates must still be shown with their suppression reason (also a real demo moment). Score format: `x/10` plus a tag (bands/vocabulary deliberately deferred until real SearXNG output exists). Two separate signals, never conflated: a graded confidence score, and binary flags (`sources conflict`, `single source only`, `unverified origin`, `claim not found in primary sources`) — thinly-sourced is not the same as contradicted, and flags tell the creator exactly what to go check.

Prompt injection defense (non-negotiable architecture, not a nice-to-have): verification/scoring and structuring/formatting are **two separate LLM calls**. Call A (verification) never sees the user's profile config and receives only sources + platform-owned rules. Call B (structuring) sees the profile config for format preferences but has no authority to change the score — it receives Call A's score as a fixed input. This holds even if the profile config contains injected instructions, because the call that could act on them never sees them, and the call that sees them can't act on scores. Defense in depth on top of this: parse the profile config into a whitelisted field set (unrecognized sections dropped with a visible warning), and frame passed-through values as data ("the user's stated tone preference is: <value>"), never as raw instructions.

Multi-sector configurability: a user-editable `profile.md`-style config (separate from the `UserProfile` entity — a file, not a DB row) controls **format only** — scene structure, categories, runtime target, tone, avoid-list — fed into query generation and Call B. **Verification rules (source hierarchy, reliability weights, suppression thresholds) stay platform-owned, never user-configurable** — letting a creator declare their own high-quality sources turns the score into "agreement with user beliefs," which destroys the entire verification moat. Sectors without a dedicated source integration still work, just score lower, honestly reflecting reduced verification depth rather than pretending uniform coverage.

Trust model: do not build toward "blind trust" — one confidently-wrong story does more damage than an honestly-low-scored one, because the creator's audience turns on them, not on the tool. The target is collapsing verification from hours to seconds, not removing it. Trust compounds through calibration (a 9/10 that's reliably solid, a 5/10 that reliably needs work) — bias scoring toward honesty over flattering numbers. The one failure mode source verification cannot catch: every individual claim can verify and the compressed hook can still mislead (narrative color, selective omission). Mitigate with an explicit check in the structuring step — does the hook overstate what sources actually support — and mark unverifiable narrative framing distinctly from sourced fact in the output itself, never in the same confident voice.

Entity schema
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
  scenes[]                  # [{scene_number, scene_name, pacing_tag, time_range, script[]}]
                            # script[] = [{speaker, line, direction}] -- a real script, not a
                            # one-line summary. `speaker` is "SPEAKER" for single-voice scenes;
                            # when a scene genuinely needs more than one, suffix with numbers
                            # ("SPEAKER_1", "SPEAKER_2", ...). `line` is the exact spoken text.
                            # `direction` is inline tone/pacing/pause guidance for that specific
                            # line (e.g. "drop pace here, [pause 0.6s] before the reveal") --
                            # written so it could be fed close to directly into Voicebox.
  delivery_notes[]          # [{label, note}] -- CTA-level notes ONLY now. Per-scene/per-line
                            # delivery guidance moved into scenes[].script[].direction (session-2
                            # addendum, decided after reviewing the mock UI's one-liner scenes and
                            # finding them too thin -- see docs/task-breakdown.md Phase 2).
  cta_text
  sources[]                 # [{title, type, date, verified, confidence_score /10, tag, flags[], suppressed, suppression_reason}]
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

profile.md                  # NOT a DB entity — a user-editable file, see Search/verification/trust
                             # section above. Controls format only (scene structure, categories,
                             # tone, avoid-list); verification rules stay platform-owned.

pacing_tag values: FAST / BUILD / SLOW / WARM — matches the validated mock format. **DB decision (session 2): Catalyst NoSQL, not the relational Data Store.** All nested fields (hooks, scenes, delivery_notes, sources, image_set) store as **native JSON** within the single ScenePaper document — no manual serialization needed, since NoSQL stores documents as-is. This keeps the design compliant with the hackathon's "one primary entity" rule while still carrying the full product-grade structure. Secondary indexes (Catalyst NoSQL supports up to 20 per table) handle filtering — e.g. an index on `category` for `list_available_stories(category)`. Full relational-vs-NoSQL tradeoff analysis in docs/catalyst-notes.md.

Feature tiers (do not build out of order)

Tier 1 — Core, must work Day 1–2 (this is what gets demoed live):

Topic → 3–4 verified candidate stories (one-liners) via SearXNG → user picks one
Structuring call, split into two isolated LLM calls per the prompt-injection defense above: Call A (verification/scoring) → Call B (structuring: verified source + Call A's fixed score → full rich schema: hooks[], scenes[] with pacing tags, delivery_notes[], sources[], cta_text) — get this exactly right first, it's what makes the demo look finished even before any audio plays
Voiceover generation (TTS) — a single consistent voice reading story_body, with pauses inserted at breath points. Per-scene pacing-tag-aware delivery (speeding up on FAST, slowing on SLOW) is a refinement, not a Day-1 requirement — get a working voiceover first, tune its pacing-awareness after, don't let tuning block progress.
Supporting images: real stock photos (Pexels or Unsplash API) matched per scene keyword — NOT AI-generated images, too unreliable for a live demo on this timeline
Full CRUD on ScenePaper including its media
Mocked free/paid gates (10-free counter, always-paid export toggle) — no real payment gateway
MCP server exposing the pipeline as tool calls

Tier 2 — Stretch, Day 3 only, only if Tier 1 is bulletproof:

Video export as a synced slideshow (not a full editor): scene images shown in sequence, timed against that scene's portion of the audio, simple crossfade between them. Build with moviepy once audio + images from Tier 1 already exist — this is assembly on top of proven pieces, not a new pipeline.
Per-scene pacing-tag-aware voiceover delivery (the refinement noted above)
Multiple voice options matched to category tone (Voicebox personality profiles: narrator_suspense, narrator_cautionary, narrator_warm — see docs/voice-notes.md)
Mobile (SwiftUI) client hitting the same media endpoints

Tier 3 — Explicitly out of scope for the hackathon, product roadmap only:

AI-generated custom imagery
Auto-captioning / burned-in subtitles
Real payment integration (Razorpay/Stripe), real multi-user accounts/auth
Full non-linear video editing beyond the synced slideshow

If unsure whether to build something, check which tier it's in. Never pull Tier 3 work into hackathon time.

MCP tools to expose
search_story_ideas(topic) — returns 3–4 verified candidate one-liners
get_scene_paper(topic) — retrieve a full paper including media URLs
verify_source(paper_id) — returns source URL + verification status
generate_scene_paper(source_url) — triggers the full structuring pipeline
generate_voiceover(paper_id) — regenerate audio independently
list_available_stories(category) — browse without the UI
get_usage_status(user_id) — returns free-tier count remaining + export lock state
Catalyst service mapping
NoSQL — the ScenePaper table (decided over the relational Data Store in session 2 — native JSON document fit, secondary indexes cover the category-filter need; see docs/catalyst-notes.md)
Advanced I/O Function (Python) — orchestrates: topic in → SearXNG search/cluster → verification call (Call A) → structuring call (Call B) → TTS call → image fetch → write to NoSQL → return
File Store — serves generated audio/image files; confirm this works cleanly before relying on it mid-demo
Auth — explicitly out of scope for hackathon unless time allows; note as "not implemented, out of scope" rather than leaving it silently missing
Agents (in agents/)
Agent	Role
catalyst-agent	NoSQL schema (ScenePaper + UserProfile) + Advanced I/O Function skeleton
api-integration-agent	Ideation search (SearXNG), verification scoring (Call A), structuring call (Call B), profile.md parsing, TTS call, image API, secrets handling
ui-agent	Web client — topic input, candidate picker, paper view, playback, mocked paywall UI
mcp-agent	Wraps the finished pipeline as MCP tool calls — the hackathon's actual differentiator; depends on Phases 1-4 landing first
video-agent	Tier 2 only — moviepy slideshow assembly, scene-timed crossfades
mobile-core-agent	Tier 2 only, gated behind Tier 1 being demo-safe — shared Rust core (FFI bindings via UniFFI or similar) reused by the iOS and Android clients; web stays on direct JSON + JS, no Rust involved there
feedback-agent	Day 3 only — turns panel feedback into a checkpointed backlog
docs-agent	Keeps README, ai-docs/, token-log, api-notes, voice-notes in sync every session
Skills to build (none exist in-org yet — creating these is itself a scored deliverable)
catalyst-crud-scaffold — reusable NoSQL + Function boilerplate pattern
token-usage-logger — appends usage estimate to ai-docs/token-log.md per session
demo-script-builder — drafts/updates Day 2 and Day 4 talk outlines from git log + ai-docs
Working conventions in this repo
This project uses git worktree — see docs/github-workflow.md for the full setup. Each active worktree corresponds to one agent's scope. Do not do cross-cutting work in a worktree scoped to a single agent; open an issue and switch worktrees instead.
Every unit of work should trace to a GitHub Issue. Reference the issue number in commit messages (#12).
Before ending a session: update ai-docs/token-log.md, confirm the relevant docs/*.md file reflects what changed, and leave a short handoff note in the issue if work isn't finished.
Context-limit handoff

When context in a session is running low (approaching the point where quality would degrade, not right at the hard limit), stop new feature work and do the following in order:

Invoke the handoff skill to produce a structured handoff note — current state, what's done, what's next, any blockers or decisions pending.
Write that note into the relevant open Issue as a comment (not just locally), so the next session — yours or another agent's — has it without you re-explaining.
Commit any in-progress work on the current worktree branch, even if incomplete, with a clear WIP commit message referencing the issue.
Only then hand off: either resume yourself in a fresh session in the same worktree, or, if the remaining work belongs to a different agent's scope, note in the issue which agent/worktree should pick it up next.

Do not let a session run to the point of degraded output before handing off — the handoff should happen proactively, not as a last resort once things are already going wrong.

What NOT to do
Do not build a WYSIWYG resume/script editor or any UI complexity beyond what's needed to demo the pipeline live.
Do not attempt AI-generated imagery — stock photo APIs only, for reliability.
Do not let Tier 2/3 features start before Tier 1 is fully working and demo-safe.
Do not skip source verification to save time — this is the actual product moat, cutting it defeats the point of the build.