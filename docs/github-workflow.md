# GitHub Workflow — ScenePaper

Goal: use git worktrees to run your existing parallel-Claude-Code habit cleanly,
and use Issues + Actions properly rather than as hackathon decoration. This doc
is the plan; commands are copy-pasteable.

## 1. Why worktrees fit how you already work

You already run multiple Claude Code sessions in parallel across projects. Normally
that means either multiple full clones (wasteful, they drift) or constant branch
switching in one directory (risky — stashing mid-session loses context). `git worktree`
solves this properly: one `.git` history, multiple checked-out directories, each on
its own branch, each safe to run an independent Claude Code session in at the same time.

## 2. Repo + worktree setup

This file itself belongs at `docs/github-workflow.md` in the repo once created —
place it there as part of the initial commit, alongside `CLAUDE.md` at repo root.

```bash
# One-time: init repo with the fixed layout
mkdir scenepaper && cd scenepaper
git init
mkdir -p ai-docs docs agents src .github/workflows

# Drop CLAUDE.md at repo root and this file at docs/github-workflow.md here,
# before the first commit, so both are tracked from the start:
#   cp /path/to/CLAUDE.md ./CLAUDE.md
#   cp /path/to/github-workflow.md ./docs/github-workflow.md

touch README.md
git add -A && git commit -m "chore: initial structure + CLAUDE.md + workflow docs"
git branch -M main
gh repo create scenepaper --private --source=. --push

# Create a worktree per agent scope. Each lives in a sibling directory,
# each is a real independent checkout on its own branch.
git worktree add ../scenepaper-catalyst -b feature/catalyst-backend
git worktree add ../scenepaper-api -b feature/api-integration
git worktree add ../scenepaper-ui -b feature/web-ui
git worktree add ../scenepaper-mcp -b feature/mcp-server
# Day 3 stretch only — create when Tier 1 is confirmed working, not before
git worktree add ../scenepaper-video -b feature/video-slideshow
```

Run a separate Claude Code session in each directory:

```bash
cd ../scenepaper-catalyst && claude   # catalyst-agent's session
cd ../scenepaper-api && claude        # api-integration-agent's session
```

`CLAUDE.md` lives at repo root and is shared across every worktree automatically
(same underlying repo), so every session starts with full project context without
you re-explaining anything.

**Merging back:** each worktree branch gets PR'd into `main` individually. Delete
the worktree once merged:

```bash
git worktree remove ../scenepaper-catalyst
```

**Suggested worktree-to-day mapping given your 4-day window:**
- Day 1: `feature/catalyst-backend` + `feature/api-integration` run in parallel
  (backend function + source/TTS/image calls can genuinely be built side by side
  since they touch different files)
- Day 1 evening / Day 2 morning: `feature/mcp-server` — built once the backend
  function is stable, wraps it
- Day 1–2: `feature/web-ui` in parallel once the API contract is frozen
- Day 3: a single `feature/panel-feedback` worktree — feedback work should NOT be
  parallelized, you want one coherent checkpointed thread here per the Day 3 rule
  in CLAUDE.md. `feature/video-slideshow` only opens if Tier 1 is fully working and
  demo-safe before Day 3 starts — otherwise it stays unopened and gets noted as
  roadmap in the Day 4 talk.

## 3. Issues — one per unit of work, not vibes

Create issues before starting each piece, not after. Suggested labels:
`day-1`, `day-2`, `day-3`, `tier-1`, `tier-2`, `agent:catalyst`, `agent:api`,
`agent:ui`, `agent:mcp`, `blocked`.

Seed issue list for Day 1 (create these first):

```
1. Set up Catalyst project + DataStore schema (ScenePaper + UserProfile)  [day-1, agent:catalyst]
2. Advanced I/O Function skeleton (Python) — routing + DataStore          [day-1, agent:catalyst]
3. Ideation search — 3-4 verified candidate one-liners per topic          [day-1, agent:api]
4. Structuring call — source → full rich schema (hooks/scenes/sources)   [day-1, agent:api]
5. TTS voiceover call, breath-point pauses (pacing-tag nuance = Tier 2)  [day-1, agent:api]
6. Stock image fetch (Pexels/Unsplash) per scene                         [day-1, agent:api]
7. Wire full pipeline end-to-end in the Function                          [day-1, tier-1]
8. Web client: topic → candidates → pick → view generated paper           [day-1, agent:ui]
9. Mocked paywall: 10-free counter + always-paid export toggle            [day-1, agent:ui]
10. MCP server wrapping the core tool calls incl. get_usage_status        [day-1, agent:mcp]
11. token-usage-logger skill                                              [day-1]
12. (Day 3 stretch) moviepy slideshow assembly, scene-timed crossfades   [day-3, agent:video, tier-2]
```

Day 2/3/4 issues get filed as you go — Day 3's issues specifically should be filed
live during/after the Day 2 showcase, each one tagged with the panel feedback it
came from, so the repo itself documents the feedback loop the guide asks for.

Use a GitHub Project board (Board view: Todo / In Progress / Done) with these
issues on it — gives you a visible artifact for the "what changed after feedback"
Day 4 talk, and it's genuinely useful for tracking parallel worktree work, not
just for show.

## 4. GitHub Actions — keep it small but real

Two workflows, both genuinely useful rather than padding:

**`.github/workflows/lint-test.yml`** — runs on every push, catches breakage before
you discover it live during a demo:

```yaml
name: Lint & Test
on: [push, pull_request]
jobs:
  python-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.9'   # matches Catalyst's supported version
      - run: pip install -r src/requirements.txt
      - run: pip install ruff pytest
      - run: ruff check src/
      - run: pytest src/tests/ || true   # remove `|| true` once tests exist
```

**`.github/workflows/docs-check.yml`** — a lightweight nudge tying directly back
to the hackathon's own documentation requirement, catches you forgetting to log
usage before a push:

```yaml
name: Docs freshness check
on: [push]
jobs:
  check-token-log:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 2
      - name: Warn if token-log wasn't updated
        run: |
          if ! git diff --name-only HEAD~1 HEAD | grep -q "ai-docs/token-log.md"; then
            echo "::warning::ai-docs/token-log.md wasn't updated in this push — remember to log usage."
          fi
```

Don't add a deploy-to-Catalyst Action for the hackathon — Catalyst deployment is
typically driven via its own CLI, and wiring CI/CD credentials into Actions under
time pressure is a real risk (secrets misconfig can silently break a demo). Deploy
manually during the hackathon; note "CI/CD to Catalyst" as a Day 4 "what I'd do
next" line — that reads as good judgment, not as a gap.

## 5. Commit convention

Reference the issue in every commit: `feat: wire TTS pacing marks (#5)`. Keeps
`git log` genuinely useful for `demo-script-builder` to pull from later.
