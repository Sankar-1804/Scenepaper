/**
 * splash.js
 * ---------
 * First-load logo animation. Fetches public/scenepaper-splash.svg and
 * inlines its markup directly into #hero-logo (not <img>), so the mark and
 * wordmark — both `fill="currentColor"` — pick up the page's theme color.
 *
 * There is deliberately only ONE logo element on the page. It shows the
 * animated SVG, which plays once and freezes on its final frame (the
 * source file uses fill="freeze" throughout) — it is never swapped for a
 * second "real" element afterward. Swapping elements is exactly what would
 * risk a visible pop/mismatch at the handoff moment; not swapping means
 * there is nothing TO look different, by construction. The rest of the
 * page (marked .pre-reveal in index.html/styles.css) fades in around it
 * once the timer below fires.
 *
 * Sizing: the SVG's own canvas has a lot of empty margin around the actual
 * mark + wordmark (its viewBox is 680x200; the visible content is much
 * smaller and roughly centered within that). We re-crop the viewBox to the
 * real rendered bounding box (measured via getBBox(), not guessed) and
 * scale so the wordmark's font-size matches the plain-text hero title this
 * replaced (2.75rem / 44px) — see TARGET_WORDMARK_PX below.
 *
 * "First load only, not on every route change": this app has no
 * client-side router yet, so every page load IS a first load, and this
 * IIFE runs exactly once. If in-app screen navigation is added later
 * without a full page reload, that navigation must NOT re-run this file's
 * logic — it exposes nothing for other code to re-trigger it.
 *
 * SMIL (the animation format the SVG uses) works in browsers but has no
 * SwiftUI equivalent — the iOS client needs this rebuilt natively or
 * converted to Lottie. Do not try to render this file directly on iOS.
 */

(function () {
  const SPLASH_SVG_PATH = "public/scenepaper-splash.svg";
  const ANIMATED_DURATION_MS = 2000; // ~= the SVG's own 1.98s runtime
  const REDUCED_MOTION_DURATION_MS = 400; // brief brand beat, nothing to wait out
  const TARGET_WORDMARK_PX = 44; // matches the old .hero-title's 2.75rem (16px root)
  const CROP_PADDING = 16; // SVG user-units of breathing room around the measured content
  // The icon square's background is fill="currentColor" but its internal
  // bars/dot are hardcoded fill="#ffffff". In dark mode, currentColor
  // resolves to the near-white page text color, so the square and its
  // "document lines" detail collapse into nearly the same shade and the
  // detail disappears. Giving the icon's own <g> a distinct `color` makes
  // its currentColor resolve separately from the wordmark text's.
  const ICON_COLOR = "var(--color-accent)";

  const logoContainer = document.getElementById("hero-logo");

  function revealApp() {
    document.body.classList.add("app-revealed");
  }

  // Resolves every <animate>/<animateTransform> in the given markup to its
  // final value (reading `to`, or the last entry of `values`) and removes
  // the animation elements — used both to render the reduced-motion static
  // end state and to measure the settled geometry for cropping (below).
  function staticizeSvg(svgText) {
    const doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
    doc.querySelectorAll("animate, animateTransform").forEach((animEl) => {
      const target = animEl.parentElement;
      const attrName = animEl.getAttribute("attributeName");
      if (!target || !attrName) {
        animEl.remove();
        return;
      }
      if (animEl.tagName.toLowerCase() === "animatetransform") {
        const to = animEl.getAttribute("to");
        const type = animEl.getAttribute("type") || "translate";
        if (to) target.setAttribute(attrName, `${type}(${to})`);
      } else {
        let finalValue = animEl.getAttribute("to");
        if (finalValue === null) {
          const values = animEl.getAttribute("values");
          if (values) {
            const parts = values.split(";");
            finalValue = parts[parts.length - 1].trim();
          }
        }
        if (finalValue !== null) target.setAttribute(attrName, finalValue);
      }
      animEl.remove();
    });
    return doc.documentElement.outerHTML;
  }

  // Renders `markup` off-screen (visibility:hidden, not display:none, so
  // getBBox() still works) and returns the real pixel bounding box of its
  // drawn content, in the SVG's own user-unit coordinate space.
  function measureContentBBox(markup) {
    const wrapper = document.createElement("div");
    wrapper.style.cssText = "position:absolute; visibility:hidden; top:0; left:0;";
    wrapper.innerHTML = markup;
    document.body.appendChild(wrapper);
    const svgEl = wrapper.querySelector("svg");
    const bbox = svgEl.getBBox();
    document.body.removeChild(wrapper);
    return bbox;
  }

  function getWordmarkFontSize(markup) {
    const doc = new DOMParser().parseFromString(markup, "image/svg+xml");
    const textGroup = doc.querySelector("g[font-size]");
    const parsed = textGroup ? parseFloat(textGroup.getAttribute("font-size")) : NaN;
    return Number.isFinite(parsed) ? parsed : TARGET_WORDMARK_PX; // sane fallback
  }

  function applyViewBox(markup, viewBox) {
    const doc = new DOMParser().parseFromString(markup, "image/svg+xml");
    const svgEl = doc.documentElement;
    svgEl.setAttribute("viewBox", viewBox);

    // First top-level <g> in this file is the icon group (translate +
    // background square + white detail bars); the second is the wordmark
    // text group. Tint just the icon's so its currentColor square doesn't
    // blend into the wordmark's ambient text color — see ICON_COLOR above.
    const iconGroup = svgEl.querySelector("g");
    if (iconGroup) iconGroup.style.color = ICON_COLOR;

    return svgEl.outerHTML;
  }

  async function initLogo() {
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    let svgText;
    try {
      const res = await fetch(SPLASH_SVG_PATH);
      if (!res.ok) throw new Error(`splash SVG fetch failed: ${res.status}`);
      svgText = await res.text();
    } catch (err) {
      // Don't let a missing/broken logo asset block the real app.
      console.error("Logo SVG failed to load — skipping.", err);
      revealApp();
      return;
    }

    const staticMarkup = staticizeSvg(svgText);

    // Measure the SETTLED geometry (icon already at its final translated
    // position) regardless of which version we're about to show, so the
    // crop matches the end state either way.
    const bbox = measureContentBBox(staticMarkup);
    const viewBox = `${bbox.x - CROP_PADDING} ${bbox.y - CROP_PADDING} ${
      bbox.width + CROP_PADDING * 2
    } ${bbox.height + CROP_PADDING * 2}`;

    const sourceFontSize = getWordmarkFontSize(svgText);
    const scale = TARGET_WORDMARK_PX / sourceFontSize;
    const renderedWidthPx = Math.round((bbox.width + CROP_PADDING * 2) * scale);

    const finalMarkup = applyViewBox(
      prefersReducedMotion ? staticMarkup : svgText,
      viewBox
    );

    logoContainer.innerHTML = finalMarkup;
    const svgEl = logoContainer.querySelector("svg");
    svgEl.style.width = `min(90vw, ${renderedWidthPx}px)`;
    svgEl.style.height = "auto";

    setTimeout(
      revealApp,
      prefersReducedMotion ? REDUCED_MOTION_DURATION_MS : ANIMATED_DURATION_MS
    );
  }

  initLogo();
})();
