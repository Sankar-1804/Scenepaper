/**
 * mockApi.js
 * ----------
 * SINGLE SWAP POINT for connecting this UI to the real backend.
 *
 * app.js talks to the app ONLY through the functions exported at the bottom
 * of this file. It never fetches anything itself and doesn't know or care
 * whether the data is mocked or real, per agents/ui-agent.md ("Never
 * touches: any backend/API logic").
 *
 * Being rebuilt screen by screen alongside app.js (see CLAUDE.md's agent
 * loop). Scene paper generation, usage-gate mutation, etc. get added here
 * when those screens are specced.
 *
 * TO SWAP IN THE REAL API LATER:
 *   1. Flip USE_MOCK_DATA to false below.
 *   2. Fill in the fetch() calls in the "real" branch of each function.
 *   3. Nothing in app.js needs to change — it already awaits these functions
 *      and renders whatever shape comes back.
 */

const USE_MOCK_DATA = true; // <-- flip this when the real backend is live

// ?searchfailed=1 forces every searchCandidates() call to reject, so the
// Screen 2 failed-state can be reviewed/demoed without code changes.
const SIMULATE_SEARCH_FAILURE = new URLSearchParams(window.location.search).has(
  "searchfailed"
);

function withLatency(value, ms = 400) {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

// UserProfile is lightweight/effectively single-user for the hackathon demo.
const sessionState = {
  scenepapers_generated_count: 3,
  free_limit: 10,
};

/**
 * getUsageStatus() -> Promise<{ scenepapers_generated_count, free_limit }>
 * Mirrors the MCP tool get_usage_status(user_id).
 */
async function getUsageStatus() {
  if (USE_MOCK_DATA) {
    return withLatency({ ...sessionState });
  }
  // --- real API swap point ---
  // const res = await fetch(`/api/usage-status`);
  // if (!res.ok) throw new Error(`usage-status failed: ${res.status}`);
  // return res.json();
  throw new Error("Real API not wired up yet — set USE_MOCK_DATA = true.");
}

// ---------------------------------------------------------------------------
// searchCandidates — Screen 2 (candidate selection)
// ---------------------------------------------------------------------------
//
// Mirrors the MCP tool search_story_ideas(topic) / POST /ideate, extended
// with the addendum's "show me more" contract: the caller passes back
// excludeAngleTypes (the growing already_surfaced[...] context) each round,
// and an optional hint for "narrow it down". This mock has no real search
// to run, so it returns canned rounds keyed off how much exclusion context
// has accumulated — round 1 (no exclusions), round 2 (some — deliberately
// returns only 2 surfaced candidates, to exercise the "fewer than 3 passed
// the suppression floor" state), then exhausted. A hint always gets a fresh
// round 1 shape, since narrowing changes the search space rather than
// continuing to exhaust the old one.

function buildCandidate(overrides) {
  return {
    candidate_id: overrides.candidate_id,
    one_liner: overrides.one_liner,
    score: overrides.score,
    score_tag: overrides.score_tag,
    flags: overrides.flags || [],
    source_count: overrides.source_count,
    angle_type: overrides.angle_type,
    era: overrides.era,
  };
}

function buildSuppressed(overrides) {
  return { ...buildCandidate(overrides), suppression_reason: overrides.suppression_reason };
}

function round1Candidates(t) {
  return [
    buildCandidate({
      candidate_id: "cand_r1_1",
      one_liner: `The well-documented turning point in the story of ${t} that most retellings skip.`,
      score: 8,
      score_tag: "Primary-sourced",
      flags: [],
      source_count: 3,
      angle_type: "vindication",
      era: "2013",
    }),
    buildCandidate({
      candidate_id: "cand_r1_2",
      one_liner: `The decision around ${t} that looked reckless in the moment and cautionary in hindsight.`,
      score: 6,
      score_tag: "Corroborated",
      flags: ["single source only"],
      source_count: 1,
      angle_type: "cautionary",
      era: "2018",
    }),
    buildCandidate({
      candidate_id: "cand_r1_3",
      one_liner: `The underdog angle on ${t} that only shows up in primary interviews, not the popular version.`,
      score: 4,
      score_tag: "Needs checking",
      flags: ["claim not found in primary sources"],
      source_count: 2,
      angle_type: "underdog",
      era: "2011–2013",
    }),
  ];
}

function round1Suppressed(t) {
  return [
    buildSuppressed({
      candidate_id: "cand_r1_sup",
      one_liner: `A widely-repeated claim about ${t} that traces back to a single blog post with no primary source.`,
      score: 1,
      score_tag: "Fabrication risk",
      flags: ["unverified origin", "sources conflict"],
      source_count: 1,
      angle_type: "untold",
      era: "2021",
      suppression_reason:
        "Traces to an anonymous post with no verifiable original source, and contradicts documented primary records. Not selectable — shown only for transparency.",
    }),
  ];
}

function round2Candidates(t) {
  return [
    buildCandidate({
      candidate_id: "cand_r2_1",
      one_liner: `The pivot in ${t}'s story that reads as lucky in retrospect but wasn't treated that way at the time.`,
      score: 7,
      score_tag: "Corroborated",
      flags: [],
      source_count: 2,
      angle_type: "pivot",
      era: "2016",
    }),
    buildCandidate({
      candidate_id: "cand_r2_2",
      one_liner: `What ${t} gave up to get here — a sacrifice angle most coverage leaves out.`,
      score: 5,
      score_tag: "Needs checking",
      flags: ["single source only"],
      source_count: 1,
      angle_type: "sacrifice",
      era: "2019",
    }),
  ];
}

function round2Suppressed(t) {
  return [
    buildSuppressed({
      candidate_id: "cand_r2_sup",
      one_liner: `A "lucky break" version of ${t}'s story that conflicts with the documented timeline.`,
      score: 2,
      score_tag: "Fabrication risk",
      flags: ["sources conflict"],
      source_count: 1,
      angle_type: "lucky-break",
      era: "2017",
      suppression_reason:
        "The dates in this version conflict with the primary timeline corroborated elsewhere. Shown only for transparency.",
    }),
  ];
}

function hintCandidates(t, hint) {
  return [
    buildCandidate({
      candidate_id: "cand_hint_1",
      one_liner: `Focused on "${hint}": the ${t} episode that best fits that angle, primary-sourced.`,
      score: 8,
      score_tag: "Primary-sourced",
      flags: [],
      source_count: 3,
      angle_type: "rejection",
      era: "2014",
    }),
    buildCandidate({
      candidate_id: "cand_hint_2",
      one_liner: `A second telling of ${t} through the "${hint}" lens, corroborated but thinner.`,
      score: 6,
      score_tag: "Corroborated",
      flags: ["single source only"],
      source_count: 1,
      angle_type: "comeback",
      era: "2015",
    }),
    buildCandidate({
      candidate_id: "cand_hint_3",
      one_liner: `A less-covered ${t} moment that fits "${hint}" but still needs a closer look.`,
      score: 4,
      score_tag: "Needs checking",
      flags: ["claim not found in primary sources"],
      source_count: 1,
      angle_type: "underdog",
      era: "2020",
    }),
  ];
}

/**
 * searchCandidates({ topic, hint, excludeAngleTypes }) ->
 *   Promise<{ topic, axis, candidates[], suppressed[] }>
 *   | Promise<{ topic, exhausted: true, message }>
 *
 * axis is "events" (Axis 1 — distinct documented events) or "framings"
 * (Axis 2 — different tellings of one event), per the addendum's
 * discovery-step decision. This mock always returns "events" — the real
 * discovery step (cluster-by-event, count distinct events) lives in
 * api-integration-agent's territory.
 */
async function searchCandidates({ topic, hint = null, excludeAngleTypes = [] }) {
  const t = topic && topic.trim() ? topic.trim() : "this topic";

  if (USE_MOCK_DATA) {
    if (SIMULATE_SEARCH_FAILURE) {
      await withLatency(null, 500);
      throw new Error("search backend unreachable");
    }

    if (hint) {
      return withLatency({
        topic: t,
        axis: "events",
        candidates: hintCandidates(t, hint),
        suppressed: [],
      });
    }

    if (excludeAngleTypes.length === 0) {
      return withLatency({
        topic: t,
        axis: "events",
        candidates: round1Candidates(t),
        suppressed: round1Suppressed(t),
      });
    }

    if (excludeAngleTypes.length < 4) {
      return withLatency({
        topic: t,
        axis: "events",
        candidates: round2Candidates(t),
        suppressed: round2Suppressed(t),
      });
    }

    return withLatency({
      topic: t,
      exhausted: true,
      message: `I've covered the strong angles here for "${t}" — want to broaden the topic or try a different framing instead?`,
    });
  }
  // --- real API swap point ---
  // const res = await fetch(`/api/ideate`, {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({ topic, hint, exclude_angle_types: excludeAngleTypes }),
  // });
  // if (!res.ok) throw new Error(`ideate failed: ${res.status}`);
  // return res.json();
  throw new Error("Real API not wired up yet — set USE_MOCK_DATA = true.");
}

// ---------------------------------------------------------------------------
// generateScenePaper — Screens 3 & 4 (scene paper view, scene detail)
// ---------------------------------------------------------------------------
//
// Mirrors POST /generate (the two-call structuring pipeline: verification,
// then structuring — see CLAUDE.md's prompt-injection defense section).
//
// Schema note: hooks[].text is still the span-based [{text, verified}] array
// from the Screen 1 session (CLAUDE.md documents this). scenes[].script[].line
// is NOT — per the Screen 4 brief, it's a plain string, and the verified-vs-
// framing distinction for a scene lives instead in that scene's own claims[]
// (text, verified, sources[] when verified). This supersedes the span
// treatment for scene lines specifically; CLAUDE.md's schema comment for
// scenes[].script[].line should get reconciled to match. Two different
// mechanisms for the same rule (5) now exist in this one paper — hooks use
// inline spans, scenes use a separate claims list — flagging that as a real
// inconsistency worth resolving, not something I resolved unilaterally here.
//
// ?media=generating or ?media=failed force those media states for review;
// default is "ready" so the normal click-through demo shows the finished
// screen. There's no real audio pipeline here, so "ready" points at a small
// local mock voiceover file rather than faking a URL that would 404.
//
// image_set is always empty: per the design handoff, the image-matching
// pipeline isn't built, and Scene Detail must show that honestly rather
// than fake a photo — see app.js's renderSceneImage, which no longer has a
// "has an image" branch at all.

const FORCED_MEDIA_STATE = new URLSearchParams(window.location.search).get("media");

function span(text, verified) {
  return { text, verified };
}

async function generateScenePaper({ candidate, topic }) {
  if (USE_MOCK_DATA) {
    const mediaStatus = FORCED_MEDIA_STATE || "ready";
    const t = topic && topic.trim() ? topic.trim() : "this story";

    const paper = {
      id: `sp_${candidate.candidate_id || "mock"}`,
      paper_number: "041",
      title: `The untold turn behind ${t}`,
      category: "cautionary",
      dek: candidate.one_liner,
      verification_status: "verified",
      runtime_estimate: "57-63s",
      hook_window: "0-3s",
      peak_tension_window: "18-30s",
      payoff_window: "48-55s",
      hooks: [
        {
          label: "Hook A",
          type: "stat",
          text: [
            span("The number everyone remembers about this story is real.", true),
            span(" What's not in most retellings is what almost didn't happen.", false),
          ],
          best_for_note: "Best for a broad, general-interest audience",
        },
        {
          label: "Hook B",
          type: "cold-open",
          text: [
            span("It nearly ended before it started.", false),
            span(" Then one decision changed everything.", true),
          ],
          best_for_note: "Best for suspense-leaning audiences who want the reveal delayed",
        },
      ],
      scenes: [
        {
          scene_number: 1,
          scene_name: "The setup",
          pacing_tag: "WARM",
          time_range: "0-8s",
          script: [
            {
              speaker: "SPEAKER",
              line: "It starts ordinarily enough — nobody in the room expects what's coming.",
              direction: "Even, conversational. [pause 0.4s] Let the ordinariness sit before the turn.",
            },
          ],
          claims: [
            {
              text: "Nobody in the room expected what was coming.",
              verified: false,
            },
          ],
        },
        {
          scene_number: 2,
          scene_name: "The doubt",
          pacing_tag: "BUILD",
          time_range: "8-20s",
          script: [
            {
              speaker: "SPEAKER",
              line: "Then a detail surfaces that doesn't fit the popular version.",
              direction: "Pick up pace slightly. Let curiosity build, don't resolve it yet.",
            },
          ],
          claims: [
            {
              text: "A detail later emerged that contradicted the popular version of events.",
              verified: true,
              sources: [
                { title: "Follow-up interview with a person close to the events", date: "2014-02-02" },
              ],
            },
          ],
        },
        {
          scene_number: 3,
          scene_name: "The turn",
          pacing_tag: "FAST",
          time_range: "20-35s",
          script: [
            {
              speaker: "SPEAKER",
              line: "Three billion dollars. Cash. For an app that made almost no revenue.",
              direction:
                "Pick pace up from the previous scene — this is the pivot. [pause 0.3s] Land hard on the number.",
            },
            {
              speaker: "SPEAKER_1",
              line: "\"I told him he was throwing away the deal of a lifetime.\"",
              direction:
                "Read as a direct quote — a slightly different cadence from the narration. [pause 0.6s] before returning to SPEAKER.",
            },
            {
              speaker: "SPEAKER",
              line: "He said no anyway.",
              direction: "Full stop. Flat delivery — let the audience's own disbelief fill the gap. [pause 0.8s]",
            },
          ],
          claims: [
            {
              text: "Facebook offered $3 billion in cash for the acquisition in 2013.",
              verified: true,
              sources: [
                { title: "Contemporaneous wire-service report on the underlying event", date: "2013-11-13" },
                { title: "Follow-up interview with a person close to the events", date: "2014-02-02" },
              ],
            },
            {
              text: "An advisor told him he was throwing away the deal of a lifetime.",
              verified: false,
            },
          ],
        },
        {
          scene_number: 4,
          scene_name: "The payoff",
          pacing_tag: "SLOW",
          time_range: "35-52s",
          script: [
            {
              speaker: "SPEAKER",
              line:
                "The reframed takeaway, stated plainly — without overstating what the sources support.",
              direction: "Slow down, warm tone, direct eye line into the CTA. [pause 1.0s]",
            },
          ],
          claims: [
            {
              text: "The full context includes years of ups and downs the highlight-reel version leaves out.",
              verified: false,
            },
          ],
        },
      ],
      delivery_notes: [
        { label: "CTA", note: "Slow back down, warm tone, direct eye line." },
      ],
      cta_text: "Follow for more stories that actually happened — not just the retold version.",
      sources: [
        {
          title: "Contemporaneous wire-service report on the underlying event",
          type: "news",
          date: "2013-11-13",
          verified: true,
          confidence_score: 8,
          tag: "reliable primary",
          flags: [],
          suppressed: false,
          suppression_reason: null,
        },
        {
          title: "Follow-up interview with a person close to the events",
          type: "interview",
          date: "2014-02-02",
          verified: true,
          confidence_score: 6,
          tag: "credible secondary",
          flags: ["single source only"],
          suppressed: false,
          suppression_reason: null,
        },
        {
          title: "Retrospective piece repeating the claim without independent sourcing",
          type: "blog",
          date: "2019-06-04",
          verified: false,
          confidence_score: 3,
          tag: "thin sourcing",
          flags: ["claim not found in primary sources"],
          suppressed: false,
          suppression_reason: null,
        },
        {
          title: "Viral social post claiming an alternate, unverifiable version of events",
          type: "social",
          date: "2021-11-04",
          verified: false,
          confidence_score: 1,
          tag: "fabrication risk",
          flags: ["unverified origin", "sources conflict"],
          suppressed: true,
          suppression_reason:
            "No primary source repeats this claim; traces to a single unattributed retelling. Not used in structuring.",
        },
      ],
      voiceover_url: mediaStatus === "ready" ? "public/mock-voiceover.wav" : null,
      image_set: [], // matching pipeline isn't built — always honestly empty
      video_url: null,
      media_status: mediaStatus,
      export_status: "locked",
      created_at: new Date().toISOString(),
    };

    return withLatency(paper, 700);
  }
  // --- real API swap point ---
  // const res = await fetch(`/api/generate`, {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({ candidate_id: candidate.candidate_id }),
  // });
  // if (!res.ok) throw new Error(`generate failed: ${res.status}`);
  // return res.json();
  throw new Error("Real API not wired up yet — set USE_MOCK_DATA = true.");
}

// Exposed as a plain global object — no bundler/module step, per CLAUDE.md's
// "no framework, no build step beyond what's trivially necessary".
window.ScenePaperMockApi = {
  USE_MOCK_DATA,
  getUsageStatus,
  searchCandidates,
  generateScenePaper,
};
