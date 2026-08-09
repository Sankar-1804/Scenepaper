# Catalyst Notes

Tracks which Zoho Catalyst services are used, why, and documents anything skipped per the hackathon rule: "if a Catalyst service is skipped, document why."

## Database decision: Catalyst NoSQL (DECIDED, session 2)

Went with **Catalyst NoSQL** over the relational **Data Store**. Both were researched in depth before deciding — full reasoning below, since this was a real architectural fork, not an obvious call.

**Why NoSQL won:**
- ScenePaper's schema is naturally one self-contained bundle per paper (`hooks[]`, `scenes[]`, `delivery_notes[]`, `sources[]`, `image_set[]` all belonging to one entity) — that's already document-shaped, not table-shaped. NoSQL stores it as native JSON, no serialization needed. Data Store has **no native JSON column type** (confirmed from official docs: only Text, Var Char, Date, DateTime, Int, BigInt, Double, Boolean, Foreign Key, Encrypted Text exist) — nested fields would've needed manual `json.dumps()`/`json.loads()` into a Text column.
- The hackathon has exactly one real filtering need (`list_available_stories(category)`), and Catalyst NoSQL's secondary indexes handle that cleanly: **up to 20 indexes per table**, global/cross-partition, each with its own independently configurable partition key and sort key. An index with `category` as the partition key covers the current need directly.
- **The one real tradeoff, weighed deliberately:** Data Store's ZCQL supports arbitrary multi-condition filtering (`WHERE x AND y AND z`) for free. NoSQL multi-condition filtering requires either a pre-planned composite index (e.g. partition key literally `"category#verification_status"`) or querying one index then filtering the remainder in application code. Since ScenePaper is meant to become a real product beyond the hackathon, this is a genuine future-flexibility cost, not just a today-non-issue — accepted deliberately, not overlooked. If a genuinely unplanned multi-field filter need shows up later (e.g. an open-ended creator-facing filter UI), that's the point to revisit this.
- Source: [NoSQL Introduction](https://docs.catalyst.zoho.com/en/cloud-scale/help/nosql/introduction/), [NoSQL Indexing](https://docs.catalyst.zoho.com/en/cloud-scale/help/nosql/indexing/introduction), [Data Store Introduction](https://docs.catalyst.zoho.com/en/cloud-scale/help/data-store/introduction/), [Data Store Column Types](https://docs.catalyst.zoho.com/en/cloud-scale/help/data-store/columns)

**Issue #1 — RESOLVED.** The Zoho-provided Catalyst MCP server and the CLI both turned out to only expose the **relational Data Store API** — no partition key, sort key, or index-creation concept anywhere in either. Confirmed directly in the real console instead:
- `ScenePaper` table created, partition key `id` (String), no sort key
- Secondary index `category_index` on `ScenePaper`, partition key `category` (String) — powers `list_available_stories(category)`
- `UserProfile` table created, partition key `id` (String), no sort key, no index needed
- Nested fields (`hooks`, `scenes`, `sources`, `image_set`, etc.) aren't pre-declared as columns — written as part of the document body at insert time, exactly as the NoSQL decision assumed

The stubbed `# TODO(issue #1)` DB calls in `functions/scenepaper_pipeline/main.py` can now be replaced with real reads/writes.

## Issue #2 — RESOLVED: 30 seconds (Basic/Advanced I/O), 15 minutes (Event/Cron/Job)

Confirmed directly from Zoho's official docs — [Serverless FAQ](https://docs.catalyst.zoho.com/en/faq/serverless), [Job Pool Key Concepts](https://docs.catalyst.zoho.com/en/job-scheduling/help/jobpool/key-concepts/):
- **Basic I/O and Advanced I/O functions: 30 seconds max.** The original handoff's 60+ second pipeline estimate definitively exceeds this — the async job pattern it flagged as a fallback is now a **confirmed requirement**, not a hypothetical.
- **Event, Cron, and Job functions: 15 minutes max.**
- **Job functions are Catalyst's purpose-built mechanism for exactly this.** Confirmed via the actual scaffolded code template (`catalyst functions:add --type job`): the handler receives a `job_request` object (`get_job_details()`, `get_all_job_params()`, `get_job_param(key)`) and a `context` with `get_remaining_execution_time_ms()` / `get_max_execution_time_ms()`, and concludes via `context.close_with_success()` / `close_with_failure()` — built specifically for long async work that reports its own completion, not a repurposed Cron/Event function.
- **Concrete architecture, no custom async pattern needed:** the fronting Advanced I/O Function (behind the API Gateway route) calls `Create_Immediate_Job` (an MCP tool — targets a Job function, has a `notify_url` webhook callback field and built-in `job_config` retry behavior) and returns the job ID immediately, well within the 30s window. The actual pipeline (SearXNG → verify → structure → TTS → images → NoSQL write) runs inside the Job function, within its 15-minute budget. Status is checked via `Get_Job_By_Id`, or Catalyst notifies the `notify_url` on completion — no hand-rolled polling infrastructure required.

## Issue #3 — substantially de-risked, one thing left to verify live

- **API Gateway is REST-only** — confirmed from its own MCP tool schema (`Configure_API_Gateway_Route`): methods are GET/POST/PUT/DELETE/PATCH/ANY/OPTIONS, targets are Basic IO Function / Advanced IO Function / Web App. No streaming/SSE concept anywhere in the schema.
- **API Gateway was disabled by default** on the Scenepaper project — enabled via `catalyst apig:enable` this session (needed CLI login + `catalyst init` in `catalyst-agent`'s worktree first — see below). Confirmed live via the MCP (`List_All_API_route` no longer errors).
- **A real Advanced I/O function was deployed** (`scenepaper_pipeline`, see below) to test an actual round trip. Confirmed: calling its bare serverless URL directly returns 404 ("Invalid API") — **an Advanced I/O function is not reachable until an API Gateway route is explicitly configured for it.** This itself is a useful finding: routes aren't optional wiring, they're load-bearing.
- **Blocked on:** creating that route via `Configure_API_Gateway_Route` hit a persistent `"Invalid input value for target"` error across multiple attempted values (`"Advanced IO Function"`, `"AdvancedIO Function"` — both match or nearly match the tool's own documented enum) that couldn't be resolved through the MCP this session. Try via the console UI directly, or the CLI, next. Once a route exists, the real "hello world" MCP-tool-call test (issue #3's original ask) is finally testable — given issue #2's resolution, each individual MCP tool call can stay short/synchronous (well under 30s) even though the underlying pipeline is async, which removes the theoretical blocker; only the practical route-creation step remains.

## Catalyst project state (as of this session)

- **Org:** `Sankaranarayanan` (ID `60081628315`) — console confirms **data center: IN (India)** directly (`console.catalyst.zoho.in`, project timezone `Asia/Kolkata`), no more guessing.
- **Project:** `Scenepaper` (ID `59024000000013054`), Development environment.
- **`catalyst-agent`'s worktree** (`../scenepaper-catalyst`, `feature/catalyst-backend`) is now a real initialized Catalyst app directory (`.catalystrc`, `catalyst.json`) — a genuine head start on issue #8, not just planning.
- **`scenepaper_pipeline`** — a real Advanced I/O function (Python 3.9), deployed and registered (function ID `59024000000018001`). Currently a "hello world" scaffold; real pipeline logic still to be written.
- **`scenepaper_job_test`** — a Job-type function scaffold, created to inspect the real code template (see issue #2 above). Not deployed; a good literal starting point for the async pipeline job once Phase 2 logic is ready.
- **Real bug found and fixed in Catalyst's own scaffold tooling:** `catalyst functions:add --type aio --stack python_3_9` defaults `requirements.txt` to `zcatalyst-sdk==1.4.0`, which **requires Python ≥3.10** — incompatible with the very Python 3.9 stack the scaffold itself targets. Deployment fails outright until pinned down to `zcatalyst-sdk==1.3.0` (the latest version that still supports 3.9, confirmed via `pip3.9 index versions`). **Remember this for every future function scaffold** — don't trust the default `requirements.txt`.
- **Local environment fix:** Python 3.9 wasn't installed on this Mac at all (`brew install python@3.9`, then `catalyst config:set python3_9.bin=/opt/homebrew/bin/python3.9`) — needed for any local deploy/build of a Python function, not optional tooling.

## Catalyst CLI

Installed session 2 (`zcatalyst-cli` v1.27.0 via `npm install -g`), **logged in this session** (`catalyst login` — interactive, needed a real terminal; piped/non-interactive input crashes its arrow-key prompts). Full command reference reviewed earlier — key notes: Advanced I/O functions can only be tested locally via `serve`, not `functions:shell` (that command explicitly excludes Advanced I/O functions). Valid Catalyst data centers, per the `--dc` flag: `us`, `eu`, `in`, `jp`, `sa`, `au`, `ca` (narrower than PlatformAI's 12-DC list — no uk/uae/cn/inec/sg on Catalyst itself). `catalyst init`'s feature-selection and function-type wizards are both arrow-key `inquirer`-style prompts that don't survive piped stdin — `catalyst functions:add --name <n> --type <bio|aio|event|cron|browserlogic|job|integ> --stack <stack>` has full non-interactive flags and is the reliable path instead.

Also connected this session: **the Zoho Catalyst MCP server** (150+ tools covering Data Store CRUD, Functions, Job Pools/Jobs, API Gateway, File Store, QuickML, and more) — used directly to inspect and modify the real project rather than requiring console clicks. Its one confirmed gap: no NoSQL-specific tools (see issue #1 above).

## Operational risks and known issues (2026-08-10)

### /ideate timing risk — NOT yet fixed
Live measurement: `POST /ideate` takes **25.2 seconds** end-to-end against the Advanced I/O function's hard 30-second cap. That leaves under 5 seconds of headroom and the endpoint will intermittently time out.

**Correct fix:** move ideation into its own Job function (same async-polling pattern as `/generate`), keeping the Advanced I/O front door well under 30s.  
**Do not:** trim search quality or skip clustering steps to buy time — that would undermine the verification moat.  
Do not attempt this during the current sprint unless everything else is done; tracked as a known risk.

### SEARXNG_BASE_URL in Catalyst Cache is an ngrok tunnel URL
The `SEARXNG_BASE_URL` key in the `ScenePaper` Cache segment currently holds an ngrok tunnel URL. ngrok tunnels die when the tunnel process stops or the session restarts. If `/ideate` starts failing with no apparent code change, this is the first thing to check — refresh the Cache value to the new tunnel URL.

Long-term fix: self-host SearXNG at a stable URL (see Issue #21 / SearXNG hosting note in Service Mapping below).

### Vendored backend/ sync coupling
Both `functions/scenepaper_pipeline/backend/` and `functions/scenepaper_pipeline_job/backend/` are vendored copies of `scenepaper-api/src/backend/`. They must stay in sync manually — Catalyst function archives are self-contained zips, so they include their own copies of the shared code.

As of 2026-08-10 the vendored copies are **ahead** of `scenepaper-api/src/backend/`: the 5xx transient retry logic in `gemini_client.py` and the full `ideation.py` exist in the vendored copies but have not yet landed on `scenepaper-api`'s `main`. Those changes need to be pushed to `scenepaper-api` or the vendored copy becomes the authoritative source, which is backwards.

**Rule:** whenever a file under `functions/*/backend/` is changed, the corresponding file under `scenepaper-api/src/backend/` must be updated in the same commit (or in a same-session follow-up commit to `scenepaper-api`). Check for divergence before each new feature sprint.

## Service mapping (per CLAUDE.md, restated here for tracking)

- **NoSQL** — the `ScenePaper` and `UserProfile` tables. Decided over Data Store, see above. Still needs direct console verification (issue #1) — neither the CLI nor the MCP expose it.
- **Advanced I/O Function (Python)** — orchestrates the front door of the pipeline; hands off the actual long-running work to a **Job function** (see issue #2). Capped at Python 3.9 — verify any library choice against this before adding it, and pin `zcatalyst-sdk` to `1.3.0` specifically, not latest.
- **File Store** — intended to serve generated audio/image files. Not yet confirmed working.
- **Auth** — explicitly out of scope for the hackathon unless there's real slack. Noted here as "not implemented, out of scope" rather than left silently missing.
- **SearXNG hosting** (issue #21, session-2 addendum) — search stack changed from Wikipedia/news-API to **self-hosted SearXNG** (metasearch). "Self-hosted" was assumed in the other planning conversation but *where* was never pinned down. Docker isn't installed in this environment, so the default self-host path isn't available as-is. Options to weigh: install Docker, a non-Docker manual SearXNG install, a small always-on hosted instance, or (lowest-effort, lowest-control) a public SearXNG instance. Blocks all of Phase 2's search work until resolved. Not touched this session — still exactly as open as before.
