/* ==========================================================================
   fit.js — copy fitting
   Every block on the page has a fixed box. Real page make-up solves the
   mismatch between copy length and box height by nudging type size and, when
   that runs out, by cutting copy and running a jump line. This does the same:
     1. binary-search a type scale that makes the copy fill its box,
     2. if the copy still won't fit at the smallest allowed scale, drop
        trailing paragraphs and set a jump line / continuation mark,
     3. report everything it had to do so the build can warn the editor.
   Runs in the page before Chromium prints to PDF.
   ========================================================================== */
(() => {
  "use strict";

  const MIN_SCALE = 0.84;
  const MAX_SCALE = 1.12;
  const STEPS = 11;          // binary-search iterations (~0.0001 precision)
  const SLACK_PX = 1.5;      // sub-pixel tolerance when measuring overflow

  /** Does this element's content spill past its box? Multi-column copy
   *  overflows sideways (column-fill: auto), single-column copy downwards. */
  function overflows(el) {
    if (!el) return false;
    return el.scrollHeight > el.clientHeight + SLACK_PX ||
           el.scrollWidth > el.clientWidth + SLACK_PX;
  }

  function anyOverflow(root, flow) {
    return overflows(flow) || overflows(root);
  }

  /** How much of the box the copy actually covers, 0..1.

   *  Overflow is easy to detect, but its opposite is not: balanced columns
   *  all finish at the same height, so a block that only fills two thirds of
   *  its box still reports scrollHeight === clientHeight. Parking a zero-size
   *  marker at the end of the copy gives us the true depth the type reaches,
   *  in the last column, for single- and multi-column copy alike. */
  function endMarker(flow) {
    let marker = flow.querySelector(":scope > [data-fit-end]");
    if (!marker) {
      marker = document.createElement("span");
      marker.setAttribute("data-fit-end", "");
      marker.style.cssText = "display:inline-block;width:0;height:0;overflow:hidden;";
      flow.appendChild(marker);
    } else {
      flow.appendChild(marker); // keep it last after any trimming
    }
    return marker;
  }

  function fillRatio(flow) {
    if (!flow) return 1;
    const box = flow.getBoundingClientRect();
    if (box.height <= 0) return 1;
    const end = endMarker(flow).getBoundingClientRect();
    return Math.min(1, Math.max(0, (end.bottom - box.top) / box.height));
  }

  function setScale(root, s) {
    root.style.setProperty("--fit", s.toFixed(4));
    void root.offsetHeight; // force reflow before the next measurement
  }

  /** Largest scale in [lo, hi] that still fits. Returns null if even lo fails. */
  function search(root, flow, lo, hi) {
    setScale(root, lo);
    if (anyOverflow(root, flow)) return null;
    let best = lo;
    for (let i = 0; i < STEPS; i++) {
      const mid = (lo + hi) / 2;
      setScale(root, mid);
      if (anyOverflow(root, flow)) {
        hi = mid;
      } else {
        best = mid;
        lo = mid;
      }
    }
    return best;
  }

  function trimToFit(root, flow, trimHost) {
    const removed = [];
    const kids = Array.from(trimHost.children);
    // Never strip a block down to nothing — keep the opening paragraph.
    for (let i = kids.length - 1; i >= 1; i--) {
      if (!anyOverflow(root, flow)) break;
      const el = kids[i];
      if (el.dataset.fitKeep === "true") continue;
      el.remove();
      removed.push(el);
    }
    return removed.length;
  }

  function markJump(root, flow, trimHost) {
    const label = root.dataset.fitJump;
    if (!label) return false;
    const jump = document.createElement("p");
    jump.className = "story__jump";
    jump.setAttribute("lang", "ta");
    jump.textContent = label;
    trimHost.appendChild(jump);
    // The jump line itself takes space; give it room by cutting one more para.
    let guard = 0;
    while (anyOverflow(root, flow) && guard++ < 40) {
      const kids = Array.from(trimHost.children);
      const victim = kids[kids.length - 2];
      if (!victim || kids.length <= 2) break;
      victim.remove();
    }
    return true;
  }

  function fitOne(root) {
    const flow = root.querySelector("[data-fit-flow]") || root;
    const trimHost = root.querySelector("[data-fit-trim]") || flow;
    const id = root.dataset.fitId || "(unnamed)";
    const record = { id, scale: 1, trimmed: 0, jumped: false, overflow: false, fill: 1 };

    setScale(root, 1);

    if (!anyOverflow(root, flow)) {
      // Copy is short for its box. Open the type up to the largest size that
      // still fits, so the block sets full rather than trailing off into
      // white space at the foot of the last column.
      const grown = search(root, flow, 1, MAX_SCALE);
      record.scale = grown === null ? 1 : grown;
      setScale(root, record.scale);
      record.fill = fillRatio(flow);
      return record;
    }

    // Copy is long — shrink.
    const shrunk = search(root, flow, MIN_SCALE, 1);
    if (shrunk !== null) {
      record.scale = shrunk;
      setScale(root, shrunk);
      record.fill = fillRatio(flow);
      return record;
    }

    // Still too long at the floor: cut copy.
    record.scale = MIN_SCALE;
    setScale(root, MIN_SCALE);
    record.trimmed = trimToFit(root, flow, trimHost);
    if (record.trimmed > 0) record.jumped = markJump(root, flow, trimHost);
    record.overflow = anyOverflow(root, flow);
    record.fill = fillRatio(flow);
    return record;
  }

  /** Shrink a single line — the nameplate — until it fits its measure. */
  function fitWidth(el) {
    const base = parseFloat(getComputedStyle(el).fontSize);
    let lo = 0.4, hi = 1;
    if (el.scrollWidth <= el.clientWidth + SLACK_PX) return 1;
    for (let i = 0; i < STEPS; i++) {
      const mid = (lo + hi) / 2;
      el.style.fontSize = (base * mid).toFixed(3) + "px";
      if (el.scrollWidth > el.clientWidth + SLACK_PX) hi = mid;
      else lo = mid;
    }
    el.style.fontSize = (base * lo).toFixed(3) + "px";
    return lo;
  }

  function run() {
    const report = [];
    document.querySelectorAll("[data-fit-width]").forEach(fitWidth);
    document.querySelectorAll("[data-fit]").forEach((root) => {
      try {
        report.push(fitOne(root));
      } catch (err) {
        report.push({ id: root.dataset.fitId || "(unnamed)", error: String(err) });
      }
    });
    window.__fitReport = report;
    document.documentElement.setAttribute("data-fit-done", "true");
    return report;
  }

  if (document.readyState === "complete") {
    run();
  } else {
    window.addEventListener("load", run, { once: true });
  }

  window.__runFit = run;
})();
