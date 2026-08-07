/**
 * app.js
 * ------
 * Rendering + view logic only. Every piece of backend-shaped data comes from
 * window.ScenePaperMockApi (see mockApi.js) — this file never fetches
 * anything itself, per agents/ui-agent.md ("Never touches: any backend/API
 * logic — this agent renders whatever JSON the Python API returns").
 *
 * Recent-searches history is the one exception: it's pure client-side UX
 * state (last few topics typed on this device) with no equivalent in the
 * ScenePaper/UserProfile entity schema, so it lives in localStorage here
 * rather than behind the mock API's swap point.
 *
 * Screen 1 (Topic input) only. No framework, no build step, per CLAUDE.md.
 */

(function () {
  const RECENT_SEARCHES_KEY = "scenepaper_recent_searches";
  const MAX_RECENT = 5;

  const EXAMPLE_PROMPTS = [
    "an underdog comeback",
    "Nokia",
    "a decision that backfired",
    "Blockbuster",
  ];

  const els = {
    form: document.getElementById("topic-form"),
    textarea: document.getElementById("topic-input"),
    fieldError: document.getElementById("topic-error"),
    submitButton: document.getElementById("topic-submit"),
    status: document.getElementById("topic-status"),
    chips: document.getElementById("example-chips"),
    recentSearches: document.getElementById("recent-searches"),
    settingsButton: document.getElementById("settings-button"),
  };

  function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
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

  // ---- example chips (populate input, don't submit) ----

  function renderChips() {
    els.chips.innerHTML = `
      <span class="section-label">or try</span>
      <div class="chip-row">
        ${EXAMPLE_PROMPTS.map(
          (topic) =>
            `<button type="button" class="chip" data-topic="${escapeHtml(topic)}">${escapeHtml(topic)}</button>`
        ).join("")}
      </div>
    `;
    els.chips.querySelectorAll(".chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        els.textarea.value = btn.dataset.topic;
        els.textarea.focus();
        autoGrow();
        clearFieldError();
      });
    });
  }

  // ---- recent searches (client-side only, see file header) ----

  function loadRecentSearches() {
    try {
      const raw = localStorage.getItem(RECENT_SEARCHES_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  function saveRecentSearch(topic) {
    const trimmed = topic.trim();
    if (!trimmed) return;
    let list = loadRecentSearches().filter(
      (t) => t.toLowerCase() !== trimmed.toLowerCase()
    );
    list.unshift(trimmed);
    list = list.slice(0, MAX_RECENT);
    localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify(list));
    renderRecentSearches();
  }

  function renderRecentSearches() {
    const recents = loadRecentSearches();
    if (!recents.length) {
      els.recentSearches.hidden = true;
      els.recentSearches.innerHTML = "";
      return;
    }
    els.recentSearches.hidden = false;
    els.recentSearches.innerHTML = `
      <span class="section-label">recent searches</span>
      <div class="recent-list">
        ${recents
          .map(
            (topic) =>
              `<button type="button" class="recent-item" data-topic="${escapeHtml(topic)}">${escapeHtml(topic)}</button>`
          )
          .join("")}
      </div>
    `;
    els.recentSearches.querySelectorAll(".recent-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        els.textarea.value = btn.dataset.topic;
        autoGrow();
        submitTopic(btn.dataset.topic);
      });
    });
  }

  // ---- submit handling ----

  function clearFieldError() {
    els.fieldError.hidden = true;
    els.fieldError.textContent = "";
  }

  function showFieldError(message) {
    els.fieldError.hidden = false;
    els.fieldError.textContent = message;
  }

  function setBusy(isBusy) {
    els.submitButton.disabled = isBusy;
    els.textarea.disabled = isBusy;
    els.chips.querySelectorAll(".chip").forEach((btn) => (btn.disabled = isBusy));
    els.recentSearches
      .querySelectorAll(".recent-item")
      .forEach((btn) => (btn.disabled = isBusy));
  }

  async function submitTopic(topic) {
    const trimmed = (topic || "").trim();
    if (!trimmed) {
      showFieldError("Enter a topic, or tap an example below to get started.");
      return;
    }
    clearFieldError();
    setBusy(true);
    els.status.textContent = "Searching for verified candidate stories…";

    saveRecentSearch(trimmed);

    // Stub: Screen 2 (candidate search / generation) hasn't been specced yet.
    // Wired here so the handoff point exists; replace with the real
    // transition once that screen is built.
    await new Promise((resolve) => setTimeout(resolve, 600));

    setBusy(false);
    els.status.textContent = `Next: handing off to the generation screen for "${trimmed}" (not built yet).`;
  }

  els.form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitTopic(els.textarea.value);
  });

  els.settingsButton.addEventListener("click", () => {
    console.info("[stub] settings screen not built yet");
  });

  // ---- init ----

  renderChips();
  renderRecentSearches();
})();
