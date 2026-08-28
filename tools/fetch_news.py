#!/usr/bin/env python3
"""Fetch the day's news and compose a draft edition.

    python3 tools/fetch_news.py                       # today, to content/draft-<date>.json
    python3 tools/fetch_news.py --dry-run             # just list what the feeds carry
    python3 tools/fetch_news.py --check-feeds         # verify every feed still works
    python3 tools/fetch_news.py --offline             # rebuild from the cache
    python3 tools/fetch_news.py --window 14           # include last night's copy too

Then build it:

    python3 build.py content/draft-2026-08-28.json --preview

What you get is a draft. The layout, the sourcing and the credits are
finished; the prose is still each publisher's own summary, in their own
language. Rewrite it before you call it your paper — the blocks are marked
"draft": true so you can find them.

This does not, and cannot, verify what the feeds say. It reproduces their
headlines and summaries and records where each came from. Treat it as a wire
desk, not a reporter.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tamilpaper import compose, news  # noqa: E402

DEFAULT_FEEDS = ROOT / "content" / "feeds.json"
CACHE = ROOT / ".cache" / "feeds"


def _print_report(report: news.FetchReport, verbose: bool = True) -> None:
    if verbose:
        for name, count in report.ok:
            print(f"  · {name:<28} {count:>3} item(s)")
    for name, error in report.failed:
        print(f"  ✗ {name:<28} {error}", file=sys.stderr)
    bits = [f"{report.total} stories"]
    if report.dropped_old:
        bits.append(f"{report.dropped_old} outside the day")
    if report.dropped_duplicate:
        bits.append(f"{report.dropped_duplicate} duplicates")
    if report.failed:
        bits.append(f"{len(report.failed)} feed(s) failed")
    print("  " + ", ".join(bits))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feeds", default=str(DEFAULT_FEEDS), help="feed configuration JSON")
    ap.add_argument("-o", "--output", help="edition file to write (default: content/draft-<date>.json)")
    ap.add_argument("--date", help="the day to build, YYYY-MM-DD (default: today in IST)")
    ap.add_argument("--window", type=int, default=0, metavar="HOURS",
                    help="also keep stories from this many hours before the day started")
    ap.add_argument("--press", default="auto",
                    help="press preset, or 'auto' to pick the sheet the copy fills")
    ap.add_argument("--cols", type=int, help="page columns (default: the preset's)")
    ap.add_argument("--rows", type=int, help="page rows (default: the preset's)")
    ap.add_argument("--name", default="பீனிக்ஸ் மலர் செய்தி", help="the paper's name")
    ap.add_argument("--latin", default="Phoenix Malar Seithi", help="the name in Latin script")
    ap.add_argument("--edition", default="மாலைப் பதிப்பு", help="edition label")
    ap.add_argument("--language", choices=["ta", "en", "any"], default="any",
                    help="keep only feeds in this language")
    ap.add_argument("--max-per-section", type=int, default=14,
                    help="most stories to carry per section")
    ap.add_argument("--offline", action="store_true", help="read the cache instead of the network")
    ap.add_argument("--no-cache", action="store_true", help="do not write the cache")
    ap.add_argument("--dry-run", action="store_true", help="list what was fetched and stop")
    ap.add_argument("--check-feeds", action="store_true",
                    help="fetch every feed, report which work, and stop")
    args = ap.parse_args(argv)

    try:
        feeds = news.load_feeds(args.feeds)
    except (OSError, ValueError, KeyError) as err:
        print(f"error: {args.feeds}: {err}", file=sys.stderr)
        return 2

    if args.language != "any":
        feeds = [f for f in feeds if f.language == args.language]
        if not feeds:
            print(f"error: no feeds in language {args.language!r}", file=sys.stderr)
            return 2

    config = json.loads(Path(args.feeds).read_text(encoding="utf-8"))
    sections = config.get("sections") or sorted({f.section for f in feeds})
    accents = config.get("accents") or {}

    if args.date:
        try:
            day = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=news.IST)
        except ValueError:
            print(f"error: --date must be YYYY-MM-DD, got {args.date!r}", file=sys.stderr)
            return 2
        day += timedelta(hours=18)     # an evening edition's clock
    else:
        day = datetime.now(news.IST)

    if args.check_feeds:
        print(f"Checking {len(feeds)} feed(s)...")
        good = 0
        for feed in feeds:
            try:
                stories = news.parse_feed(news.fetch_bytes(feed.url), feed)
                newest = max((s.published for s in stories if s.published), default=None)
                stamp = f", newest {newest:%Y-%m-%d %H:%M}" if newest else ", undated"
                print(f"  · {feed.name:<24} {feed.section:<12} {len(stories):>3} item(s){stamp}")
                good += 1
            except news.FeedError as err:
                print(f"  ✗ {feed.name:<24} {feed.section:<12} {err}", file=sys.stderr)
        print(f"{good} of {len(feeds)} feed(s) usable")
        return 0 if good else 1

    print(f"Fetching {len(feeds)} feed(s) for {day:%Y-%m-%d}"
          + (" (offline)" if args.offline else "") + "...")
    stories, report = news.fetch(
        feeds, day=day, window_hours=args.window,
        cache_dir=None if args.no_cache else CACHE, offline=args.offline)
    _print_report(report)

    if not stories:
        print("error: no stories for that day. Try --window 24, or --check-feeds.",
              file=sys.stderr)
        return 1

    # Cap each section so one prolific feed cannot take over the paper.
    capped: list[news.Story] = []
    counts: dict[str, int] = {}
    for story in stories:
        if counts.get(story.section, 0) >= args.max_per_section:
            continue
        counts[story.section] = counts.get(story.section, 0) + 1
        capped.append(story)

    if args.dry_run:
        for section in sections + [s for s in counts if s not in sections]:
            items = [s for s in capped if s.section == section]
            if not items:
                continue
            print(f"\n{section} ({len(items)})")
            for story in items:
                when = f"{story.published:%H:%M}" if story.published else "  —  "
                print(f"  {when}  [{story.source}] {story.title[:96]}")
        return 0

    from tamilpaper import press as press_module

    chosen = args.press
    if chosen == "auto":
        chosen = compose.choose_press(capped, press_module.PRESETS)
        print(f"  sheet: {chosen} (chosen to fit the copy; override with --press)")
    try:
        preset = press_module.get(chosen)
    except ValueError as err:
        print(f"error: {err}", file=sys.stderr)
        return 2
    cols = args.cols or preset.cols
    rows = args.rows or preset.rows

    try:
        edition = compose.compose(
            capped, sections=sections, cols=cols, rows=rows, day=day,
            preset=chosen, name=args.name, latin=args.latin,
            edition_label=args.edition, accents=accents)
    except compose.ComposeError as err:
        print(f"error: {err}", file=sys.stderr)
        return 1

    out = Path(args.output) if args.output else ROOT / "content" / f"draft-{day:%Y-%m-%d}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(edition, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    drafts = sum(1 for p in edition["pages"] for b in p["blocks"] if b.get("draft"))
    print(f"\nWrote {out}")
    print(f"  {len(edition['pages'])} page(s), {len(capped)} stories, "
          f"{drafts} block(s) still carrying feed copy")
    print(f"  Build it:  python3 build.py {out} --preview")
    print("  Then rewrite the drafted blocks in your own words before publishing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
