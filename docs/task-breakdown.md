# Task Breakdown — Tier 1

Phase → Tasklist → Task → Subtask, each task tagged `afk` or `hil`. See CLAUDE.md
for the full agent loop definition and the AFK mode variant.

## AFK vs HIL — the rule

**AFK** (agent runs unattended, self-verifies, commits, opens a PR — no live approval):
spec is fully defined already, success is machine-checkable, doesn't touch another
agent's files or `main`.

**HIL** (needs you present): anything subjective (does this read/sound/look right),
cross-agent integration, secrets/deployment, merging to `main`, panel feedback.

When in doubt, it's HIL.

## Phase 1 — Backend Foundation `[catalyst-agent]`

### Tasklist 1.1 — NoSQL & Function setup — AFK
- [ ] NoSQL table design for `ScenePaper` + `UserProfile` (per CLAUDE.md schema) — native JSON documents, no serialization needed
  - [ ] Define secondary indexes (at minimum: `category` for `list_available_stories`)
  - [ ] Write table/index setup script
- [ ] Advanced I/O Function routing skeleton
  - [ ] POST /ideate
  - [ ] POST /generate
  - [ ] GET /paper/:id
  - [ ] PUT /paper/:id
  - [ ] DELETE /paper/:id
- [ ] Local curl test harness + sample payloads

## Phase 2 — Content Pipeline `[api-integration-agent]`

### Tasklist 2.1 — Ideation search (SearXNG) — Mixed
- [ ] SearXNG hosting resolved (self-hosted — docker unavailable as of session 2, needs an alternative) — **hil**, blocks everything below
- [ ] Query classification: broad vs. specific request — **afk**
- [ ] Query-generation call: structured JSON output, controlled `angle_type` vocabulary — **hil** (tune for genuinely different angles, not near-synonyms)
- [ ] Broad-request fan-out: 3-4 parallel SearXNG queries across niche sub-angles — **afk**
- [ ] Specific-request discovery step: cluster by event, Axis 1 (different events) vs. Axis 2 (different framings) per the >=3-events rule — **afk**
- [ ] Result clustering + domain-quality scoring (SearXNG results are noisy — filter before clustering) — **afk**
- [ ] Fetch top 1-2 results per cluster for one-liner generation (snippets alone are too thin) — **afk**
- [ ] "Show me more" loop: exclusion context (`already_surfaced[...]`), hint handling, exhaustion detection — **afk**
- [ ] Ideation prompt tuning (quality of 3–4 one-liners) — **hil**

### Tasklist 2.2 — Verification & structuring — Mixed
- [ ] **Call A (verification/scoring)** — never sees profile.md, sources + platform rules only — **hil** (security-critical, get the isolation right first)
- [ ] Scoring output: `x/10` + tag + binary flags (`sources conflict`, `single source only`, `unverified origin`, `claim not found in primary sources`) — **afk**
- [ ] Suppression logic: fabrications/satire/AI-farms only, always shown with reason — **afk**
- [ ] profile.md parsing: whitelist fields only, unrecognized sections dropped with a visible warning — **afk**
- [ ] profile.md sanitization: length caps, values framed as data not instructions, log rejections/truncations — **hil**
- [ ] **Call B (structuring)** — receives Call A's score as a fixed input, no authority to change it, applies profile.md format prefs — **hil** (highest-leverage
      creative task — do the first pass yourself, don't delegate blind)
  - [ ] **Output a real per-scene script, not a one-liner summary** (session-2 addendum, decided after reviewing the mock UI's thin scene descriptions): each `scenes[]` entry needs a `scene_name` and a `script[]` array of `{speaker, line, direction}` — `speaker` is `"SPEAKER"` for single-voice scenes, `"SPEAKER_1"`/`"SPEAKER_2"`/etc. when a scene genuinely needs more than one, `line` is the exact spoken text, `direction` is inline tone/pacing/pause guidance per line. `delivery_notes[]` is now CTA-only.
- [ ] JSON schema validation + retry-on-invalid — **afk**
- [ ] Category classification (enum-constrained) — **afk**

## Phase 3 — Voice & Media `[api-integration-agent]`

### Tasklist 3.1 — Voiceover — Mixed
- [ ] Python script hitting Voicebox REST API — **afk**
- [ ] Breath-point pause insertion — **afk**
- [ ] Voice personality tuning per category — **hil**

### Tasklist 3.2 — Images — AFK
- [ ] Pexels/Unsplash fetch per scene keyword
- [ ] Fallback logic when no good match exists

## Phase 4 — Product Layer `[ui-agent]`

### Tasklist 4.1 — Web CRUD client — Mixed
- [ ] Topic input + candidate picker — **afk**
- [ ] Scene paper detail view (full schema render) — **afk**
- [ ] Playback + usage-limit indicator — **afk**
- [ ] Visual/demo-polish pass — **hil** (this is what the panel sees first)

### Tasklist 4.2 — Mocked usage-gate — AFK
- [ ] Counter + free-limit check
- [ ] Export lock/unlock toggle

## Phase 5 — MCP Layer `[mcp-agent]`
Depends on Phases 1–4 landing first — each tool call wraps an already-built function.
- [ ] MCP server scaffold — **afk**
- [ ] `search_story_ideas` — **afk**
- [ ] `get_scene_paper` — **afk**
- [ ] `verify_source` — **afk**
- [ ] `generate_scene_paper` — **afk**
- [ ] `generate_voiceover` — **afk**
- [ ] `list_available_stories` — **afk**
- [ ] `get_usage_status` — **afk**
- [ ] End-to-end validation of every tool call — **hil**

## Phase 5.5 — Mobile Core `[mobile-core-agent]` — Tier 2, Day 3 only
Gated behind Tier 1 being fully working and demo-safe (same rule as the rest of
Tier 2) — do not start this while Tier 1 is still shaky. Web client is unaffected:
it renders the direct JSON response from the Python API via JS, no Rust involved.
- [ ] Rust core crate: shared request/response models + client logic for the
      ScenePaper API — **afk**
- [ ] UniFFI (or equivalent) bindings generated for Swift — **afk**
- [ ] UniFFI (or equivalent) bindings generated for Kotlin — **afk**
- [ ] iOS app wired to the Rust core — **hil** (first real integration test of
      the bindings)
- [ ] Android app wired to the Rust core — **hil**, and only attempted if there's
      real slack — Android remains the first thing to drop if time is short

## Phase 6 — Integration & Demo Readiness
Entirely HIL, no exceptions — this is where silent breakage between agents' work
would otherwise hide.
- [ ] Merge all worktree PRs in dependency order (1 → 2/3/4 → 5)
- [ ] Full pipeline run, live, by you
- [ ] Demo script rehearsal
