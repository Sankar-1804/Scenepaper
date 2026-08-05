/**
 * mockApi.js
 * ----------
 * SINGLE SWAP POINT for connecting this UI to the real backend.
 *
 * Every other file in src/web/ talks to the app ONLY through the functions
 * exported at the bottom of this file (searchStoryIdeas, generateScenePaper,
 * getUsageStatus, setExportUnlocked). None of them know or care whether the
 * data is mocked or real.
 *
 * Tonight (Phase 4, issue #11), the real Catalyst Advanced I/O Function does
 * not exist yet, so USE_MOCK_DATA is hardcoded true and every exported
 * function returns static mock JSON shaped exactly like the ScenePaper /
 * UserProfile entity schema in CLAUDE.md.
 *
 * TO SWAP IN THE REAL API LATER:
 *   1. Flip USE_MOCK_DATA to false below.
 *   2. Fill in the fetch() calls in the "real" branch of each function
 *      (endpoints per docs/api-notes.md / the Advanced I/O Function routes
 *      in docs/task-breakdown.md Phase 1: POST /ideate, POST /generate,
 *      GET /paper/:id, etc).
 *   3. Nothing in app.js needs to change — it already awaits these functions
 *      and renders whatever shape comes back.
 */

const USE_MOCK_DATA = true; // <-- flip this when the real backend is live

// Simulate real network latency so loading states are demoable, not instant.
function withLatency(value, ms = 650) {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

// ---------------------------------------------------------------------------
// Mock data — shaped to match CLAUDE.md's ScenePaper / UserProfile schema
// ---------------------------------------------------------------------------

// Candidates are ephemeral per CLAUDE.md — never persisted as their own
// entity. Scores/tags/flags mirror the two-signal trust model: a graded
// confidence score plus separate binary flags. All candidates are shown
// regardless of score (top 3-4, no silent suppression of low scorers).
function buildMockCandidates(topic) {
  const t = topic && topic.trim() ? topic.trim() : "this topic";
  return [
    {
      id: "cand_01",
      one_liner: `The well-documented turning point in the story of ${t} that most retellings skip.`,
      confidence_score: 8,
      tag: "well-documented",
      flags: [],
    },
    {
      id: "cand_02",
      one_liner: `A lesser-known ${t} figure whose role only shows up in primary interviews, not the popular version.`,
      confidence_score: 6,
      tag: "credible, less-covered",
      flags: ["single source only"],
    },
    {
      id: "cand_03",
      one_liner: `The failure-before-the-comeback angle on ${t} that's usually left out of the highlight-reel version.`,
      confidence_score: 7,
      tag: "solid secondary sourcing",
      flags: [],
    },
    {
      id: "cand_04",
      one_liner: `A widely-repeated claim about ${t} that traces back to a single blog post with no primary source.`,
      confidence_score: 3,
      tag: "thin sourcing",
      flags: ["claim not found in primary sources"],
    },
  ];
}

// One fully-fleshed-out ScenePaper template. generateScenePaper() clones this
// and merges in the picked candidate's title/category/dek so the detail view
// always reflects what the user actually picked, while still demoing every
// field in the real schema (including a suppressed source and a
// single-source-only flag, per issue #11's explicit requirement).
function buildMockScenePaper(candidate) {
  return {
    id: `sp_mock_${candidate.id}`,
    paper_number: "001",
    title: `The Untold Turn Behind ${candidate.id === "cand_01" ? "the Well-Known Version" : "This Story"}`,
    category: "curious", // enum: suspense / cautionary / human_interest / curious
    dek: candidate.one_liner,
    verification_status: "verified — see sources[] for per-source confidence and flags",
    runtime_estimate: "57-63s",
    hook_window: "0-3s",
    peak_tension_window: "20-35s",
    payoff_window: "48-55s",
    hooks: [
      {
        label: "Hook A",
        type: "question",
        text: "What if the version everyone tells... isn't the part that actually mattered?",
        best_for_note: "Best for viewers who respond to contrarian framing",
      },
      {
        label: "Hook B",
        type: "cold-open",
        text: "By the time anyone noticed, it had already changed everything.",
        best_for_note: "Best for suspense-leaning audiences",
      },
      {
        label: "Hook C",
        type: "stat",
        text: "Only a handful of people believed it would work. They were right.",
        best_for_note: "Best for underdog framing",
      },
    ],
    scenes: [
      {
        scene_number: 1,
        title: "The Setup",
        description: "Establish the ordinary version of events the audience already assumes is true.",
        pacing_tag: "WARM",
        time_range: "0-8s",
      },
      {
        scene_number: 2,
        title: "The Doubt",
        description: "Introduce the detail that doesn't fit the popular version — let it sit.",
        pacing_tag: "BUILD",
        time_range: "8-20s",
      },
      {
        scene_number: 3,
        title: "The Turn",
        description: "The verified fact that reframes everything the audience thought they knew.",
        pacing_tag: "FAST",
        time_range: "20-35s",
      },
      {
        scene_number: 4,
        title: "The Payoff",
        description: "Land the reframed takeaway plainly, without overstating what the sources support.",
        pacing_tag: "SLOW",
        time_range: "35-52s",
      },
    ],
    delivery_notes: [
      { label: "Scene 2", note: "Let the pause breathe here — don't rush past the doubt." },
      { label: "Scene 3", note: "Pick up pace noticeably; this is the pivot moment." },
      { label: "CTA", note: "Slow back down, warm tone, direct eye line." },
    ],
    cta_text: "Follow for more stories that actually happened — not just the retold version.",
    sources: [
      {
        title: "Original wire-service report on the underlying event",
        type: "news",
        date: "1998-03-12",
        verified: true,
        confidence_score: 8,
        tag: "reliable primary",
        flags: [],
        suppressed: false,
        suppression_reason: null,
      },
      {
        title: "Follow-up interview transcript with a direct participant",
        type: "interview",
        date: "1998-04-02",
        verified: true,
        confidence_score: 7,
        tag: "credible secondary",
        flags: ["single source only"],
        suppressed: false,
        suppression_reason: null,
      },
      {
        title: "Retrospective blog post repeating the claim without independent sourcing",
        type: "blog",
        date: "2015-06-19",
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
          "Traces back to an AI-generated content-farm article with no verifiable original source, and contradicts the primary wire report on key facts. Shown for transparency, per policy — suppressions are never hidden silently.",
      },
    ],
    voiceover_url: null, // Tier-1 voiceover pipeline not built yet — honestly null, not faked
    image_set: [], // image-matching pipeline not built yet — honestly empty, not faked
    video_url: null, // Tier-2 slideshow export — out of scope tonight
    media_status: "pending",
    export_status: "locked",
    created_at: new Date().toISOString(),
  };
}

// UserProfile is lightweight/effectively single-user for the hackathon demo.
const mockUserProfile = {
  id: "user_demo",
  about_me: "Creates true-story shorts for a general audience; medium pacing, avoids gore.",
  scenepapers_generated_count: 3,
  free_limit: 10,
};

// In-memory session state so the mock behaves consistently across actions
// within one page load (counter increments, export unlock toggle), without
// pretending to be a real persistence layer.
const sessionState = {
  scenepapers_generated_count: mockUserProfile.scenepapers_generated_count,
  free_limit: mockUserProfile.free_limit,
  papersById: {}, // id -> ScenePaper, tracks per-paper export_status toggles
};

// ---------------------------------------------------------------------------
// Exported API — this is the contract the rest of the app codes against
// ---------------------------------------------------------------------------

/**
 * searchStoryIdeas(topic) -> Promise<{ candidates: Candidate[] }>
 * Mirrors the MCP tool search_story_ideas(topic) / POST /ideate.
 */
async function searchStoryIdeas(topic) {
  if (USE_MOCK_DATA) {
    return withLatency({ candidates: buildMockCandidates(topic) });
  }
  // --- real API swap point ---
  // const res = await fetch(`/api/ideate?topic=${encodeURIComponent(topic)}`);
  // if (!res.ok) throw new Error(`ideate failed: ${res.status}`);
  // return res.json();
  throw new Error("Real API not wired up yet — set USE_MOCK_DATA = true.");
}

/**
 * generateScenePaper(candidate) -> Promise<ScenePaper>
 * Mirrors POST /generate (full structuring pipeline) once a candidate is picked.
 * Also applies the mocked free-tier counter, honestly reflecting CLAUDE.md's
 * "first 10 generations free, then paid" rule (mocked, no real charge).
 */
async function generateScenePaper(candidate) {
  if (USE_MOCK_DATA) {
    if (sessionState.scenepapers_generated_count >= sessionState.free_limit) {
      return withLatency({
        error: "FREE_LIMIT_REACHED",
        message:
          "Free generation limit reached (simulated for demo). In the real product this is where the paid gate would trigger — no real charge happens here.",
      });
    }
    const paper = buildMockScenePaper(candidate);
    sessionState.scenepapers_generated_count += 1;
    sessionState.papersById[paper.id] = paper;
    return withLatency(deepClone(paper), 900);
  }
  // --- real API swap point ---
  // const res = await fetch(`/api/generate`, {
  //   method: "POST",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({ candidate_id: candidate.id, source_url: candidate.source_url }),
  // });
  // if (!res.ok) throw new Error(`generate failed: ${res.status}`);
  // return res.json();
  throw new Error("Real API not wired up yet — set USE_MOCK_DATA = true.");
}

/**
 * getUsageStatus() -> Promise<{ scenepapers_generated_count, free_limit }>
 * Mirrors the MCP tool get_usage_status(user_id).
 */
async function getUsageStatus() {
  if (USE_MOCK_DATA) {
    return withLatency({
      scenepapers_generated_count: sessionState.scenepapers_generated_count,
      free_limit: sessionState.free_limit,
    }, 150);
  }
  // --- real API swap point ---
  // const res = await fetch(`/api/usage-status`);
  // if (!res.ok) throw new Error(`usage-status failed: ${res.status}`);
  // return res.json();
  throw new Error("Real API not wired up yet — set USE_MOCK_DATA = true.");
}

/**
 * setExportUnlocked(paperId, unlocked) -> Promise<{ export_status }>
 * Mocked, always-paid export gate toggle. No real payment gateway — this is
 * explicitly a simulated UI state per CLAUDE.md ("real 'Unlock' UI states,
 * no actual charge... label mocked actions honestly").
 */
async function setExportUnlocked(paperId, unlocked) {
  if (USE_MOCK_DATA) {
    const paper = sessionState.papersById[paperId];
    if (paper) {
      paper.export_status = unlocked ? "unlocked" : "locked";
    }
    return withLatency({ export_status: unlocked ? "unlocked" : "locked" }, 400);
  }
  // --- real API swap point ---
  // const res = await fetch(`/api/paper/${paperId}/export`, {
  //   method: "PUT",
  //   headers: { "Content-Type": "application/json" },
  //   body: JSON.stringify({ unlocked }),
  // });
  // if (!res.ok) throw new Error(`export toggle failed: ${res.status}`);
  // return res.json();
  throw new Error("Real API not wired up yet — set USE_MOCK_DATA = true.");
}

// Exposed as a plain global object — no bundler/module step, per CLAUDE.md's
// "no framework, no build step beyond what's trivially necessary".
window.ScenePaperMockApi = {
  USE_MOCK_DATA,
  searchStoryIdeas,
  generateScenePaper,
  getUsageStatus,
  setExportUnlocked,
};
