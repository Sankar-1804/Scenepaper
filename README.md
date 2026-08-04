# ScenePaper

A tool for short-form content creators (YouTube Shorts, Instagram Reels) that replaces
hours of story research and structuring with a real, source-verified story, pre-structured
into a "scene paper" — hooks, scene-by-scene pacing, delivery notes, and a full source
list — plus a generated voiceover and matched images.

Built for a 4-day internal Zoho AI hackathon. Also the foundation of an ongoing product —
see `ai-docs/` and `docs/` for the fuller context behind the design decisions.

## The goal

Give a creator a topic. Get back a real, verifiable story that's already broken into
hooks, scenes, pacing, and delivery notes — ready to record, not just a script to edit.
The research and structuring work that normally takes hours happens before the creator
ever opens the tool.

## What it does

1. You give it a topic.
2. It searches for a handful of real, verifiable candidate stories and shows you a
   one-liner for each.
3. You pick one.
4. It generates a full scene paper: multiple hook options, a scene-by-scene structure
   with pacing tags (`FAST` / `BUILD` / `SLOW` / `WARM`), delivery notes, a CTA, and
   the verified sources behind it.
5. It generates a voiceover reading the story, and pulls real images matched to each
   scene.
6. Usage is tracked per profile, with generation and export gated by a lightweight
   access-limit system — implemented for this build without a live payment processor.

## Why this isn't "just another AI script generator"

Every competitor in this space generates a script from a prompt. ScenePaper doesn't —
every story is pulled from a real, checkable source and gated by verification before
it's structured. The differentiator is the curated, verified story pipeline and the
fixed output format, not the generation step itself.

## Stack

- **Backend:** Python, on Zoho Catalyst (Advanced I/O Functions + DataStore + File Store)
- **AI:** Claude (Enterprise) as primary dev tool; Sahaa for small/low-risk
  implementation tasks — see `ai-docs/token-log.md` for the actual split
- **TTS:** [Voicebox](https://voicebox.sh) — local, open-source voice generation
- **Images:** Pexels/Unsplash API (real stock photos, not AI-generated)
- **Frontend:** Web (primary), SwiftUI mobile client (stretch)
- **MCP:** ScenePaper ships its own MCP server — see `docs/mcp-notes.md` for the
  exposed tools

## Repo layout

```
CLAUDE.md              # full project context for any Claude Code session
README.md              # this file
ai-docs/                # prompt/spec files, product context, token usage log
docs/                   # API notes, Catalyst notes, MCP notes, GitHub workflow plan
agents/                 # custom agent configs used during development
src/                     # application code
```

## Running it locally

_Fill in once the pipeline is working — placeholder during Day 1 build:_

```bash
# Backend
cd src/backend
pip install -r requirements.txt --break-system-packages
# Catalyst CLI deploy / local dev server command goes here

# Web frontend
cd src/web
npm install
npm run dev
```

Environment variables needed (see `.env.example`, never commit the real `.env`):
- LLM API key (structuring calls)
- Pexels/Unsplash API key (images)
- Any Catalyst project credentials

## Demoing it (Day 2 / Day 4 walkthrough)

1. Enter a topic on the web client.
2. Pick one of the 3–4 verified candidate stories shown.
3. Watch the scene paper generate live — hooks, scenes, pacing tags, sources.
4. Play the generated voiceover.
5. Show the MCP server being called directly (`get_scene_paper`, `search_story_ideas`)
   to prove the pipeline works headless, not just through the UI.
6. Show the usage-limit indicator to demonstrate the access-gating logic.

## Development workflow

This repo uses `git worktree` — one worktree per agent's scope, so multiple Claude
Code sessions can run in parallel without branch-switching conflicts. Full setup,
worktree-to-agent mapping, and the GitHub Issues/Actions plan are in
`docs/github-workflow.md`.

## Hackathon deliverables checklist

- [ ] CRUD app — full C/R/U/D on `ScenePaper` demoed live
- [ ] API integration — documented in `docs/api-notes.md`
- [ ] Catalyst integration — DataStore, Advanced I/O Functions, File Store
- [ ] Custom agent(s) — in `agents/`, roles documented
- [ ] MCP connection — used during dev and shipped as part of the product
- [ ] AI markdowns — `ai-docs/`
- [ ] Token/model usage — `ai-docs/token-log.md`
- [ ] Skills used/created — documented, see `docs/`
- [ ] Git pushed, README explains run/demo steps