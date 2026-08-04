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

### Tasklist 1.1 — DataStore & Function setup — AFK
- [ ] DataStore schema for `ScenePaper` + `UserProfile` (per CLAUDE.md schema)
  - [ ] Define columns, types, JSON fields
  - [ ] Write migration/setup script
- [ ] Advanced I/O Function routing skeleton
  - [ ] POST /ideate
  - [ ] POST /generate
  - [ ] GET /paper/:id
  - [ ] PUT /paper/:id
  - [ ] DELETE /paper/:id
- [ ] Local curl test harness + sample payloads

## Phase 2 — Content Pipeline `[api-integration-agent]`

### Tasklist 2.1 — Ideation search — Mixed
- [ ] Wikipedia search wrapper — **afk**
- [ ] Source verification logic (citable URL check) — **afk**
- [ ] Ideation prompt tuning (quality of 3–4 one-liners) — **hil**

### Tasklist 2.2 — Structuring call — Mixed
- [ ] Structuring prompt matching the rich schema — **hil** (highest-leverage
      creative task — do the first pass yourself, don't delegate blind)
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

## Phase 6 — Integration & Demo Readiness
Entirely HIL, no exceptions — this is where silent breakage between agents' work
would otherwise hide.
- [ ] Merge all worktree PRs in dependency order (1 → 2/3/4 → 5)
- [ ] Full pipeline run, live, by you
- [ ] Demo script rehearsal
