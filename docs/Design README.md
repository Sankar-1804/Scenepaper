# Handoff: ScenePaper UI (Nocturne, black variant)

## Overview
Full-flow UI for ScenePaper — a research/scripting tool for short-form video creators. Covers the entire core flow: Topic Input → Candidate Selection → Generation Progress → Scene Paper View → Scene Detail. The product's central idea: verification (scores, flags, verified-fact-vs-narrative-framing) is primary UI, not a badge — never de-emphasize it.

## About the design files
`ScenePaper.dc.html` in this folder is a **design reference built in HTML** (a Design Component prototype with inline styles and a small React-like logic class) — not production code to copy verbatim. It shows the intended look, content structure, and click-through behavior. The task is to **recreate this design in your actual codebase's stack** — this project's repo (`Sankar-1804/Scenepaper`) currently has a Python backend (Catalyst functions) and a plain HTML/CSS/JS frontend at `src/web/`. Recreate the screens below either in that same vanilla JS setup (matching `src/web/js/app.js`'s patterns) or in a framework of your choice if you're migrating — using your own components, not by embedding this file.

## Fidelity
**High-fidelity.** Colors, type, spacing, and copy below are final for this pass. Recreate pixel-close using your codebase's conventions; don't restyle from scratch.

## Design tokens

Ground is intentionally **true black** (a deliberate deviation from the Nocturne design system default, which normally avoids pure black):

- `--color-bg`: `#000000`
- `--color-surface`: `#141319`
- `--color-text`: `#e9e9ed`
- `--color-accent`: `#a394f0` (interactive, links, focus ring, SLOW pacing tag)
- `--color-accent-2`: `#b6abe8`
- `--color-divider`: `color-mix(in srgb, #e9e9ed 14%, transparent)`
- Neutral ramp 100–900 and accent ramp 100–900: see `_ds/nocturne-.../styles.css` (unchanged from Nocturne base — only bg/surface/accent/divider were overridden).

Semantic pacing / verification colors (all OKLCH, boosted chroma vs. stock Nocturne for a richer feel — apply consistently, these are semantic not decorative):
- **FAST** (danger/red): bg `oklch(26% 0.10 25)`, text `oklch(82% 0.17 25)`
- **BUILD** (warning/amber): bg `oklch(28% 0.09 70)`, text `oklch(84% 0.15 70)`
- **SLOW** (accent/purple): bg `var(--color-accent-800)`, text `var(--color-accent-100)`
- **WARM** (success/green): bg `oklch(26% 0.09 150)`, text `oklch(80% 0.15 150)`
- Verification score coloring uses the same three bands: ≥7 green, 4–6 amber, ≤3 red (same OKLCH values as above, text-only variants for large score numerals: `oklch(75% 0.17 150)` / `oklch(80% 0.15 70)` / `oklch(70% 0.19 25)`).

Typography: Inter, weight 400/500 only, sentence case everywhere (ALL CAPS only for small tracking-wide labels like section headers and card kickers). Spoken script lines use a serif (Georgia/Times New Roman fallback stack) at 22px/1.6 line-height — the single most readable text in the app. Monospace (`ui-monospace, Menlo, monospace`) is reserved for scene numbers, timestamps, speaker labels, and pause-token pills.

Radius: 8px (`--radius-md`) standard, 4px small, 14px large (dialogs). Icons: Phosphor, regular weight by default, filled weight for emphasis (checkmarks, play/pause, locks).

## Screens

### 1. Topic Input (home)
- Large centered column, max-width ~760px.
- Header: wordmark "ScenePaper" + a settings icon button, top nav bar, bottom border divider.
- Kicker "find a real story" (uppercase, tracked, muted) → H1 "What's the topic?" (36px) → one-line muted subhead about verifiable sourcing.
- Row: large text input (52px tall, 16px text) + primary button "Find stories" (magnifying-glass icon).
- Example chips below input: pill buttons, populate the input on click, don't submit — "Snapchat", "an underdog comeback", "Nokia", "a founder who almost gave up".
- Divider, then active creator-profile summary row (icon + one-liner + muted "Active creator profile" caption + ghost "Edit" button).
- Divider, then "recent searches" list (uppercase label + tappable rows with a history icon, re-runs search on click).
- Usage counter at the bottom, small and muted: "3 of 10 free scene papers used this month".

### 2. Candidate Selection
- Wide column (~980px). Topic echoed at top with an inline "edit" ghost button back to Topic Input.
- H2 "Pick a story to script" + a result-context line stating whether candidates are distinct events or distinct framings of one event.
- 3 candidate cards in a row (grid, 3 columns, 16px gap). Each card: one-liner (dominant, 15px, up to 2 lines) + large right-aligned semantically-colored score (`x/10`), a filled score-tag pill below matching the score's color band, flag pills (amber, warning icon) only when present, a divider, then muted meta row (source count with a document icon, left; angle type + era, right).
- Below cards: two secondary buttons, "Show me more" and "Narrow it down".
- Divider, then a "suppressed — filtered by the verification layer" section (muted uppercase label with an eye-slash icon): dashed-border cards, strikethrough one-liner, muted suppression-reason line with an X-circle icon. This section is togglable/dev-only in the real product but shown here for the demo.

### 3. Generation Progress
- Narrow column, generous top padding (empty/quiet page).
- Muted kicker "building your scene paper" + the picked candidate's one-liner (19px) at top so the user remembers their pick.
- Vertical step list, each row: 26px circular status icon (pending = dashed circle, active = spinning circle in accent, complete = filled accent checkmark) + label. Steps in order: Searching sources, Verifying claims, Structuring the scene paper, Generating voiceover, Matching images. Rows get a bottom divider. Auto-advances (~600ms/step in the prototype) then transitions to Scene Paper View.

### 4. Scene Paper View (single long scroll, no tabs/accordions)
Top to bottom:
1. Metadata line: "paper #014 · vindication" (muted, tracked) + a ghost "back to candidates" button, right-aligned.
2. H1 title (38px), then a 17px dek/summary line.
3. Verification badge row: a filled pill "8/10 · well-documented" (score-band colored, shield-check icon) + muted "4 verified sources" text with a files icon.
4. Compact full-width audio player card: icon play/pause button (primary), a thin progress track, elapsed/total time label.
5. "hooks — pick your opening" section header (h6, uppercase small). Two hook cards side by side: kicker "Hook A — curiosity gap" style label, italic serif hook text (17px), muted "best for" rationale beneath. Selected hook gets an inset accent ring + a filled checkmark icon in the corner. Selection persists.
6. "timing" section: 4 metric tiles in a grid (runtime, hook window, peak tension, payoff) — muted uppercase label above, 20px value below.
7. "scenes" section: a bordered list, one row per scene — mono scene number, scene name, mono time range, a pacing-tag pill (colored per the FAST/BUILD/SLOW/WARM legend above), and a chevron. Full script is never inlined here; clicking a row opens Scene Detail.
8. "verified sources" section: one row per source — green check icon, title, muted type+date right-aligned.
9. "export" section: a card showing locked state (lock icon, "Audio/video export — locked", muted honest note "Always-paid feature. Mocked in this prototype — no real charge.") + a secondary "Unlock (mock)" button.

### 5. Scene Detail
- Ghost "back to scene paper" button at top.
- Header row: mono scene number, pacing-tag pill, mono time range. Then H2 scene title (28px).
- Scene-level audio player (same compact pattern as paper view, plays just this scene).
- "script" section header with a right-aligned muted line count + speaker count.
- One block per script line: mono uppercase muted speaker label, then the line itself in serif at 22px/1.6 (largest, most readable text in the app), then the direction directly beneath in small muted text with a pencil icon — any `[pause Ns]` tokens inside the direction are pulled out and rendered as monospace pills (accent-tinted background), never left as literal bracket text and never inside the spoken line itself. Non-primary speakers (e.g. `SPEAKER_1` for direct quotes) get a left accent border + tinted background so a speaker change is structurally obvious at a glance.
- "claims in this scene" section: each claim in its own block. Verified claims: solid surface background, filled green check icon, label "verified fact", plain text, muted source+date beneath. Framing claims: dashed border, quote icon (muted, not colored), label "narrative framing", italic muted text, muted line reading "Not a sourced claim — ...". These two must never look alike.
- "scene image" section: dashed-border placeholder row (image icon in a small box + "Image not yet generated — matching pipeline pending" + a disabled "Swap" button) — honestly reflects that the image-matching pipeline isn't built yet; never fake an image.
- Bottom row: "previous scene" / "next scene" secondary buttons, disabled at the first/last scene respectively.

## Interactions & behavior
- All navigation is client-side state (a `screen` enum: input/candidates/progress/paper/detail) — no page reloads.
- Topic input: Enter key or the "Find stories" button submits and moves to Candidate Selection.
- Example chips and recent-search rows just populate/submit the topic field, they don't bypass the flow.
- Picking a candidate starts Generation Progress immediately, which auto-advances through 5 steps then lands on Scene Paper View.
- Hook selection is a simple click-to-select toggle between exactly 2 hook cards.
- Clicking any scene row opens Scene Detail for that scene index; prev/next buttons move between scenes; back button returns to Scene Paper View preserving scroll context.
- Transitions are a simple ~250ms fade/slide-up on screen mount; respect `prefers-reduced-motion` (disable the animation).
- No real audio/network — the audio player and generation progress are timed/mocked; label mocked actions honestly in copy exactly as shown (e.g. "Mocked in this prototype — no real charge").

## Content used (sample data — replace via your real ideate/generate pipeline, shape matches `src/web/js/mockApi.js` and `src/backend/verification.py`)
Sample topic used throughout: "Snapchat" / the 2013 Facebook $3B acquisition offer. 3 visible candidates + 1 suppressed candidate; one full scene paper with 2 hooks, 4 scenes (WARM → BUILD → FAST → SLOW pacing arc), 4 verified sources. Full text is in `ScenePaper.dc.html`.

## Assets
Phosphor icons (regular + fill weights), loaded via `unpkg.com/@phosphor-icons/web`. Inter typeface. No raster images/photos used — the scene-image slot is an honest placeholder.

## Files in this bundle
- `ScenePaper.dc.html` — the full design reference, all 5 screens, inline styles + a small state-driven logic class. View source for exact markup, colors, and copy.
- `nocturne-styles.css` — the base Nocturne design-system stylesheet this design builds on (component classes `.btn`, `.card`, `.tag`, `.input`, etc. — see the file for full token list; this design overrides `--color-bg`/`--color-surface`/`--color-accent`/`--color-divider` as noted above).
