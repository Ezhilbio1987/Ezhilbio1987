"""Print the laid-out page to PDF with headless Chromium.

Chromium is what makes this work at all: it shapes Tamil through HarfBuzz, so
vowel signs reorder and ligatures form correctly, and it embeds the fonts in
the PDF as real Unicode text — the resulting file is searchable and
copy-pastable, unlike editions set in the legacy TAB/TAM encodings.
"""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def _to_css_length(value: str) -> str:
    return value.strip()


def _chromium_path() -> str | None:
    """Locate a Chromium to drive.

    Returning None lets Playwright use the browser it downloaded itself, which
    is the normal case. Some environments ship a pre-installed Chromium whose
    build number does not match the installed Playwright; point at it
    explicitly rather than downloading a second copy.
    """
    override = os.environ.get("TAMILPAPER_CHROMIUM")
    if override:
        return override

    roots = [Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers"))]
    for root in roots:
        if not root.is_dir():
            continue
        for candidate in sorted(root.glob("chromium-*/chrome-linux/chrome"), reverse=True):
            if os.access(candidate, os.X_OK):
                return str(candidate)
    return None


def compress(pdf_path: Path) -> tuple[int, int]:
    """Squeeze the finished PDF, if the tooling for it is installed.

    Chromium writes a correct PDF but a loose one — objects go out
    uncompressed and unreferenced ones are left behind. Repacking typically
    halves the file, which matters: these are read on phones, where a large
    download simply stalls.

    Returns (before, after) in bytes; equal values mean nothing was done.
    """
    before = pdf_path.stat().st_size
    try:
        import pymupdf                      # optional
    except ImportError:
        return before, before
    try:
        document = pymupdf.open(pdf_path)
        packed = document.tobytes(garbage=4, deflate=True, clean=True)
        document.close()
    except Exception:
        return before, before               # never lose a good PDF to this
    if len(packed) < before:
        pdf_path.write_bytes(packed)
        return before, len(packed)
    return before, before


def print_pdf(html_path: Path, pdf_path: Path, press: dict,
              preview_png: Path | None = None, preview_dpi: int = 96) -> list[dict]:
    """Render ``html_path`` to ``pdf_path``. Returns the copy-fitting report."""
    html_path = Path(html_path).resolve()
    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        launch: dict = {"args": ["--font-render-hinting=none"]}
        executable = _chromium_path()
        if executable:
            launch["executable_path"] = executable
        browser = p.chromium.launch(**launch)
        page = browser.new_page()
        page.goto(html_path.as_uri(), wait_until="load")
        page.emulate_media(media="print")

        # Fonts must be in before anything is measured, or every box is fitted
        # against fallback metrics.
        page.evaluate("() => document.fonts.ready")
        page.wait_for_function("() => document.documentElement.dataset.fitDone === 'true'",
                               timeout=60_000)
        # Print media can change metrics; re-fit once under print rules.
        report = page.evaluate("() => window.__runFit()")

        page.pdf(
            path=str(pdf_path),
            width=_to_css_length(press["width"]),
            height=_to_css_length(press["height"]),
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
            prefer_css_page_size=True,
        )

        if preview_png:
            preview_png.parent.mkdir(parents=True, exist_ok=True)
            page.emulate_media(media="screen")
            page.screenshot(path=str(preview_png), full_page=True)

        browser.close()

    return report
