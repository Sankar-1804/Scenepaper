/**
 * app.js
 * ------
 * Rendering + view logic only. Every piece of backend-shaped data comes from
 * window.ScenePaperMockApi (see mockApi.js) — this file never fetches
 * anything itself, per agents/ui-agent.md ("Never touches: any backend/API
 * logic — this agent renders whatever JSON the Python API returns").
 *
 * Screens: Topic input, Candidate selection, Generation progress, Scene
 * paper view, Scene detail. No framework, no build step, per CLAUDE.md.
 * There's no client-side router — every screen lives in this one page,
 * toggled via showView().
 *
 * Icons are inline SVG (not the design handoff's Phosphor-via-CDN) and type
 * stays on the system font stack (not Google Fonts Inter) — deliberate, so
 * the app has no network dependency for a live demo. See Design README.md
 * for the palette these colors come from.
 */

(function () {
  // Screen 2's suppressed-candidates section is a dev/demo-only transparency
  // aid (see CLAUDE.md's trust model) — flip this off for a production
  // build rather than deleting the section outright.
  const SHOW_SUPPRESSED_DEV_SECTION = true;

  const ICON_WARNING = `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 1.5 15 14H1L8 1.5Z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/><path d="M8 6.2v3.3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/><circle cx="8" cy="11.6" r="0.9" fill="currentColor"/></svg>`;
  const ICON_DOCUMENT = `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="3" y="1.5" width="10" height="13" rx="1.5" stroke="currentColor" stroke-width="1.3"/><path d="M5.5 5h5M5.5 8h5M5.5 11h3" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>`;
  const ICON_REFRESH = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M13.5 8A5.5 5.5 0 1 1 11.8 4" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/><path d="M13.5 2.5v3.5H10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const ICON_SLIDERS = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 4.5h12M2 8h12M2 11.5h12" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/><circle cx="6" cy="4.5" r="1.4" fill="var(--color-bg)" stroke="currentColor" stroke-width="1.2"/><circle cx="11" cy="8" r="1.4" fill="var(--color-bg)" stroke="currentColor" stroke-width="1.2"/><circle cx="5" cy="11.5" r="1.4" fill="var(--color-bg)" stroke="currentColor" stroke-width="1.2"/></svg>`;
  const ICON_EYE_SLASH = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M2 8s2.4-4.5 6-4.5S14 8 14 8s-2.4 4.5-6 4.5S2 8 2 8Z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/><circle cx="8" cy="8" r="1.8" stroke="currentColor" stroke-width="1.3"/><path d="M2.5 2.5l11 11" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>`;
  const ICON_X_CIRCLE = `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6.3" stroke="currentColor" stroke-width="1.3"/><path d="M6 6l4 4M10 6l-4 4" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg>`;
  const ICON_SHIELD_CHECK = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 1.5 13.5 3.5v4c0 4-2.4 6.2-5.5 7-3.1-0.8-5.5-3-5.5-7v-4L8 1.5Z" fill="currentColor" opacity="0.15" stroke="currentColor" stroke-width="1.2"/><path d="M5.5 8 7.3 9.8 10.5 6.2" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const ICON_LOCK = `<svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="3.5" y="7" width="9" height="6.5" rx="1.3" stroke="currentColor" stroke-width="1.3"/><path d="M5.3 7V5a2.7 2.7 0 0 1 5.4 0v2" stroke="currentColor" stroke-width="1.3"/></svg>`;
  const ICON_ARROW_LEFT = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M13 8H3M6.5 3.5 3 8l3.5 4.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const ICON_ARROW_RIGHT = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 8h10M9.5 3.5 13 8l-3.5 4.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const ICON_CIRCLE_DASHED = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.3" stroke-dasharray="2.4 2.4"/></svg>`;
  const ICON_CIRCLE_NOTCH = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M14 8A6 6 0 1 1 8 2" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>`;
  const ICON_CHECK_CIRCLE_FILL = `<svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true"><circle cx="8" cy="8" r="6.3" fill="currentColor"/><path d="M5.3 8.2 7.2 10 10.7 6" stroke="var(--color-bg)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  const els = {
    // Screen 1
    viewTopic: document.getElementById("view-topic"),
    form: document.getElementById("topic-form"),
    textarea: document.getElementById("topic-input"),
    fieldError: document.getElementById("topic-error"),
    settingsButton: document.getElementById("settings-button"),
    // Screen 2
    viewCandidates: document.getElementById("view-candidates"),
    topicRecapText: document.getElementById("topic-recap-text"),
    changeTopicButton: document.getElementById("change-topic-button"),
    candidatesUsage: document.getElementById("candidates-usage"),
    resultContext: document.getElementById("result-context"),
    searchProgress: document.getElementById("search-progress"),
    searchProgressIntro: document.getElementById("search-progress-intro"),
    searchElapsed: document.getElementById("search-elapsed"),
    searchProgressSteps: document.getElementById("search-progress-steps"),
    searchReassurance: document.getElementById("search-reassurance"),
    candidateList: document.getElementById("candidate-list"),
    candidateActions: document.getElementById("candidate-actions"),
    showMoreButton: document.getElementById("show-more-button"),
    narrowButton: document.getElementById("narrow-button"),
    narrowInputRow: document.getElementById("narrow-input-row"),
    narrowInput: document.getElementById("narrow-input"),
    narrowSubmit: document.getElementById("narrow-submit"),
    suppressedSection: document.getElementById("suppressed-dev-section"),
    suppressedHeader: document.getElementById("suppressed-header"),
    suppressedList: document.getElementById("suppressed-list"),
    // Generation progress
    viewProgress: document.getElementById("view-progress"),
    progressOneLiner: document.getElementById("progress-one-liner"),
    progressSteps: document.getElementById("progress-steps"),
    // Screen 3
    viewPaper: document.getElementById("view-paper"),
    backToCandidatesButton: document.getElementById("back-to-candidates-button"),
    paperNumber: document.getElementById("paper-number"),
    paperCategory: document.getElementById("paper-category"),
    paperTitle: document.getElementById("paper-title"),
    paperDek: document.getElementById("paper-dek"),
    verificationBadge: document.getElementById("verification-badge"),
    audioPlayer: document.getElementById("audio-player"),
    hookList: document.getElementById("hook-list"),
    timingGrid: document.getElementById("timing-grid"),
    sceneRows: document.getElementById("scene-rows"),
    sourceRows: document.getElementById("source-rows"),
    exportRow: document.getElementById("export-row"),
    // Screen 4
    viewScene: document.getElementById("view-scene"),
    sceneBackButton: document.getElementById("scene-back-button"),
    sceneNumberLabel: document.getElementById("scene-number-label"),
    scenePacingPillWrap: document.getElementById("scene-pacing-pill-wrap"),
    sceneTimeRange: document.getElementById("scene-time-range"),
    sceneTitleText: document.getElementById("scene-title-text"),
    sceneAudioPlayer: document.getElementById("scene-audio-player"),
    scriptMeta: document.getElementById("script-meta"),
    scriptLines: document.getElementById("script-lines"),
    claimsList: document.getElementById("claims-list"),
    sceneImageBlock: document.getElementById("scene-image-block"),
    scenePrevButton: document.getElementById("scene-prev-button"),
    sceneNextButton: document.getElementById("scene-next-button"),
  };

  // Static icon+text labels for buttons that never change their content —
  // set once here instead of re-rendered every time their screen paints.
  els.showMoreButton.innerHTML = `${ICON_REFRESH}Show me more`;
  els.narrowButton.innerHTML = `${ICON_SLIDERS}Narrow it down`;
  els.backToCandidatesButton.innerHTML = `${ICON_ARROW_LEFT}back to candidates`;
  els.sceneBackButton.innerHTML = `${ICON_ARROW_LEFT}back to scene paper`;
  els.scenePrevButton.innerHTML = `${ICON_ARROW_LEFT}previous scene`;
  els.sceneNextButton.innerHTML = `next scene${ICON_ARROW_RIGHT}`;

  // Screen 2 state — grows each round so mock/real search can avoid
  // resurfacing the same angles (the addendum's already_surfaced[...]).
  let currentTopic = "";
  let excludeAngleTypes = [];
  let lastSearchParams = null; // for the failed-state "try again" button

  function showView(name) {
    els.viewTopic.hidden = name !== "topic";
    els.viewCandidates.hidden = name !== "candidates";
    els.viewProgress.hidden = name !== "progress";
    els.viewPaper.hidden = name !== "paper";
    els.viewScene.hidden = name !== "scene";
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Shared by the search-progress list (Screen 2) and the generation-
  // progress list — same visual language for both real waits, per the
  // design note that they should feel like one product. `activeIndex` is
  // never claimed complete by the caller past what's actually known —
  // both callers stop advancing it once they run out of real information
  // and just hold the last step "active" for as long as it actually takes.
  function renderStepList(targetEl, steps, activeIndex) {
    targetEl.innerHTML = steps
      .map((step, i) => {
        let iconHtml = ICON_CIRCLE_DASHED;
        let iconClass = "";
        let labelClass = "";
        if (i < activeIndex) {
          iconHtml = ICON_CHECK_CIRCLE_FILL;
          iconClass = "is-complete";
          labelClass = "is-complete";
        } else if (i === activeIndex) {
          iconHtml = ICON_CIRCLE_NOTCH;
          iconClass = "is-active";
          labelClass = "is-current";
        }
        return `
          <div class="progress-step">
            <div class="progress-step-icon ${iconClass}">${iconHtml}</div>
            <div class="progress-step-label ${labelClass}">${escapeHtml(step.label)}</div>
          </div>
        `;
      })
      .join("");
  }

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  // ---- auto-growing textarea ----

  function autoGrow() {
    els.textarea.style.height = "auto";
    els.textarea.style.height = els.textarea.scrollHeight + "px";
  }

  els.textarea.addEventListener("input", () => {
    autoGrow();
    clearFieldError();
  });

  // ---- submit handling ----

  function clearFieldError() {
    els.fieldError.hidden = true;
    els.fieldError.textContent = "";
  }

  function showFieldError(message) {
    els.fieldError.hidden = false;
    els.fieldError.textContent = message;
  }

  async function submitTopic(topic) {
    const trimmed = (topic || "").trim();
    if (!trimmed) {
      showFieldError("Enter a topic to get started.");
      return;
    }
    clearFieldError();

    currentTopic = trimmed;
    excludeAngleTypes = [];
    els.topicRecapText.textContent = trimmed;
    els.narrowInputRow.hidden = true;
    els.narrowInput.value = "";

    showView("candidates");
    renderCandidatesUsage();
    runSearch({ topic: trimmed });
  }

  els.form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitTopic(els.textarea.value);
  });

  els.settingsButton.addEventListener("click", () => {
    console.info("[stub] settings screen not built yet");
  });

  // ==========================================================================
  // Screen 2: Candidate selection
  // ==========================================================================

  const api = window.ScenePaperMockApi;

  // Honest label reflecting which backend is actually live — this used to
  // hardcode "USE_MOCK_DATA = true", which silently went stale (and lied)
  // the moment the flag's default flipped to false.
  const dataSourceNoteEl = document.getElementById("data-source-note");
  dataSourceNoteEl.innerHTML = api.USE_MOCK_DATA
    ? `Mock data (<code>?mock=1</code>) — see <code>src/web/js/mockApi.js</code>.`
    : `Live backend — append <code>?mock=1</code> to force mock data.`;

  // "unscored" — not one of the real verification bands — is a genuine
  // state, not an error: the live /ideate endpoint currently returns
  // confidence_score: null for every candidate (api-integration-agent is
  // still wiring up real scoring). Falling through to "danger" would lie —
  // it'd paint an un-scored candidate the same red as a genuinely bad one.
  function scoreBand(score) {
    if (score === null || score === undefined) return "unscored";
    if (score >= 7) return "success";
    if (score >= 4) return "warning";
    return "danger";
  }

  function renderCandidateCard(c) {
    const band = scoreBand(c.score);
    const scoreHtml =
      band === "unscored"
        ? `<span class="candidate-score-unscored">not yet scored</span>`
        : `<span class="candidate-score-number">${escapeHtml(c.score)}</span><span class="candidate-score-max">/10</span>`;

    const metaParts = [];
    if (c.source_count !== null && c.source_count !== undefined) {
      metaParts.push(
        `<span class="meta-sources">${ICON_DOCUMENT}${c.source_count} source${c.source_count === 1 ? "" : "s"}</span>`
      );
    }
    const angleEra = [c.angle_type, c.era].filter(Boolean).join(" · ");
    if (angleEra) {
      metaParts.push(`<span class="meta-angle">${escapeHtml(angleEra)}</span>`);
    }

    return `
      <button type="button" class="candidate-card" data-candidate-id="${escapeHtml(c.candidate_id)}">
        <div class="candidate-card-main">
          <p class="candidate-one-liner">${escapeHtml(c.one_liner)}</p>
          <div class="candidate-score score-${band}">${scoreHtml}</div>
        </div>
        ${
          c.score_tag
            ? `<div class="candidate-pills">
                <span class="pill pill-score-tag score-${band}">${escapeHtml(c.score_tag)}</span>
              </div>`
            : ""
        }
        ${
          c.flags.length
            ? `<div class="candidate-pills">
                ${c.flags
                  .map((f) => `<span class="pill pill-flag">${ICON_WARNING}${escapeHtml(f)}</span>`)
                  .join("")}
              </div>`
            : ""
        }
        ${
          metaParts.length
            ? `<hr class="candidate-divider" /><div class="candidate-meta">${metaParts.join("")}</div>`
            : ""
        }
      </button>
    `;
  }

  function renderSuppressedCard(c) {
    return `
      <div class="suppressed-card">
        <p class="suppressed-one-liner">${escapeHtml(c.one_liner)}</p>
        <p class="suppressed-reason">${ICON_X_CIRCLE}<span>${escapeHtml(c.suppression_reason)}</span></p>
      </div>
    `;
  }

  function renderResultContext(count, axis, topic) {
    const plural = count === 1 ? "" : "s";
    if (axis === "framings") {
      els.resultContext.textContent = `${count} candidate${plural} — different framings of one event in ${topic}'s history.`;
    } else {
      els.resultContext.textContent = `${count} candidate${plural} — distinct events from ${topic}'s history.`;
    }
  }

  function setCandidatesBusy(isBusy) {
    els.showMoreButton.disabled = isBusy;
    els.narrowButton.disabled = isBusy;
    els.narrowSubmit.disabled = isBusy;
    els.candidateList
      .querySelectorAll(".candidate-card")
      .forEach((btn) => (btn.disabled = isBusy));
  }

  function changeTopic() {
    showView("topic");
    els.textarea.value = currentTopic;
    autoGrow();
    els.textarea.focus();
  }

  els.changeTopicButton.addEventListener("click", changeTopic);

  async function renderCandidatesUsage() {
    els.candidatesUsage.innerHTML = `<p class="usage-line">Loading usage…</p>`;
    try {
      const usage = await api.getUsageStatus();
      const remaining = Math.max(usage.free_limit - usage.scenepapers_generated_count, 0);
      const pct = Math.min(
        100,
        Math.round((usage.scenepapers_generated_count / usage.free_limit) * 100)
      );
      els.candidatesUsage.innerHTML = `
        <div class="usage-line">
          ${usage.scenepapers_generated_count} of ${usage.free_limit} free papers used (${remaining} left)
        </div>
        <div class="usage-bar" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100">
          <div class="usage-bar-fill" style="width:${pct}%"></div>
        </div>
      `;
    } catch (err) {
      els.candidatesUsage.innerHTML = `<p class="usage-line">Couldn't load usage status.</p>`;
    }
  }

  function renderExhausted(message) {
    els.resultContext.textContent = "";
    els.candidateList.innerHTML = `
      <div class="state-message">
        <p>${escapeHtml(message)}</p>
        <button type="button" class="secondary-button" id="exhausted-change-topic">Change topic</button>
      </div>
    `;
    document
      .getElementById("exhausted-change-topic")
      .addEventListener("click", changeTopic);
    els.candidateActions.hidden = true;
    els.narrowInputRow.hidden = true;
    els.suppressedSection.hidden = true;
  }

  // ---- search-progress: the "searching" state for /ideate ----
  //
  // /ideate is a single blocking call, typically 20-30s+, with no progress
  // events to subscribe to. So this does NOT fake a percentage or a live
  // source counter — both would be inventing data in a product whose whole
  // pitch is verification. What's real and shown instead: elapsed time
  // (always accurate) and the pipeline's known, fixed stage sequence
  // (classify -> build queries -> search SearXNG -> score domain quality ->
  // cluster -> summarize), paced against a measured TYPICAL duration —
  // there's no per-stage telemetry, so that pacing is an estimate. The last
  // stage never auto-completes on the timer; it just holds "active" for as
  // long as the real call actually takes, same pattern as the generation-
  // progress screen (and reusing its exact visual language, on purpose).

  const SEARCH_STAGES = [
    { label: "Understanding the request" },
    { label: "Building search queries" },
    { label: "Searching sources" },
    { label: "Ranking by source quality" },
    { label: "Grouping into distinct stories" },
    { label: "Writing candidate summaries" },
  ];

  // Rough midpoint of the measured range (broad topics ~25s, specific
  // subjects ~28s+) — paces the stage list only, never used to predict or
  // claim completion.
  const SEARCH_EXPECTED_DURATION_MS = 27000;
  const SEARCH_SLOW_AFTER_MS = 30000;
  const SEARCH_ELAPSED_TICK_MS = 500;
  // Fraction of SEARCH_EXPECTED_DURATION_MS elapsed at which each stage
  // after the first becomes active — one fewer entry than SEARCH_STAGES,
  // since the last stage has no threshold; it's just "whatever's left".
  const SEARCH_STAGE_THRESHOLDS = [0.05, 0.2, 0.6, 0.7, 0.85];

  function stageIndexForElapsed(elapsedMs) {
    const ratio = elapsedMs / SEARCH_EXPECTED_DURATION_MS;
    let idx = 0;
    for (const threshold of SEARCH_STAGE_THRESHOLDS) {
      if (ratio >= threshold) idx++;
    }
    return Math.min(idx, SEARCH_STAGES.length - 1);
  }

  function formatElapsedSeconds(ms) {
    return `${Math.floor(ms / 1000)}s`;
  }

  // So the result lands into an already-shaped layout instead of replacing
  // a plain message — CLAUDE.md's ScenePaper trust model always shows the
  // top 3 regardless of score, so 3 is the honest number to skeleton, not
  // a guess at "3-4".
  function renderCandidateSkeletons(count) {
    return Array.from(
      { length: count },
      () => `
        <div class="candidate-card candidate-card-skeleton" aria-hidden="true">
          <div class="skeleton-bar skeleton-bar-title"></div>
          <div class="skeleton-bar skeleton-bar-title skeleton-bar-title-short"></div>
          <div class="skeleton-bar skeleton-bar-pill"></div>
          <hr class="candidate-divider" />
          <div class="skeleton-bar skeleton-bar-meta"></div>
        </div>
      `
    ).join("");
  }

  // Starts the searching UI and returns a stop() to call once the real
  // response lands — success, exhaustion, or failure all call it.
  function startSearchProgress() {
    els.searchProgress.hidden = false;
    els.searchProgressIntro.textContent =
      "This usually takes 20–30 seconds — we're searching real sources, not generating from memory.";
    els.searchReassurance.hidden = true;
    els.candidateList.innerHTML = renderCandidateSkeletons(3);

    const startedAt = Date.now();
    let reassured = false;

    function tick() {
      const elapsedMs = Date.now() - startedAt;
      els.searchElapsed.textContent = formatElapsedSeconds(elapsedMs);
      renderStepList(els.searchProgressSteps, SEARCH_STAGES, stageIndexForElapsed(elapsedMs));

      if (!reassured && elapsedMs >= SEARCH_SLOW_AFTER_MS) {
        reassured = true;
        els.searchReassurance.hidden = false;
        els.searchReassurance.textContent =
          "This is taking longer than usual — some topics take longer to verify than others. Still working.";
      }
    }

    tick();
    const intervalId = setInterval(tick, SEARCH_ELAPSED_TICK_MS);

    return function stopSearchProgress() {
      clearInterval(intervalId);
      els.searchProgress.hidden = true;
    };
  }

  // A 408 EXECUTION_TIME_EXCEEDED is a known, understood condition (the
  // search backend's own 30s cap), not a generic failure — say so, and
  // give the actual workaround instead of a raw HTTP-status string.
  function renderSearchFailed(err) {
    els.resultContext.textContent = "";
    const isTimeout = err && (err.errorCode === "EXECUTION_TIME_EXCEEDED" || err.status === 408);
    const messageHtml = isTimeout
      ? `This search passed the server's 30-second limit and timed out. Specific, single-subject topics (like "Google") often take longer to verify than broad ones ("an underdog comeback") — try broadening the topic, or try again.`
      : `Something went wrong searching for candidates${err && err.message ? ` (${escapeHtml(err.message)})` : ""}.`;
    els.candidateList.innerHTML = `
      <div class="state-message">
        <p>${messageHtml}</p>
        <button type="button" class="secondary-button" id="retry-search-button">Try again</button>
      </div>
    `;
    document.getElementById("retry-search-button").addEventListener("click", () => {
      if (lastSearchParams) runSearch(lastSearchParams);
    });
    els.candidateActions.hidden = true;
    els.narrowInputRow.hidden = true;
    els.suppressedSection.hidden = true;
  }

  function renderCandidates(result) {
    const { candidates, suppressed, axis, topic } = result;
    renderResultContext(candidates.length, axis, topic);

    if (!candidates.length) {
      // Fewer than 3 (including zero) passed the suppression floor — show
      // what exists, don't pad with placeholders.
      els.candidateList.innerHTML = `
        <div class="state-message"><p>No candidates passed verification this round.</p></div>
      `;
    } else {
      els.candidateList.innerHTML = candidates.map(renderCandidateCard).join("");
      els.candidateList.querySelectorAll(".candidate-card").forEach((btn) => {
        btn.addEventListener("click", () => {
          const candidate = candidates.find((c) => c.candidate_id === btn.dataset.candidateId);
          // Ideation marks a candidate "thin sourcing" when the search results
          // were too sparse to summarise into a real story -- the one-liner
          // itself usually says so. Generating from one spends two Gemini
          // calls to produce a scene paper with nothing behind it, so confirm
          // first. Deliberately NOT hidden or disabled: CLAUDE.md's trust
          // model says low scorers stay visible, the creator just shouldn't
          // pick one by accident.
          const thin = (candidate.flags || []).some((f) =>
            String(f).toLowerCase().includes("thin")
          );
          if (thin) {
            const ok = window.confirm(
              "This story has thin sourcing — the search didn't find enough to " +
                "verify it properly, so the scene paper will be weak.\n\n" +
                "Generate anyway?"
            );
            if (!ok) return;
          }
          handlePickCandidate(candidate);
        });
      });
    }

    excludeAngleTypes = excludeAngleTypes.concat(candidates.map((c) => c.angle_type));

    els.candidateActions.hidden = false;

    if (SHOW_SUPPRESSED_DEV_SECTION && suppressed && suppressed.length) {
      els.suppressedSection.hidden = false;
      els.suppressedHeader.innerHTML = `${ICON_EYE_SLASH}<span class="section-label">suppressed — filtered by the verification layer</span>`;
      els.suppressedList.innerHTML = suppressed.map(renderSuppressedCard).join("");
    } else {
      els.suppressedSection.hidden = true;
    }
  }

  async function runSearch(params) {
    lastSearchParams = params;
    setCandidatesBusy(true);
    els.candidateActions.hidden = true;
    els.suppressedSection.hidden = true;
    els.resultContext.textContent = "";
    const stopSearchProgress = startSearchProgress();

    let result;
    try {
      result = await api.searchCandidates(params);
    } catch (err) {
      stopSearchProgress();
      renderSearchFailed(err);
      setCandidatesBusy(false);
      return;
    }
    stopSearchProgress();

    if (result.exhausted) {
      renderExhausted(result.message);
      setCandidatesBusy(false);
      return;
    }

    renderCandidates(result);
    setCandidatesBusy(false);
  }

  function handlePickCandidate(candidate) {
    runGenerationProgress(candidate);
  }

  els.showMoreButton.addEventListener("click", () => {
    runSearch({ topic: currentTopic, excludeAngleTypes });
  });

  els.narrowButton.addEventListener("click", () => {
    els.narrowInputRow.hidden = !els.narrowInputRow.hidden;
    if (!els.narrowInputRow.hidden) els.narrowInput.focus();
  });

  function submitNarrowHint() {
    const hint = els.narrowInput.value.trim();
    if (!hint) return;
    excludeAngleTypes = []; // a hint changes the search space, not a continuation of it
    els.narrowInputRow.hidden = true;
    els.narrowInput.value = "";
    runSearch({ topic: currentTopic, hint });
  }

  els.narrowSubmit.addEventListener("click", submitNarrowHint);
  els.narrowInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      submitNarrowHint();
    }
  });

  // ==========================================================================
  // Screen: Generation progress
  // ==========================================================================
  //
  // Sits between picking a candidate and Scene Paper View. The step list is
  // a visual pace-setter over ONE real async call, not five observable
  // phases — POST /generate returns as soon as the job is accepted (202),
  // long before the paper exists, so this screen owns the poll loop against
  // GET /paper?id= until it does. The first N-1 steps advance on a fixed,
  // fast cadence purely to establish visible motion; the LAST step stays in
  // its "active" (spinning) state for as long as polling actually takes —
  // which, per real testing, can run well past the documented 15-30s — so a
  // slow real run never reads as a stalled one.

  const GENERATION_POLL_INTERVAL_MS = 3000;
  const GENERATION_POLL_TIMEOUT_MS = 90000;
  const GENERATION_REASSURANCE_AFTER_MS = 15000;

  // These are the stages POST /generate's job function ACTUALLY runs, in
  // order. Two entries were removed on 2026-08-10 -- "Generating voiceover"
  // and "Matching images" -- because the job logs those as
  // "STUB stage 2/4" and "STUB stage 3/4": neither does any work. Ticking
  // them was claiming work that never happened, which is not a thing this
  // product can afford to do. Put them back when the stages are real.
  //
  // "Searching sources" was also dropped: the search happens during
  // /ideate, before this screen. By the time we get here the candidate
  // already carries its sources.
  const PROGRESS_STEPS = [
    { label: "Verifying sources" },
    { label: "Structuring the scene paper" },
    { label: "Saving your scene paper" },
  ];

  // Measured: Call A ~10s, Call B ~15s, NoSQL write ~1s.
  const GENERATION_EXPECTED_DURATION_MS = 26000;
  const GENERATION_ELAPSED_TICK_MS = 500;
  // Fraction of GENERATION_EXPECTED_DURATION_MS at which each stage after
  // the first becomes active. One fewer entry than PROGRESS_STEPS -- the
  // last stage has no threshold, it holds until the real call returns.
  const GENERATION_STAGE_THRESHOLDS = [0.38, 0.92];

  function generationStageForElapsed(elapsedMs) {
    const ratio = elapsedMs / GENERATION_EXPECTED_DURATION_MS;
    let idx = 0;
    for (const threshold of GENERATION_STAGE_THRESHOLDS) {
      if (ratio >= threshold) idx++;
    }
    return Math.min(idx, PROGRESS_STEPS.length - 1);
  }

  function renderProgressSteps(activeIndex) {
    renderStepList(els.progressSteps, PROGRESS_STEPS, activeIndex);
  }

  function renderProgressFailed(err, candidate) {
    const detail = err && err.message ? ` (${escapeHtml(err.message)})` : "";
    els.progressSteps.innerHTML = `
      <div class="state-message">
        <p>Something went wrong generating the scene paper${detail}.</p>
        <button type="button" class="secondary-button" id="progress-retry-button">Try again</button>
        <button type="button" class="secondary-button" id="progress-back-button">${ICON_ARROW_LEFT}back to candidates</button>
      </div>
    `;
    document.getElementById("progress-retry-button").addEventListener("click", () => {
      runGenerationProgress(candidate);
    });
    document.getElementById("progress-back-button").addEventListener("click", () => {
      showView("candidates");
    });
  }

  function showProgressReassurance() {
    if (document.getElementById("progress-reassurance")) return;
    els.progressSteps.insertAdjacentHTML(
      "beforeend",
      `<p class="progress-reassurance" id="progress-reassurance">Generation can take a while for a new topic — this is still working.</p>`
    );
  }

  // Polls GET /paper?id= until it resolves (api.getPaper returns the paper),
  // times out, or throws (a real backend error — not just "not ready yet",
  // which getPaper already represents as null rather than a rejection).
  async function pollForPaper(paperId) {
    const deadline = Date.now() + GENERATION_POLL_TIMEOUT_MS;
    const reassuranceAt = Date.now() + GENERATION_REASSURANCE_AFTER_MS;
    for (;;) {
      const paper = await api.getPaper(paperId);
      if (paper) return paper;
      if (Date.now() >= reassuranceAt) showProgressReassurance();
      if (Date.now() >= deadline) {
        throw new Error(
          "Generation is taking longer than expected. It may still finish in the background — try checking back, or try again."
        );
      }
      await new Promise((resolve) => setTimeout(resolve, GENERATION_POLL_INTERVAL_MS));
    }
  }

  async function runGenerationProgress(candidate) {
    els.progressOneLiner.textContent = candidate.one_liner;
    showView("progress");

    // Advance stages against ELAPSED TIME, not a fixed animation. The old
    // version raced through every stage in ~2.4s and then parked on the last
    // one for the remaining ~25s, which read as a hang. Same approach the
    // candidate-search screen uses.
    const startedAt = Date.now();
    renderProgressSteps(0);
    const ticker = setInterval(() => {
      renderProgressSteps(generationStageForElapsed(Date.now() - startedAt));
    }, GENERATION_ELAPSED_TICK_MS);

    try {
      const { paper_id } = await api.startGeneration({ candidate, topic: currentTopic });
      const paper = await pollForPaper(paper_id);
      clearInterval(ticker);
      showScenePaper(paper);
    } catch (err) {
      clearInterval(ticker);
      renderProgressFailed(err, candidate);
    }
  }

  // ==========================================================================
  // Screen 3: Scene paper view
  // ==========================================================================

  const ICON_CHECK = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 8.5 6.5 12 13 4.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const ICON_PLAY = `<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M4 2.5v11l10-5.5-10-5.5Z"/></svg>`;
  const ICON_PAUSE = `<svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><rect x="3.5" y="2.5" width="3.2" height="11"/><rect x="9.3" y="2.5" width="3.2" height="11"/></svg>`;
  const ICON_CHEVRON = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M6 3.5 11 8l-5 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

  let currentPaper = null;
  let selectedHookLabel = null;

  // Renders a {text, verified} span array — hooks[].text and, later, scene
  // script lines. Verified spans render as plain text; unverified spans
  // (narrative framing, not sourced fact) get a visually distinct dotted
  // underline — the fact-vs-framing distinction from CLAUDE.md's rule 5,
  // decided during the Screen 1 build as span-level, not a per-line bool.
  function renderSpans(spans) {
    return spans
      .map((s) =>
        s.verified ? escapeHtml(s.text) : `<span class="framing-span">${escapeHtml(s.text)}</span>`
      )
      .join("");
  }

  // CLAUDE.md's ScenePaper schema has no top-level score/tag field — scoring
  // lives per-source. This derives a paper-level badge (average confidence
  // across non-suppressed sources) for the UI; flagging this as an
  // assumption, not a documented field, in case a real endpoint later
  // returns one directly.
  function paperScoreInfo(paper) {
    const used = (paper.sources || []).filter((s) => !s.suppressed);
    const avg = used.length
      ? Math.round(used.reduce((sum, s) => sum + s.confidence_score, 0) / used.length)
      : 0;
    const band = scoreBand(avg);
    const tag =
      band === "success" ? "Primary-sourced" : band === "warning" ? "Corroborated" : "Needs checking";
    return { score: avg, band, tag, sourceCount: used.length };
  }

  function renderPaperMeta(paper) {
    els.paperNumber.textContent = `#${paper.paper_number}`;
    els.paperCategory.textContent = paper.category;
  }

  function renderVerificationBadge(paper) {
    const { score, band, tag, sourceCount } = paperScoreInfo(paper);
    els.verificationBadge.innerHTML = `
      <span class="verification-pill pill-score-tag score-${band}">${ICON_SHIELD_CHECK}${score}/10 · ${escapeHtml(tag)}</span>
      <span class="meta-sources">${ICON_DOCUMENT}${sourceCount} verified source${sourceCount === 1 ? "" : "s"}</span>
    `;
  }

  els.backToCandidatesButton.addEventListener("click", () => {
    showView("candidates");
  });

  function formatPlaybackTime(seconds) {
    if (!Number.isFinite(seconds)) return "0:00";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  function renderAudioPlayer(paper) {
    if (paper.media_status === "generating") {
      els.audioPlayer.innerHTML = `
        <div class="audio-player-surface">
          <span class="playback-state-text">Generating voiceover — text is ready to read in the meantime.</span>
        </div>
      `;
      return;
    }

    if (paper.media_status !== "ready" || !paper.voiceover_url) {
      els.audioPlayer.innerHTML = `
        <div class="audio-player-surface">
          <span class="playback-state-text">Voiceover generation failed — the text below is still usable.</span>
        </div>
      `;
      return;
    }

    els.audioPlayer.innerHTML = `
      <div class="audio-player-surface">
        <button type="button" class="playback-button" id="playback-toggle" aria-label="Play voiceover">${ICON_PLAY}</button>
        <div class="playback-track" id="playback-track"><div class="playback-track-fill" id="playback-track-fill"></div></div>
        <span class="playback-time mono" id="playback-time">0:00 / 0:00</span>
        <audio id="voiceover-audio" src="${escapeHtml(paper.voiceover_url)}" preload="metadata"></audio>
      </div>
    `;

    const audio = document.getElementById("voiceover-audio");
    const toggleButton = document.getElementById("playback-toggle");
    const track = document.getElementById("playback-track");
    const trackFill = document.getElementById("playback-track-fill");
    const timeLabel = document.getElementById("playback-time");

    function updateTime() {
      const total = Number.isFinite(audio.duration) ? audio.duration : 0;
      timeLabel.textContent = `${formatPlaybackTime(audio.currentTime)} / ${formatPlaybackTime(total)}`;
      trackFill.style.width = total ? `${(audio.currentTime / total) * 100}%` : "0%";
    }

    audio.addEventListener("loadedmetadata", updateTime);
    audio.addEventListener("timeupdate", updateTime);
    audio.addEventListener("ended", () => {
      toggleButton.innerHTML = ICON_PLAY;
      toggleButton.setAttribute("aria-label", "Play voiceover");
    });

    toggleButton.addEventListener("click", () => {
      if (audio.paused) {
        audio.play();
        toggleButton.innerHTML = ICON_PAUSE;
        toggleButton.setAttribute("aria-label", "Pause voiceover");
      } else {
        audio.pause();
        toggleButton.innerHTML = ICON_PLAY;
        toggleButton.setAttribute("aria-label", "Play voiceover");
      }
    });

    track.addEventListener("click", (event) => {
      if (!Number.isFinite(audio.duration) || audio.duration === 0) return;
      const rect = track.getBoundingClientRect();
      const ratio = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1);
      audio.currentTime = ratio * audio.duration;
    });
  }

  function renderHooks(paper) {
    els.hookList.innerHTML = (paper.hooks || [])
      .map((h) => {
        const selected = selectedHookLabel === h.label;
        return `
          <button type="button" class="hook-card${selected ? " selected" : ""}" data-hook-label="${escapeHtml(h.label)}" aria-pressed="${selected}">
            <div class="hook-head">
              <span class="hook-label-type">${escapeHtml(h.label)} — ${escapeHtml(h.type)}</span>
              ${selected ? `<span class="hook-selected-icon">${ICON_CHECK_CIRCLE_FILL}</span>` : ""}
            </div>
            <p class="hook-text">"${renderSpans(h.text)}"</p>
            <p class="hook-note">${escapeHtml(h.best_for_note)}</p>
          </button>
        `;
      })
      .join("");

    els.hookList.querySelectorAll(".hook-card").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedHookLabel = btn.dataset.hookLabel;
        renderHooks(currentPaper);
      });
    });
  }

  function renderTiming(paper) {
    const tiles = [
      { label: "Runtime", value: paper.runtime_estimate },
      { label: "Hook window", value: paper.hook_window },
      { label: "Peak tension", value: paper.peak_tension_window },
      { label: "Payoff", value: paper.payoff_window },
    ];
    els.timingGrid.innerHTML = tiles
      .map(
        (t) => `
          <div class="timing-tile">
            <span class="timing-label">${escapeHtml(t.label)}</span>
            <span class="timing-value mono">${escapeHtml(t.value)}</span>
          </div>
        `
      )
      .join("");
  }

  function pacingClass(tag) {
    switch (tag) {
      case "FAST":
        return "pacing-fast";
      case "BUILD":
        return "pacing-build";
      case "SLOW":
        return "pacing-slow";
      case "WARM":
        return "pacing-warm";
      default:
        return "";
    }
  }

  function renderScenes(paper) {
    els.sceneRows.innerHTML = (paper.scenes || [])
      .map(
        (s) => `
          <div class="scene-row" data-scene-number="${escapeHtml(s.scene_number)}" role="button" tabindex="0">
            <span class="scene-row-number mono">${escapeHtml(s.scene_number)}</span>
            <span class="scene-row-name">${escapeHtml(s.scene_name)}</span>
            <span class="scene-row-time mono">${escapeHtml(s.time_range)}</span>
            <span class="pacing-pill ${pacingClass(s.pacing_tag)}">${escapeHtml(s.pacing_tag)}</span>
            <span class="scene-row-chevron">${ICON_CHEVRON}</span>
          </div>
        `
      )
      .join("");

    els.sceneRows.querySelectorAll(".scene-row").forEach((row) => {
      const open = () => openSceneDetail(Number(row.dataset.sceneNumber));
      row.addEventListener("click", open);
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          open();
        }
      });
    });
  }

  function renderSources(paper) {
    // "Verified sources" — suppressed sources aren't part of this paper's
    // backing evidence, so (unlike Screen 2) there's no dev-only suppressed
    // section here; this screen simply doesn't show them.
    const visible = (paper.sources || []).filter((s) => !s.suppressed);
    els.sourceRows.innerHTML = visible
      .map(
        (s) => `
          <div class="source-row">
            <span class="source-check">${ICON_CHECK}</span>
            <span class="source-row-title">${escapeHtml(s.title)}</span>
            <span class="source-row-meta">${escapeHtml(s.type)} · ${escapeHtml(s.date)}</span>
          </div>
        `
      )
      .join("");
  }

  function renderExportRow(paper) {
    const unlocked = paper.export_status === "unlocked";
    els.exportRow.innerHTML = `
      <div class="export-card-main">
        <span class="export-card-icon">${ICON_LOCK}</span>
        <div>
          <div class="export-state">Audio/video export — ${unlocked ? "unlocked" : "locked"}</div>
          <div class="export-note">Always-paid feature. Mocked in this prototype — no real charge.</div>
        </div>
      </div>
      <button type="button" class="secondary-button" id="export-toggle">
        ${unlocked ? "Lock (mock)" : "Unlock (mock)"}
      </button>
    `;
    document.getElementById("export-toggle").addEventListener("click", () => {
      paper.export_status = unlocked ? "locked" : "unlocked";
      renderExportRow(paper);
    });
  }

  function showScenePaper(paper) {
    // Belt and braces: unwrap the {status, paper} envelope here too.
    // GET /paper?id= responds {status:"success", paper:{...}}; mockApi's
    // getPaper unwraps it, but doing it again at the render boundary means a
    // paper arriving from ANY path renders correctly. Handing the envelope to
    // the renderer is what made complete, correctly-scored papers display as
    // "0/10 · Needs checking" with no hooks and no scenes -- every field was
    // simply one level too deep. Cheap to be defensive about; expensive to
    // debug when it happens.
    if (paper && paper.paper && !paper.title) paper = paper.paper;
    currentPaper = paper;
    // Hook selection persists for as long as this paper is on screen — it's
    // part of what the user takes to recording. Defaults to the first hook
    // so something is always active. No schema field exists for this yet,
    // so it's client-only state, not sent anywhere.
    // `hooks` can be ABSENT, not merely empty: the schema marks it required
    // (the key must exist) but does not forbid an empty array, and the
    // backend prunes null-valued keys before writing to NoSQL. A live run
    // crashed here with "undefined is not an object" because the old guard
    // indexed before checking. Treat every schema array as possibly missing.
    const hooks = paper.hooks || [];
    selectedHookLabel = hooks[0] ? hooks[0].label : null;

    renderPaperMeta(paper);
    els.paperTitle.textContent = paper.title;
    els.paperDek.textContent = paper.dek;
    renderVerificationBadge(paper);
    renderAudioPlayer(paper);
    renderHooks(paper);
    renderTiming(paper);
    renderScenes(paper);
    renderSources(paper);
    renderExportRow(paper);

    showView("paper");
  }

  // ==========================================================================
  // Screen 4: Scene detail
  // ==========================================================================
  //
  // Data shape note: unlike hooks[].text, scenes[].script[].line here is a
  // plain string (per the Screen 4 brief), not the {text, verified} span
  // array CLAUDE.md documents. The fact-vs-framing distinction for a scene
  // lives instead in that scene's own claims[] (see renderClaims below).
  // Flagged in the checkpoint — two mechanisms for rule 5 now exist in one
  // paper (hooks: inline spans, scenes: a separate claims list) and that's
  // worth reconciling in CLAUDE.md, not something resolved unilaterally here.

  const ICON_DIRECTION = `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M10.5 2.5 13.5 5.5 5.5 13.5H2.5v-3Z" stroke="currentColor" stroke-width="1.3" stroke-linejoin="round"/><path d="M9 4 12 7" stroke="currentColor" stroke-width="1.3"/></svg>`;
  const ICON_FRAMING = `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M3 6.5c0-1.7 1-2.7 2.6-3v1.2c-.8.3-1.2.8-1.2 1.6h1.2v3.2H3V6.5Zm6.2 0c0-1.7 1-2.7 2.6-3v1.2c-.8.3-1.2.8-1.2 1.6h1.2v3.2H9.2V6.5Z" fill="currentColor"/></svg>`;
  const ICON_IMAGE = `<svg width="18" height="18" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1.5" y="2.5" width="13" height="11" rx="1.3" stroke="currentColor" stroke-width="1.2"/><circle cx="5.3" cy="6" r="1.1" stroke="currentColor" stroke-width="1.1"/><path d="M2 11.5 5.5 8l2.5 2.5 2.5-3 3 3" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round"/></svg>`;

  let currentSceneIndex = -1;

  // Pulls "[pause 0.8s]"-style tokens out of a direction string so they can
  // render as their own monospace pill instead of sitting inline as raw
  // prose — they're data (a TTS-readable cue), not narration.
  function extractPauseMarkers(direction) {
    const pauses = [];
    const cleaned = direction
      .replace(/\[pause\s+([\d.]+s)\]/gi, (match, dur) => {
        pauses.push(dur);
        return "";
      })
      .replace(/\s{2,}/g, " ")
      .trim();
    return { cleaned, pauses };
  }

  // A speaker change must be structurally obvious, not just a different
  // label — any non-primary speaker (SPEAKER_1, SPEAKER_2, ...) gets the
  // same left-accent-border + tinted-background treatment, per the design
  // handoff. (An earlier pass rotated a distinct color per secondary
  // speaker; the handoff uses one consistent accent for all of them, so
  // that's what this renders now.)
  function isSecondarySpeaker(speaker) {
    return speaker !== "SPEAKER";
  }

  function renderScriptMeta(scene) {
    const script = scene.script || [];
    const speakerCount = new Set(script.map((l) => l.speaker)).size;
    els.scriptMeta.textContent = `${script.length} line${
      script.length === 1 ? "" : "s"
    } · ${speakerCount} speaker${speakerCount === 1 ? "" : "s"}`;
  }

  function renderScriptLines(scene) {
    // Declared here, not borrowed from renderScriptMeta -- an earlier
    // defensive-guard edit referenced `script` in this function while only
    // declaring it in that one, so this threw ReferenceError and killed the
    // whole scene-detail render before the view could switch.
    const script = scene.script || [];
    els.scriptLines.innerHTML = script
      .map((entry) => {
        const isQuote = isSecondarySpeaker(entry.speaker);
        const variantClass = isQuote ? "script-line--secondary" : "";
        const { cleaned, pauses } = extractPauseMarkers(entry.direction);
        return `
          <div class="script-line ${variantClass}">
            <div class="script-line-head">
              <span class="speaker-label mono">${escapeHtml(entry.speaker)}</span>
              ${isQuote ? '<span class="pill quote-tag">Direct quote</span>' : ""}
            </div>
            <p class="script-line-text">${escapeHtml(entry.line)}</p>
            <div class="direction-block">
              <span class="direction-icon">${ICON_DIRECTION}</span>
              <span class="direction-text">${escapeHtml(cleaned)}</span>
              ${pauses
                .map((p) => `<span class="pause-pill mono">pause ${escapeHtml(p)}</span>`)
                .join("")}
            </div>
          </div>
        `;
      })
      .join("");
  }

  function renderClaims(scene) {
    const claims = scene.claims || [];
    if (!claims.length) {
      els.claimsList.innerHTML = `<p class="usage-line">No individually flagged claims in this scene.</p>`;
      return;
    }
    els.claimsList.innerHTML = claims
      .map((c) => {
        if (c.verified) {
          const sourcesText = (c.sources || [])
            .map((s) => `${escapeHtml(s.title)} (${escapeHtml(s.date)})`)
            .join("; ");
          return `
            <div class="claim-row is-verified">
              <div class="claim-kind is-verified">${ICON_CHECK}verified fact</div>
              <p class="claim-text">${escapeHtml(c.text)}</p>
              <p class="claim-source-line">${sourcesText}</p>
            </div>
          `;
        }
        return `
          <div class="claim-row is-framing">
            <div class="claim-kind is-framing">${ICON_FRAMING}narrative framing</div>
            <p class="claim-text is-framing">${escapeHtml(c.text)}</p>
            <p class="claim-source-line">Not a sourced claim — narrative framing.</p>
          </div>
        `;
      })
      .join("");
  }

  // Per the design handoff: the image-matching pipeline isn't built, so this
  // always shows the honest pending state — never a real or fake photo,
  // regardless of what's in paper.image_set (which mockApi.js keeps empty
  // for exactly this reason). Swap stays disabled; there's nothing to swap.
  function renderSceneImage() {
    els.sceneImageBlock.innerHTML = `
      <div class="scene-image-thumb">${ICON_IMAGE}</div>
      <div class="scene-image-info">
        <p class="scene-image-description">Image not yet generated — matching pipeline pending</p>
        <p class="scene-image-note">Honestly reflects the current build status</p>
      </div>
      <button type="button" class="secondary-button" id="swap-image-button" disabled>Swap</button>
    `;
  }

  function parseTimeRangeSeconds(timeRange) {
    const match = /^(\d+)\s*[–-]\s*(\d+)s?$/.exec(timeRange.trim());
    if (!match) return { start: 0, end: null };
    return { start: parseInt(match[1], 10), end: parseInt(match[2], 10) };
  }

  function renderSceneAudioPlayer(paper, scene) {
    if (paper.media_status === "generating") {
      els.sceneAudioPlayer.innerHTML = `
        <div class="audio-player-surface">
          <span class="playback-state-text">Generating voiceover — text is ready to read in the meantime.</span>
        </div>
      `;
      return;
    }

    if (paper.media_status !== "ready" || !paper.voiceover_url) {
      els.sceneAudioPlayer.innerHTML = `
        <div class="audio-player-surface">
          <span class="playback-state-text">Audio not yet generated for this scene.</span>
        </div>
      `;
      return;
    }

    const { start, end } = parseTimeRangeSeconds(scene.time_range);

    els.sceneAudioPlayer.innerHTML = `
      <div class="audio-player-surface">
        <button type="button" class="playback-button" id="scene-playback-toggle" aria-label="Play scene">${ICON_PLAY}</button>
        <div class="playback-track" id="scene-playback-track"><div class="playback-track-fill" id="scene-playback-track-fill"></div></div>
        <span class="playback-time mono" id="scene-playback-time">0:00 / 0:00</span>
        <audio id="scene-voiceover-audio" src="${escapeHtml(paper.voiceover_url)}" preload="metadata"></audio>
      </div>
    `;

    const audio = document.getElementById("scene-voiceover-audio");
    const toggleButton = document.getElementById("scene-playback-toggle");
    const track = document.getElementById("scene-playback-track");
    const trackFill = document.getElementById("scene-playback-track-fill");
    const timeLabel = document.getElementById("scene-playback-time");

    // There's no separate per-scene audio file in the schema — this reuses
    // the whole-paper voiceover_url but constrains playback to this scene's
    // time_range slice, since that window is already known.
    function updateTime() {
      const sceneDuration = end !== null ? end - start : 0;
      const elapsed = Math.min(Math.max(audio.currentTime - start, 0), sceneDuration || Infinity);
      timeLabel.textContent = `${formatPlaybackTime(elapsed)} / ${formatPlaybackTime(sceneDuration)}`;
      trackFill.style.width = sceneDuration ? `${Math.min((elapsed / sceneDuration) * 100, 100)}%` : "0%";
      if (end !== null && audio.currentTime >= end) {
        audio.pause();
        toggleButton.innerHTML = ICON_PLAY;
        toggleButton.setAttribute("aria-label", "Play scene");
      }
    }

    audio.addEventListener("timeupdate", updateTime);
    audio.addEventListener("loadedmetadata", updateTime);

    toggleButton.addEventListener("click", () => {
      if (audio.paused) {
        if (audio.currentTime < start || (end !== null && audio.currentTime >= end)) {
          audio.currentTime = start;
        }
        audio.play();
        toggleButton.innerHTML = ICON_PAUSE;
        toggleButton.setAttribute("aria-label", "Pause scene");
      } else {
        audio.pause();
        toggleButton.innerHTML = ICON_PLAY;
        toggleButton.setAttribute("aria-label", "Play scene");
      }
    });

    track.addEventListener("click", (event) => {
      if (end === null) return;
      const rect = track.getBoundingClientRect();
      const ratio = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1);
      audio.currentTime = start + ratio * (end - start);
    });
  }

  function renderSceneNav() {
    const isFirst = currentSceneIndex <= 0;
    const isLast = currentSceneIndex >= currentPaper.scenes.length - 1;
    els.scenePrevButton.disabled = isFirst;
    els.sceneNextButton.disabled = isLast;
  }

  function renderSceneDetail(index) {
    currentSceneIndex = index;
    const scene = currentPaper.scenes[index];

    els.sceneNumberLabel.textContent = `scene ${scene.scene_number}`;
    els.scenePacingPillWrap.innerHTML = `<span class="pacing-pill ${pacingClass(
      scene.pacing_tag
    )}">${escapeHtml(scene.pacing_tag)}</span>`;
    els.sceneTimeRange.textContent = scene.time_range;
    els.sceneTitleText.textContent = scene.scene_name;

    renderSceneAudioPlayer(currentPaper, scene);
    renderScriptMeta(scene);
    renderScriptLines(scene);
    renderClaims(scene);
    renderSceneImage();
    renderSceneNav();
  }

  function openSceneDetail(sceneNumber) {
    const index = currentPaper.scenes.findIndex((s) => s.scene_number === sceneNumber);
    if (index === -1) return;
    renderSceneDetail(index);
    showView("scene");
  }

  els.sceneBackButton.addEventListener("click", () => {
    showView("paper");
  });

  els.scenePrevButton.addEventListener("click", () => {
    if (currentSceneIndex > 0) renderSceneDetail(currentSceneIndex - 1);
  });

  els.sceneNextButton.addEventListener("click", () => {
    if (currentSceneIndex < currentPaper.scenes.length - 1) renderSceneDetail(currentSceneIndex + 1);
  });
})();
