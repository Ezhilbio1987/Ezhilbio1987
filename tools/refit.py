#!/usr/bin/env python3
"""Resize an edition's blocks to the copy they actually hold.

Writing to a fixed page is a two-pass job. You write the copy, then you find
out how much room it wants, then you resize the holes. The build already
measures the second part — it reports what fraction of its box each block
fills — so this closes the loop: it reads those numbers, scales every block
to what it needs, and re-packs each page so the grid is covered exactly.

    python3 tools/refit.py content/daily.json          # resize in place
    python3 tools/refit.py content/daily.json --dry-run

It never edits copy. If a page ends up with cells to spare it says so, and
the fix is more news, not bigger type.
"""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

TARGET_FILL = 0.96      # what a well-made block should reach
MIN_ROWS = 2


def measure(edition_path: Path) -> dict[str, float]:
    """Build the edition and return each block's fill fraction."""
    from tamilpaper import content, pdf, render

    data = content.load(edition_path)
    html = ROOT / "output" / "_refit.html"
    out = ROOT / "output" / "_refit.pdf"
    render.render_html(data, html)
    report = pdf.print_pdf(html, out, data["press"])
    html.unlink(missing_ok=True)
    out.unlink(missing_ok=True)
    return {item["id"]: float(item.get("fill", 1.0)) for item in report
            if not item.get("error")}


def repack(page: dict, wanted: dict[str, int]) -> None:
    """Lay the page's blocks out in full-width bands at their wanted sizes.

    Order is preserved — the editor decided it — and only the shape changes.
    """
    cols, rows = page["cols"], page["rows"]
    blocks = page["blocks"]

    # Widths stay as the editor set them; only heights are recomputed, so a
    # band is a run of blocks whose widths sum to the page width.
    bands: list[list[dict]] = []
    run: list[dict] = []
    width = 0
    for block in blocks:
        run.append(block)
        width += block["col"]
        if width >= cols:
            bands.append(run)
            run, width = [], 0
    if run:
        bands.append(run)

    heights = []
    for band in bands:
        need = max(
            max(MIN_ROWS, math.ceil(wanted.get(b["id"], b["col"] * b["row"]) / b["col"]))
            for b in band)
        heights.append(need)

    # Fit the bands to the page: trim the roomiest first, then grow the
    # tightest, until the heights add up to exactly the rows available.
    while sum(heights) > rows:
        i = heights.index(max(heights))
        if heights[i] <= MIN_ROWS:
            break
        heights[i] -= 1
    while sum(heights) < rows:
        i = heights.index(min(heights))
        heights[i] += 1

    for band, height in zip(bands, heights):
        for block in band:
            block["row"] = height


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edition")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--passes", type=int, default=2,
                    help="measure-and-resize rounds (default 2)")
    args = ap.parse_args(argv)

    path = Path(args.edition)
    data = json.loads(path.read_text(encoding="utf-8"))

    for round_no in range(1, args.passes + 1):
        if not args.dry_run or round_no == 1:
            scratch = path if not args.dry_run else path
        fills = measure(path)
        moved = 0
        for page in data["pages"]:
            wanted = {}
            for block in page["blocks"]:
                cells = block["col"] * block["row"]
                fill = fills.get(block["id"])
                if fill is None:
                    wanted[block["id"]] = cells
                    continue
                wanted[block["id"]] = max(block["col"] * MIN_ROWS,
                                          math.ceil(cells * fill / TARGET_FILL))
            before = [(b["id"], b["row"]) for b in page["blocks"]]
            repack(page, wanted)
            moved += sum(1 for (i, r), b in zip(before, page["blocks"]) if r != b["row"])
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        print(f"pass {round_no}: resized {moved} block(s)")
        if not moved:
            break

    for page in data["pages"]:
        used = sum(b["col"] * b["row"] for b in page["blocks"])
        grid = page["cols"] * page["rows"]
        if used != grid:
            print(f"warning: page {page['number']} covers {used} of {grid} cells",
                  file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
