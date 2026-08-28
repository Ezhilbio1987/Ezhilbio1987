#!/usr/bin/env python3
"""Build a press-ready Tamil newspaper PDF from an edition file.

    python3 build.py                                  # build content/edition.json
    python3 build.py content/edition.json -o out.pdf
    python3 build.py --press a3 --preview
    python3 build.py --list-presets
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tamilpaper import content, pdf, press, render  # noqa: E402

ROOT = Path(__file__).resolve().parent
DEFAULT_EDITION = ROOT / "content" / "edition.json"


UNDERFILL = 0.88  # below this, the block leaves a visible hole in the page


def _report_line(item: dict) -> str:
    if item.get("error"):
        return f"  ✗ {item['id']}: {item['error']}"
    bits = [f"type {item['scale'] * 100:.0f}%", f"fills {item.get('fill', 1) * 100:.0f}%"]
    if item.get("trimmed"):
        bits.append(f"{item['trimmed']} para cut")
    if item.get("jumped"):
        bits.append("jump line set")
    if item.get("overflow"):
        bits.append("STILL OVERSET")
    if item.get("fill", 1) < UNDERFILL:
        bits.append("short — add copy or shrink the block")
    mark = ("✗" if item.get("overflow")
            else "!" if item.get("trimmed") or item.get("fill", 1) < UNDERFILL
            else "·")
    return f"  {mark} {item['id']}: {', '.join(bits)}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Lay out a Tamil newspaper edition and print it to PDF.")
    ap.add_argument("edition", nargs="?", default=str(DEFAULT_EDITION),
                    help="edition JSON file (default: content/edition.json)")
    ap.add_argument("-o", "--output", help="PDF path (default: output/<edition>.pdf)")
    ap.add_argument("--press", help="override the press preset from the edition file")
    ap.add_argument("--preview", action="store_true",
                    help="also write a full-length PNG proof next to the PDF")
    ap.add_argument("--keep-html", action="store_true",
                    help="keep the intermediate HTML for inspection")
    ap.add_argument("--quiet", action="store_true", help="only report problems")
    ap.add_argument("--list-presets", action="store_true", help="show press presets and exit")
    args = ap.parse_args(argv)

    if args.list_presets:
        for key, value in press.PRESETS.items():
            marker = "*" if key == press.DEFAULT else " "
            print(f" {marker} {key:<20} {value.width} × {value.height:<8} "
                  f"grid {value.cols}×{value.rows}   {value.label}")
        return 0

    edition_path = Path(args.edition)
    if not edition_path.exists():
        print(f"error: no edition file at {edition_path}", file=sys.stderr)
        return 2

    try:
        if args.press:
            press.get(args.press)  # fail fast on a bad name
        edition = content.load(edition_path)
        if args.press:
            edition["press"] = press.get(args.press).as_dict()
            for page in edition["pages"]:
                page.setdefault("cols", edition["press"]["cols"])
    except (content.ContentError, KeyError, ValueError) as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    out_pdf = Path(args.output) if args.output else ROOT / "output" / f"{edition_path.stem}.pdf"
    html_path = ROOT / "output" / f"{edition_path.stem}.html"
    preview = out_pdf.with_suffix(".png") if args.preview else None

    render.render_html(edition, html_path)
    report = pdf.print_pdf(html_path, out_pdf, edition["press"], preview_png=preview)

    if not args.keep_html:
        html_path.unlink(missing_ok=True)

    problems = [r for r in report if r.get("overflow") or r.get("error")]
    short = [r for r in report if r.get("fill", 1) < UNDERFILL]
    adjusted = [r for r in report if r.get("trimmed") or r.get("error")
                or r.get("fill", 1) < UNDERFILL or abs(r.get("scale", 1) - 1) > 0.02]

    if not args.quiet:
        pages = len(edition["pages"])
        size = f"{edition['press']['width']} × {edition['press']['height']}"
        print(f"{edition['paper']['name']} — {pages} page(s), {size}")
        print(f"  PDF     {out_pdf}")
        if preview:
            print(f"  proof   {preview}")
        if adjusted:
            print(f"  copy fitting ({len(adjusted)} of {len(report)} blocks adjusted):")
            for item in adjusted:
                print(_report_line(item))

    for warning in edition.get("warnings", []):
        print(f"warning: {warning}", file=sys.stderr)
    for item in problems:
        print(f"warning: {item['id']} could not be fitted into its box", file=sys.stderr)
    for item in short:
        print(f"warning: {item['id']} fills only {item['fill']:.0%} of its box",
              file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
