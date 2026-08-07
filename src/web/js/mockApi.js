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
 * loop). Screen 1 (Topic input) doesn't call anything here right now — the
 * usage counter moved to the future Settings screen, which is what
 * getUsageStatus() below is reserved for. Candidate search, scene paper
 * generation, etc. get added here when those screens are specced.
 *
 * TO SWAP IN THE REAL API LATER:
 *   1. Flip USE_MOCK_DATA to false below.
 *   2. Fill in the fetch() calls in the "real" branch of each function.
 *   3. Nothing in app.js needs to change — it already awaits these functions
 *      and renders whatever shape comes back.
 */

const USE_MOCK_DATA = true; // <-- flip this when the real backend is live

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
 * Mirrors the MCP tool get_usage_status(user_id). Not called by Screen 1
 * anymore (usage counter moved to the Settings screen, not yet built).
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

// Exposed as a plain global object — no bundler/module step, per CLAUDE.md's
// "no framework, no build step beyond what's trivially necessary".
window.ScenePaperMockApi = {
  USE_MOCK_DATA,
  getUsageStatus,
};
