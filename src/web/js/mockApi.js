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
 * The real backend is now live (see ai-docs/plan.md) — USE_MOCK_DATA
 * defaults to false. Flip it to true (or append ?mock=1) as demo insurance
 * if the backend is down; every mock code path below is still fully intact.
 */

// Base URL in one overridable place, per the plan — set
// window.SCENEPAPER_API_BASE_URL before this script loads to point
// elsewhere (e.g. a local dev backend) without editing this file.
const API_BASE_URL =
  window.SCENEPAPER_API_BASE_URL ||
  "https://scenepaper-60081628315.development.catalystserverless.in";

const params = new URLSearchParams(window.location.search);
const USE_MOCK_DATA = params.has("mock") || false; // <-- demo-insurance override

// ?searchfailed=1 / ?generatefailed=1 force those calls to reject even in
// mock mode, so the Screen 2 / progress failed-states can be reviewed
// without code changes.
const SIMULATE_SEARCH_FAILURE = params.has("searchfailed");
const SIMULATE_GENERATE_FAILURE = params.has("generatefailed");

function withLatency(value, ms = 400) {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

async function safeJson(res) {
  try {
    return await res.json();
  } catch {
    return null;
  }
}

// The backend's error envelope is consistently {status:"error", message}
// across 400/404/502/503 (see ai-docs/plan.md) — surface the real message
// instead of a generic "request failed".
function backendErrorMessage(body, status) {
  if (body && typeof body.message === "string" && body.message) return body.message;
  return `Request failed (HTTP ${status})`;
}

// The real /ideate response is missing several fields the UI expects
// (score_tag, source_count, angle_type, era, candidate_id) while
// api-integration-agent is still building it out, and confidence_score is
// currently always null. Normalize defensively so the UI renders an honest
// "not yet scored" state instead of crashing or lying with a fake band —
// per the plan, these fields "simply become good data" once the real
// pipeline lands, with no UI change needed then.
function normalizeCandidate(raw, index) {
  return {
    ...raw,
    candidate_id: raw.candidate_id || `cand_${index}`,
    score: raw.score ?? raw.confidence_score ?? null,
    score_tag: raw.score_tag ?? null,
    flags: raw.flags || [],
    source_count: raw.source_count ?? null,
    angle_type: raw.angle_type ?? null,
    era: raw.era ?? null,
  };
}

// UserProfile is lightweight/effectively single-user for the hackathon demo.
const sessionState = {
  scenepapers_generated_count: 3,
  free_limit: 10,
};

/**
 * getUsageStatus() -> Promise<{ scenepapers_generated_count, free_limit }>
 * Mirrors the MCP tool get_usage_status(user_id). There's no real
 * usage-status route in ai-docs/plan.md's backend table yet, so this stays
 * on local mock state regardless of USE_MOCK_DATA — not gated by the flag,
 * because there's nothing real to gate to.
 */
async function getUsageStatus() {
  // --- real API swap point (once a route exists) ---
  // const res = await fetch(`${API_BASE_URL}/usage-status`);
  // if (!res.ok) throw new Error(`usage-status failed: ${res.status}`);
  // return res.json();
  return withLatency({ ...sessionState });
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

  // Real backend. Only `topic` is in the documented /ideate contract right
  // now (see ai-docs/plan.md) — hint/exclude_angle_types are sent anyway as
  // forward-looking extras the backend can adopt later; harmless if ignored
  // today. There's no suppressed/axis/exhausted concept in the real
  // response yet, so those default to "nothing suppressed" / "events" /
  // "not exhausted" until api-integration-agent adds them.
  const res = await fetch(`${API_BASE_URL}/ideate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic: t, hint, exclude_angle_types: excludeAngleTypes }),
  });
  const body = await safeJson(res);
  if (!res.ok || (body && body.status === "error")) {
    throw new Error(backendErrorMessage(body, res.status));
  }
  return {
    topic: (body && body.topic) || t,
    axis: (body && body.axis) || "events",
    candidates: ((body && body.candidates) || []).map((c, i) => normalizeCandidate(c, i)),
    suppressed: (body && body.suppressed) || [],
  };
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

const FORCED_MEDIA_STATE = params.get("media");

function span(text, verified) {
  return { text, verified };
}

// In-memory store for mock-mode "generated" papers, keyed by the synthetic
// paper_id startGeneration() hands back — lets getPaper() honor the same
// start-then-poll contract the real backend uses, without actually needing
// multiple polls in mock mode.
const mockPapersById = new Map();

function buildMockPaper({ candidate, topic }) {
  const mediaStatus = FORCED_MEDIA_STATE || "ready";
  const t = topic && topic.trim() ? topic.trim() : "this story";

  return {
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
}

/**
 * startGeneration({ candidate, topic }) -> Promise<{ paper_id }>
 * Mirrors POST /generate. This is asynchronous on the real backend — it
 * returns as soon as the job is *accepted*, not once the paper exists.
 * getPaper() below is how the caller finds out when it's actually ready.
 */
async function startGeneration({ candidate, topic }) {
  if (USE_MOCK_DATA) {
    if (SIMULATE_GENERATE_FAILURE) {
      await withLatency(null, 500);
      throw new Error("generation backend unreachable");
    }
    const paperId = `mock_${Date.now()}_${Math.floor(Math.random() * 1e6)}`;
    mockPapersById.set(paperId, buildMockPaper({ candidate, topic }));
    await withLatency(null, 700); // same "it takes a moment" feel the old mock had
    return { paper_id: paperId };
  }

  const res = await fetch(`${API_BASE_URL}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ topic, candidate }),
  });
  const body = await safeJson(res);
  if (res.status !== 202) {
    throw new Error(backendErrorMessage(body, res.status));
  }
  return { paper_id: body && body.paper_id };
}

/**
 * getPaper(paperId) -> Promise<paper | null>
 * Mirrors GET /paper?id=<paper_id> — NOTE the query param, not a path
 * segment; the API Gateway rewrites each route to a fixed path and can't
 * carry a per-request id any other way (see ai-docs/plan.md).
 *
 * Resolves `null` while the paper doesn't exist yet (confirmed empirically:
 * the real backend returns 404 + {status:"error"} during generation, not
 * just once something has actually gone wrong) — the caller polls on that.
 * Throws for any other non-OK status, since those are real failures, not
 * "still working".
 */
async function getPaper(paperId) {
  if (USE_MOCK_DATA) {
    return mockPapersById.get(paperId) || null;
  }

  const res = await fetch(`${API_BASE_URL}/paper?id=${encodeURIComponent(paperId)}`);
  if (res.status === 404) return null;
  const body = await safeJson(res);
  if (!res.ok) {
    throw new Error(backendErrorMessage(body, res.status));
  }
  return body;
}

// Exposed as a plain global object — no bundler/module step, per CLAUDE.md's
// "no framework, no build step beyond what's trivially necessary".
window.ScenePaperMockApi = {
  USE_MOCK_DATA,
  getUsageStatus,
  searchCandidates,
  startGeneration,
  getPaper,
};
