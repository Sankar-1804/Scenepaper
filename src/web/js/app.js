/**
 * app.js
 * ------
 * Rendering + view logic only. Every piece of data comes from
 * window.ScenePaperMockApi (see mockApi.js) — this file never fetches
 * anything itself and never touches backend/API logic, per agents/ui-agent.md
 * ("Never touches: Any backend/API logic — this agent renders whatever JSON
 * the Python API returns").
 *
 * No framework, no build step — plain DOM + template strings, per CLAUDE.md.
 */

(function () {
  const api = window.ScenePaperMockApi;

  const els = {
    usageWidget: document.getElementById("usage-widget"),
    viewTopic: document.getElementById("view-topic"),
    viewPaper: document.getElementById("view-paper"),
    topicForm: document.getElementById("topic-form"),
    topicInput: document.getElementById("topic-input"),
    topicSubmit: document.getElementById("topic-submit"),
    topicStatus: document.getElementById("topic-status"),
    candidateList: document.getElementById("candidate-list"),
    backButton: document.getElementById("back-to-candidates"),
    paperStatus: document.getElementById("paper-status"),
    paperDetail: document.getElementById("paper-detail"),
  };

  let currentPaper = null;

  // ---- small helpers --------------------------------------------------

  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
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

  function switchView(view) {
    els.viewTopic.classList.toggle("hidden", view !== "topic");
    els.viewPaper.classList.toggle("hidden", view !== "paper");
  }

  // ---- usage widget (mocked usage-gate UI) -----------------------------

  async function renderUsageWidget() {
    const usage = await api.getUsageStatus();
    const remaining = Math.max(usage.free_limit - usage.scenepapers_generated_count, 0);
    const pct = Math.min(
      100,
      Math.round((usage.scenepapers_generated_count / usage.free_limit) * 100)
    );
    els.usageWidget.innerHTML = `
      <div class="usage-count">
        Free generations used: <strong>${usage.scenepapers_generated_count} of ${usage.free_limit}</strong>
        (${remaining} left)
      </div>
      <div class="usage-bar" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100">
        <div class="usage-bar-fill" style="width:${pct}%"></div>
      </div>
      <div class="simulated-badge">Simulated for demo — no real payment gateway</div>
    `;
  }

  // ---- candidate picker --------------------------------------------------

  function renderCandidates(candidates) {
    els.candidateList.innerHTML = candidates
      .map(
        (c) => `
        <article class="candidate-card">
          <p class="candidate-one-liner">${escapeHtml(c.one_liner)}</p>
          <div class="candidate-meta">
            <span class="score-badge">${escapeHtml(c.confidence_score)}/10</span>
            <span class="tag-badge">${escapeHtml(c.tag)}</span>
            ${c.flags
              .map((f) => `<span class="flag-badge">${escapeHtml(f)}</span>`)
              .join("")}
          </div>
          <button class="pick-button" data-candidate-id="${escapeHtml(c.id)}">
            Pick this story
          </button>
        </article>
      `
      )
      .join("");

    els.candidateList.querySelectorAll(".pick-button").forEach((btn) => {
      btn.addEventListener("click", () => {
        const candidate = candidates.find((c) => c.id === btn.dataset.candidateId);
        handlePickCandidate(candidate);
      });
    });
  }

  async function handleTopicSubmit(event) {
    event.preventDefault();
    const topic = els.topicInput.value;
    els.topicSubmit.disabled = true;
    els.topicStatus.textContent = "Searching for verified candidate stories...";
    els.candidateList.innerHTML = "";

    try {
      const { candidates } = await api.searchStoryIdeas(topic);
      els.topicStatus.textContent = `Showing ${candidates.length} candidates (top results shown regardless of score — see CLAUDE.md trust model).`;
      renderCandidates(candidates);
    } catch (err) {
      els.topicStatus.textContent = `Something went wrong: ${err.message}`;
    } finally {
      els.topicSubmit.disabled = false;
    }
  }

  async function handlePickCandidate(candidate) {
    els.topicStatus.textContent = `Structuring scene paper for: "${candidate.one_liner}"...`;

    const result = await api.generateScenePaper(candidate);

    if (result && result.error === "FREE_LIMIT_REACHED") {
      els.topicStatus.textContent = `${result.message}`;
      return;
    }

    currentPaper = result;
    renderPaperDetail(currentPaper);
    switchView("paper");
    renderUsageWidget();
  }

  // ---- scene paper detail view --------------------------------------------

  function renderHooks(hooks) {
    return hooks
      .map(
        (h) => `
        <li class="hook-item">
          <div class="hook-head">
            <span class="hook-label">${escapeHtml(h.label)}</span>
            <span class="hook-type">${escapeHtml(h.type)}</span>
          </div>
          <p class="hook-text">"${escapeHtml(h.text)}"</p>
          <p class="hook-note">${escapeHtml(h.best_for_note)}</p>
        </li>
      `
      )
      .join("");
  }

  function renderScenes(scenes) {
    return scenes
      .map(
        (s) => `
        <li class="scene-item">
          <div class="scene-head">
            <span class="scene-number">Scene ${escapeHtml(s.scene_number)}</span>
            <span class="scene-title">${escapeHtml(s.title)}</span>
            <span class="pacing-badge ${pacingClass(s.pacing_tag)}">${escapeHtml(s.pacing_tag)}</span>
            <span class="scene-time">${escapeHtml(s.time_range)}</span>
          </div>
          <p class="scene-description">${escapeHtml(s.description)}</p>
        </li>
      `
      )
      .join("");
  }

  function renderDeliveryNotes(notes) {
    return notes
      .map(
        (n) => `
        <li class="delivery-note-item">
          <span class="delivery-note-label">${escapeHtml(n.label)}</span>
          <span class="delivery-note-text">${escapeHtml(n.note)}</span>
        </li>
      `
      )
      .join("");
  }

  function renderSources(sources) {
    return sources
      .map((s) => {
        const suppressedClass = s.suppressed ? "source-card suppressed" : "source-card";
        return `
        <li class="${suppressedClass}">
          <div class="source-head">
            <span class="source-title">${escapeHtml(s.title)}</span>
            <span class="score-badge">${escapeHtml(s.confidence_score)}/10</span>
          </div>
          <div class="source-meta">
            <span class="source-type">${escapeHtml(s.type)}</span>
            <span class="source-date">${escapeHtml(s.date)}</span>
            <span class="source-verified">${s.verified ? "verified" : "unverified"}</span>
            <span class="tag-badge">${escapeHtml(s.tag)}</span>
          </div>
          ${
            s.flags && s.flags.length
              ? `<div class="source-flags">${s.flags
                  .map((f) => `<span class="flag-badge">${escapeHtml(f)}</span>`)
                  .join("")}</div>`
              : ""
          }
          ${
            s.suppressed
              ? `<div class="suppression-notice">
                  <strong>Suppressed.</strong> ${escapeHtml(s.suppression_reason)}
                </div>`
              : ""
          }
        </li>
      `;
      })
      .join("");
  }

  function renderPlaybackStub(paper) {
    const hasAudio = Boolean(paper.voiceover_url);
    return `
      <div class="playback-stub">
        <button class="playback-button" disabled>&#9654; Play voiceover</button>
        <span class="playback-state">
          ${
            hasAudio
              ? "Ready"
              : "Not yet available — voiceover generation runs in a later pipeline stage (Tier 1, in progress on another worktree)."
          }
        </span>
      </div>
    `;
  }

  function renderExportGate(paper) {
    const unlocked = paper.export_status === "unlocked";
    return `
      <div class="export-gate">
        <span class="export-state">Export: <strong>${unlocked ? "Unlocked" : "Locked"}</strong></span>
        <button id="unlock-export-button" class="unlock-button" data-unlocked="${unlocked}">
          ${unlocked ? "Re-lock (simulated)" : "Unlock export (simulated)"}
        </button>
        <div class="simulated-badge">Simulated for demo — no real charge, no payment gateway</div>
      </div>
    `;
  }

  function renderPaperDetail(paper) {
    els.paperStatus.textContent = "";
    els.paperDetail.innerHTML = `
      <header class="paper-header">
        <span class="paper-number">#${escapeHtml(paper.paper_number)}</span>
        <h2 class="paper-title">${escapeHtml(paper.title)}</h2>
        <span class="category-badge">${escapeHtml(paper.category)}</span>
      </header>

      <p class="paper-dek">${escapeHtml(paper.dek)}</p>
      <p class="verification-status">${escapeHtml(paper.verification_status)}</p>

      <div class="windows-row">
        <span>Runtime: ${escapeHtml(paper.runtime_estimate)}</span>
        <span>Hook window: ${escapeHtml(paper.hook_window)}</span>
        <span>Peak tension: ${escapeHtml(paper.peak_tension_window)}</span>
        <span>Payoff: ${escapeHtml(paper.payoff_window)}</span>
      </div>

      <section class="paper-section">
        <h3>Hooks</h3>
        <ul class="hook-list">${renderHooks(paper.hooks)}</ul>
      </section>

      <section class="paper-section">
        <h3>Scenes</h3>
        <ol class="scene-list">${renderScenes(paper.scenes)}</ol>
      </section>

      <section class="paper-section">
        <h3>Delivery notes</h3>
        <ul class="delivery-note-list">${renderDeliveryNotes(paper.delivery_notes)}</ul>
      </section>

      <section class="paper-section">
        <h3>CTA</h3>
        <p class="cta-text">${escapeHtml(paper.cta_text)}</p>
      </section>

      <section class="paper-section">
        <h3>Sources</h3>
        <ul class="source-list">${renderSources(paper.sources)}</ul>
      </section>

      <section class="paper-section">
        <h3>Voiceover</h3>
        ${renderPlaybackStub(paper)}
      </section>

      <section class="paper-section">
        <h3>Media status</h3>
        <p>media_status: <strong>${escapeHtml(paper.media_status)}</strong> — image_set is empty until the images pipeline lands.</p>
      </section>

      <section class="paper-section">
        <h3>Export</h3>
        ${renderExportGate(paper)}
      </section>
    `;

    const unlockButton = document.getElementById("unlock-export-button");
    unlockButton.addEventListener("click", async () => {
      const currentlyUnlocked = unlockButton.dataset.unlocked === "true";
      unlockButton.disabled = true;
      const result = await api.setExportUnlocked(paper.id, !currentlyUnlocked);
      paper.export_status = result.export_status;
      renderPaperDetail(paper);
    });
  }

  // ---- wiring --------------------------------------------------------

  els.topicForm.addEventListener("submit", handleTopicSubmit);
  els.backButton.addEventListener("click", () => {
    currentPaper = null;
    switchView("topic");
  });

  renderUsageWidget();
  switchView("topic");
})();
