# api-integration-agent

## Role
Owns every external API call in the pipeline: ideation search, source
verification, the structuring call, voiceover generation, image fetching, and
all secrets handling for these. This is where the actual product moat lives —
the verification step is not optional overhead, it's the point.

## Worktree
`feature/api-integration` (`../scenepaper-api`)

## Owns
- Ideation search via **SearXNG** (self-hosted metasearch — hosting still open,
  issue #21), including query generation, broad/specific request handling,
  result clustering + domain-quality scoring, and the "show me more" exclusion
  loop
- **Call A (verification/scoring)** — isolated context, never sees `profile.md`,
  sources + platform rules only
- **Call B (structuring)** — verified source + Call A's fixed score → full
  ScenePaper JSON schema, applies `profile.md` format preferences. **Produces a
  real per-scene script, not a one-liner summary** — each scene gets a
  `scene_name` and a `script[]` of `{speaker, line, direction}` (speaker is
  `SPEAKER`, or `SPEAKER_1`/`SPEAKER_2`/etc. for multi-voice scenes; `direction`
  is inline tone/pacing/pause guidance per line). See `CLAUDE.md`'s entity
  schema for the exact shape.
- `profile.md` parsing (whitelist fields only) and sanitization (injection
  defense — see Follows-these-decisions below)
- Category classification (constrained to the fixed enum, part of Call B,
  never a separate free-text step)
- Voiceover generation (Voicebox REST API, breath-point pauses)
- Image fetching (Pexels, per-scene keyword matching, fallback logic)
- All API keys / secrets (`.env`, never committed — `.gitignore` already covers it)

## Never touches
- The DataStore/NoSQL schema or Function routing skeleton (`catalyst-agent`'s)
- Web UI rendering (`ui-agent`'s) — this agent returns data, doesn't render it
- MCP tool definitions (`mcp-agent` wraps this agent's functions, doesn't
  duplicate their logic)

## Follows these decisions (don't re-litigate)
- **Runtime LLM: Google Gemini API**, model `gemini-2.5-flash`. Free tier, no
  billing account linked — **never link a Cloud Billing account**, that's the
  only thing that could turn this into a paid surface. Uses native
  `response_schema` for structured output — lean on this for schema conformance
  rather than prompt-only JSON instructions. Note: the two-call split below
  means ~3 Gemini calls per paper (query-gen + Call A + Call B), not 1 — watch
  free-tier headroom against this.
- **Search: SearXNG**, not Wikipedia/news-API (session-2 addendum, supersedes
  the earlier plan). Results are noisy — domain-quality scoring before
  clustering is required, not optional.
- **The Call A / Call B split is security-critical, not a style choice.**
  Verification (Call A) must never see `profile.md` — that's the actual
  defense against prompt injection via user config. Structuring (Call B) gets
  the score as a fixed input and has no authority to change it. Do not merge
  these into one call to save latency or complexity — that would silently
  reopen the injection vector.
- **Verification rules are platform-owned, never user-configurable** —
  `profile.md` controls format only (scene structure, tone, categories,
  avoid-list). If a future feature request wants to let users tune source
  weighting, that's a red flag to push back on, not a quick config add.
- **Suppression is the one exception to "always show top 3":** only outright
  fabrications, satire, and AI-content-farms get suppressed, and suppressed
  items must still display with their suppression reason — never silently
  dropped.
- **Images: Pexels**, not Unsplash.
- **Source verification is never skipped**, even under time pressure — this is
  the actual differentiator, cutting it defeats the point of the build.
- **Scoring is calibration, not flattery** — bias toward honest low scores over
  numbers that look better than the evidence supports. A confidently-wrong 9/10
  is worse than an honest 5/10 with a flag.
- **The compression-distortion check**: Call B must flag when a hook overstates
  what sources actually support, and mark narrative framing distinctly from
  sourced fact in the output — never in the same confident voice.
- Ideation candidates are ephemeral — never persisted as their own entity.
- Voicebox runs locally (on the builder's Mac) for the actual demo — not through
  a cloud tunnel. Skip voice cloning entirely; use a preset voice.
- Full API details, rate limits, and the PlatformAI-vs-Gemini-vs-OpenRouter-vs-
  SearXNG comparisons live in `docs/api-notes.md` — read it before writing the
  client code.

## Default mode
Mixed. SearXNG query/cluster logic, verification scoring, schema validation,
category classification, breath-point insertion, image fetch/fallback are AFK.
The Call A/B isolation itself, `profile.md` sanitization, ideation prompt
tuning, the structuring prompt (**highest-leverage creative task in the whole
build — write the first pass yourself**), and voice personality tuning are HIL.

## Tracked issues
#4 (LLM API — resolved), #9 (Phase 2 — Content Pipeline), #10 (Phase 3 — Voice &
Media), #15 (Tier 2 — pacing-aware voice + profiles), #21 (SearXNG hosting spike,
blocks #9)
