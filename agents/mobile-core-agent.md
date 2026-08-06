# mobile-core-agent

## Role
Tier 2 only — builds a shared Rust core (FFI bindings, e.g. via UniFFI) reused
by the iOS and Android clients, so both platforms share one implementation of
the request/response models and client logic against the ScenePaper API.

## Worktree
`feature/mobile-core` (`../scenepaper-mobile-core`)

## Owns
- The Rust core crate itself
- UniFFI (or equivalent) bindings generated for Swift and Kotlin
- Wiring the iOS app to the core; wiring the Android app to the core, if
  Android is attempted at all

## Never touches
- The web client — web renders the direct JSON response via plain JS, no Rust
  involved there at all, don't "help" by touching it
- Anything in Tier 1

## Follows these decisions (don't re-litigate)
- **Gated behind Tier 1 being fully working and demo-safe** — same rule as the
  rest of Tier 2. Don't start scaffolding the Rust toolchain while Tier 1 is
  still shaky, even if it feels like idle time.
- **iOS is committed, Android is the actual stretch.** Android integration is
  the first thing to drop if time runs short — don't treat both platforms as
  equally likely to ship.
- This was new scope added mid-hackathon specifically as a shared core, not a
  separate Rust server — no deployed service, just a library compiled into
  each app.

## Default mode
Rust core crate + bindings generation are AFK once Tier 1 is stable (mechanical
work against an already-frozen API contract). iOS integration is HIL (first
real test of the bindings actually working). Android integration is HIL and
explicitly optional.

## Tracked issues
#5 (Shared Rust core for iOS/Android)

## Depends on
Phase 6 (#13) complete and the API contract frozen — building against a
still-changing API wastes the whole point of a shared core.
