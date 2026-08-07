# catalyst-agent — Plan (written 2026-08-07)

Written as part of a full plan-file pass across all 4 active agents before
simultaneous deployment. Read `CLAUDE.md`'s Agent Loop Strategy first — this
file is the PLAN step's output; ACT still means small reviewable diffs, and
step 5 (checkpoint before commit) is non-negotiable.

## Real current state (verified directly against code + git history, not
just docs/task-breakdown.md's checkboxes, which are stale)

- `functions/scenepaper_pipeline/main.py`: full routing skeleton for
  `POST /ideate`, `POST /generate`, `GET|PUT|DELETE /paper/:id`, real input
  validation, correct status codes. `POST /generate` genuinely submits a Job
  via `zcatalyst_sdk`'s `job_scheduling().job().submit_job(...)` against a
  **real deployed** Job Pool (`scenepaper_job_pool`, id
  `59024000000020001`) and Job function (`scenepaper_pipeline_job`, id
  `59024000000021001`) — done last commit (`20aac49`).
- `functions/scenepaper_pipeline_job/main.py`: real job-function skeleton
  (param validation, 5-stage walk, `context.close_with_success/failure`).
  All 5 stages are stubs pending api-integration-agent's work.
- `tests/test_scenepaper_pipeline_routes.py`: 19-check local harness with
  fake Request/job_request/context objects — doubles as the curl-harness
  deliverable from task-breakdown.
- **Issue #1 (NoSQL) is CLOSED as of `21ed1a0`** — this is more resolved
  than the stub comments in `main.py` currently admit. Real tables exist in
  console:
  - `ScenePaper` — partition key `id` (String), no sort key, secondary
    index `category_index` (partition key `category`, String)
  - `UserProfile` — partition key `id` (String), no sort key, no index
  - Nested fields (`hooks`, `scenes`, `sources`, `image_set`, etc.) are NOT
    pre-declared columns — written as part of the document body at insert
    time.
- **The stub comments in `main.py` (lines ~90-142) reference the wrong
  SDK surface** — they say `.datastore().table(...)`, which is the
  relational Data Store API. The real NoSQL runtime API is
  `zcatalyst_sdk`'s `nosql` module (confirmed installed,
  `zcatalyst-sdk==1.3.0`, path `zcatalyst_sdk/nosql/`) — this exists and
  works at the SDK level even though neither the Catalyst CLI nor the
  Catalyst MCP server expose NoSQL management (that gap is about
  managing tables/indexes declaratively, not about runtime read/write,
  which this SDK module handles directly against the tables already
  created in console).

## Work item 1 — Wire real NoSQL CRUD (UNBLOCKED, no hurdle remaining)

Replace `_stub_create_scenepaper` / `_stub_get_scenepaper` /
`_stub_update_scenepaper` / `_stub_delete_scenepaper` in
`functions/scenepaper_pipeline/main.py` with real calls. Tag: **afk** —
spec is fully defined, success is machine-checkable (existing test harness
already exercises found/not-found paths), doesn't touch another agent's
files.

Real SDK surface (verified by reading the installed package directly,
`zcatalyst_sdk/nosql/_table_items.py` + `zcatalyst_sdk/types/nosql.py`):

```python
app = zcatalyst_sdk.initialize()
table = app.nosql().get_table('ScenePaper')  # accepts name OR id directly

# create
result = table.insert_items({'item': {'id': paper_id, **payload}})

# get
result = table.fetch_item({'keys': [{'id': paper_id}]})

# update — NoSqlItemUpdateAttributeOperation shape below is read from the
# type stub but not yet exercised against a live call; verify
# `update_value`'s exact key (likely {'value': <val>}) with one real test
# call before trusting it blind:
result = table.update_items({
    'keys': {'id': paper_id},
    'update_attributes': [
        {'operation_type': 'PUT', 'attribute_path': [k], 'update_value': {'value': v}}
        for k, v in updates.items()
    ],
})

# delete
result = table.delete_items({'keys': {'id': paper_id}})
```

Steps:
1. Replace the 4 stub functions with real `table.*` calls per above.
2. Update the module docstring (lines ~1-33) and the stub-layer comment
   block (lines ~80-87) — they still say "issue #1 is not resolved yet,"
   which is now false and actively misleading to the next reader.
3. Extend `tests/test_scenepaper_pipeline_routes.py`'s fake objects (or add
   a `zcatalyst_sdk` mock) so the harness still runs without hitting a real
   Catalyst project — don't make the test suite require live credentials.
4. Do the same replacement for `UserProfile` wherever it's touched (check
   if any route currently stubs it — if not, note it as follow-up, don't
   invent new UserProfile routes not in scope).
5. Run the local harness (`python3.9 tests/test_scenepaper_pipeline_routes.py`
   — not pytest-discoverable, run directly, per the known gotcha) and
   confirm all checks still pass.
6. **Checkpoint** — present the diff before committing, per CLAUDE.md step
   5. Then commit referencing issue #1/#8, push to `feature/catalyst-backend`.

## Work item 2 — API Gateway route (BLOCKED on a manual console action)

The CLI has no route-creation command (`apig:enable/disable/status` only,
confirmed by reading `catalyst --help`), and the Catalyst MCP's
`Configure_API_Gateway_Route` tool rejects its own documented `target` enum
values (issue #3). This is a real tool bug, not a missing decision — the
route has to be created by hand in the console:

**Catalyst console → Scenepaper project → API Gateway → Add Route** →
target `scenepaper_pipeline` (Advanced I/O Function), a path (e.g.
`/generate`, or a catch-all covering all 5 routes above), methods
`GET/POST/PUT/DELETE`.

This is a **hil** item with no code for a fresh session to write — it's
listed here so the next session doesn't rediscover the CLI/MCP dead ends.
Once done: confirm the deployed `/generate` → Job Pool path works over a
real HTTP call (not just the local fake-object harness), and unblock
mcp-agent's issue #3 (same underlying gap).

## Work item 3 — Wire real pipeline stages in the Job function (BLOCKED on
api-integration-agent)

`functions/scenepaper_pipeline_job/main.py`'s 5 stages (search+verify,
structure, TTS, images, NoSQL write) are stubs. Do not start this until
api-integration-agent's plan.md items land (SearXNG hosting, Voicebox
verification, and — the biggest one — the Call A/Call B prompts, which are
`None` placeholders as of this writing). When ready, this item is: import
`src/backend/clients/*` and `src/backend/verification.py` into the job
function and replace each stage stub with a real call, using work item 1's
NoSQL wiring for the final write. Tag: **afk** once api-integration's
pieces exist and are tested, since the seam is already clean.

## Order for a fresh session executing this file

1. Work item 1 (fully unblocked, do this first).
2. Flag work item 2 to the user as a pending manual step (don't block on
   it — it's not something a session can do unattended).
3. Watch for api-integration-agent's plan.md items landing on `main`, then
   pick up work item 3.
