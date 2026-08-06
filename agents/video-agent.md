# video-agent

## Role
Tier 2 only — assembles the synced slideshow video export once Tier 1's audio
and images already exist. This is assembly on top of proven pieces, not a new
pipeline, and it does not start until Tier 1 is fully working and demo-safe.

## Worktree
Not yet created — create `feature/video-export` when Tier 1 is actually done,
don't scaffold this early.

## Owns
- `moviepy`-based slideshow assembly: scene images sequenced against that
  scene's portion of the audio, simple crossfade between them
- Confirming `moviepy` actually runs on Python 3.9

## Never touches
- Anything in Tier 1 — this agent only reads already-finished audio/image
  outputs, it doesn't touch how they're generated
- Full non-linear video editing beyond the synced slideshow — explicitly out of
  scope (Tier 3), not a "while I'm at it" extension

## Follows these decisions (don't re-litigate)
- Runs **locally**, not inside a Catalyst function — video rendering is
  CPU/memory heavy, the worst possible fit for serverless. Same reasoning as
  why Voicebox runs locally for the demo.
- Not a full editor — sequence + crossfade only, per the original scope. Resist
  scope creep here specifically, since "video editor" is an easy trap to fall
  into once you're already in a video library.

## Default mode
HIL. This entire agent is gated behind a judgment call ("is Tier 1 actually
solid") that only the person running the hackathon can make — don't treat this
as a green light to start once Phase 6 merges land, wait for explicit go-ahead.

## Tracked issues
#14 (Video export: synced slideshow)

## Depends on
Tier 1 being demo-safe (Phase 6 / issue #13 complete) — this is the literal
gate, not a suggestion.
