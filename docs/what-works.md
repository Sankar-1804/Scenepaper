# ScenePaper — what actually works, verified

Written 2026-08-10. Every claim here was checked against the live system, not
inferred from code. Where something is unverified or broken, it says so.

---

## The one-line summary

`topic → SearXNG search → verified candidates → Call A (score) → Call B
(structure) → NoSQL → retrievable over HTTP` — **works end to end, live.**

---

## 1. Verified working

### Search and ideation
`POST /ideate` — real SearXNG metasearch, domain-quality scoring, clustering,
LLM-summarised one-liners. Each candidate carries the **real sources** from
its cluster, which is what makes the later verification meaningful.

Measured: **20–25 seconds**, 4 candidates. Example (topic "corporate collapse"):

> *"Retail giant Sears filed for bankruptcy and announced plans to close 142
> unprofitable stores."* — 2 sources

### Verification and structuring
`POST /generate` → 202 + `job_id` + `paper_id`, then a Job function runs
Call A (verification/scoring) and Call B (structuring), and writes to NoSQL.

Measured: **~24 seconds** to a stored, retrievable paper.

### The scoring genuinely discriminates
Not a decorative number — three real runs:

| Story | Sources | Score | Status | Flags |
|---|---|---|---|---|
| Sears collapse | 2 quality | **9.5 / 8.5** | Verified | none |
| Snapchat redesign | 1 BBC | **7.5** | Plausible | `single source only` |
| Slack pivot | 1 trade press | **6.0** | Thinly Corroborated | `single source only` |

Same pipeline, same prompt — different evidence quality, different honest
answers. That is the product.

### It marks its own dramatization
Within one paper, sitting side by side:

```
verified=True   "The lighthouse was moved 70 meters inland on rails in October 2019."
verified=False  "Engineers described the rescue plan as daring before execution."
```

The second is narrative colour the model added for pacing. It says so.

### It refuses when sources are too thin
Given a sparse snippet, the ideation step returned:

> *"The snippet only mentions Enron's accounting methods and a regulatory
> filing, which is too thin to summarize into a story."*

It declined to invent a story. That refusal is the behaviour the whole trust
model exists to produce.

### Storage
Catalyst NoSQL. Full CRUD verified live — write via the pipeline, read via
`GET /paper?id=`, update via `PUT`, all against the real table.

### MCP server
`src/mcp_server/` — 7 tools. **4 live** (`search_story_ideas`,
`generate_scene_paper`, `get_scene_paper`, `verify_source`). **3 return
`not_implemented`** rather than fabricating data.

---

## 2. Known limits — say these before anyone asks

| Limit | Detail |
|---|---|
| **`/ideate` can time out** | ~25s against a hard **30s** Advanced I/O cap. Broad topics ("corporate collapse") work; specific single subjects ("Google") do more work and exceed it. Fix is moving ideation to a Job function with polling, as `/generate` already does. |
| **Voiceover and images are stubs** | Not wired. The UI no longer claims otherwise — the progress screen shows only the three stages that actually run. |
| **3 of 7 MCP tools are inert** | `generate_voiceover` (TTS stub), `list_available_stories` (needs a `category_index` route), `get_usage_status` (needs the UserProfile counter). They fail honestly. |
| **Free-tier quota** | RPD **20 per model, per key**. Two keys rotate. Failed calls consume quota too. |
| **SearXNG runs via a tunnel** | Self-hosted locally; the Catalyst cloud reaches it through an ngrok tunnel whose URL changes on restart. Stored in Catalyst Cache. |
| **Usage counter is fake** | "3 of 10 free papers used" is hardcoded — no UserProfile route exists yet. |

---

## 3. Demo path that is known to work

1. Topic: **"corporate collapse"** or **"underdog startup comeback"** — broad
   topics stay inside the 30s cap. Avoid single-subject queries.
2. Wait ~25s. Candidates appear with real sources.
3. Pick one that is **not** flagged `thin sourcing`.
4. Wait ~25s. The scene paper appears with its score, flags, hooks, scenes and
   per-clause verification marks.

**Fallback:** append `?mock=1` for the full click-through on mock data. It is
labelled as mock in the UI — do not present it as live.

---

## 4. Pre-demo checklist

- [ ] SearXNG running — `~/Desktop/Personal/Projects/searxng/start-scenepaper.sh --bg`
- [ ] ngrok tunnel up, and `SEARXNG_BASE_URL` in Catalyst Cache matches it
- [ ] `GEMINI_API_KEY` / `_2` present in Cache **and** not quota-exhausted
- [ ] Cache entries not expired (**48h max TTL** — they will lapse)
- [ ] One paper pre-generated as insurance against a quota wall
- [ ] Hard-reload the page (`Cmd+Shift+R`) so no stale JS is cached
