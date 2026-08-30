#!/usr/bin/env python3
"""End-to-end tests for the news pipeline, run without a network.

The fixtures under tests/fixtures/ stand in for live feeds: two RSS 2.0 feeds
in Tamil, an Atom feed and two more RSS feeds in English, plus one file that
is deliberately malformed. They are placed in a cache directory under the
names the fetcher would give them, and the fetcher is run in offline mode, so
everything from parsing to a printed PDF is exercised exactly as it would be
on a live run.

    python3 tests/test_pipeline.py
"""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(ROOT / "src"))

from tamilpaper import compose, content, news, press  # noqa: E402

DAY = datetime(2026, 8, 28, 18, 0, tzinfo=news.IST)

FEEDS = [
    (news.Feed("மாதிரி நாளிதழ்", "https://example.test/tamilnadu.rss", "தமிழ்நாடு", "ta"),
     "tamilnadu_rss.xml"),
    (news.Feed("மாதிரி நாளிதழ்", "https://example.test/india.rss", "இந்தியா", "ta"),
     "india_rss.xml"),
    (news.Feed("Sample Wire", "https://example.test/world.atom", "உலகம்", "en"),
     "world_atom.xml"),
    (news.Feed("Sample Business Wire", "https://example.test/business.rss", "வணிகம்", "en"),
     "business_rss.xml"),
    (news.Feed("Sample Sport Wire", "https://example.test/sport.rss", "விளையாட்டு", "en"),
     "sport_rss.xml"),
]

SECTIONS = ["தமிழ்நாடு", "இந்தியா", "உலகம்", "வணிகம்", "விளையாட்டு"]


def seed_cache(directory: Path, extra: list[tuple[news.Feed, str]] | None = None) -> list[news.Feed]:
    """Write the fixtures into a cache directory under the fetcher's names."""
    directory.mkdir(parents=True, exist_ok=True)
    feeds = []
    for feed, fixture in FEEDS + (extra or []):
        stem = hashlib.sha1(feed.url.encode()).hexdigest()[:12]
        shutil.copyfile(FIXTURES / fixture, directory / f"{stem}.xml")
        feeds.append(feed)
    return feeds


class TestText(unittest.TestCase):
    def test_strips_markup_and_entities(self):
        self.assertEqual(
            news.clean_text("<p>Hello &amp; <b>goodbye</b></p>\n\n  spaced"),
            "Hello & goodbye spaced")

    def test_double_escaped_entities(self):
        self.assertEqual(news.clean_text("&lt;p&gt;a &amp;amp; b&lt;/p&gt;"), "a & b")

    def test_empty(self):
        self.assertEqual(news.clean_text(None), "")

    def test_title_folding_ignores_case_accents_punctuation(self):
        self.assertEqual(news.normalise_title("  The  Café—Story!  "), "the cafe story")

    def test_tamil_marks_survive_folding(self):
        """A Tamil vowel sign is a combining character. Folding it away would
        collapse unrelated headlines into one and lose real stories."""
        self.assertEqual(news.normalise_title("சென்னை மெட்ரோ!"), "சென்னை மெட்ரோ")

    def test_distinct_tamil_headlines_stay_distinct(self):
        self.assertNotEqual(news.normalise_title("மெட்ரோ ரயில் திட்டம்"),
                            news.normalise_title("மாட்ரா ரயல் தட்டம்"))


class TestDates(unittest.TestCase):
    def test_rfc822(self):
        parsed = news.parse_date("Fri, 28 Aug 2026 18:30:00 +0530")
        self.assertEqual(parsed.astimezone(news.IST).hour, 18)

    def test_iso_with_z(self):
        self.assertEqual(news.parse_date("2026-08-28T18:30:00Z").hour, 18)

    def test_date_only(self):
        self.assertEqual(news.parse_date("2026-08-28").day, 28)

    def test_naive_gets_utc(self):
        self.assertIsNotNone(news.parse_date("2026-08-28T10:00:00").tzinfo)

    def test_garbage_is_none(self):
        self.assertIsNone(news.parse_date("not a date"))
        self.assertIsNone(news.parse_date(None))


class TestParsing(unittest.TestCase):
    def _parse(self, fixture, feed=None):
        feed = feed or news.Feed("F", "https://example.test/f", "S")
        return news.parse_feed((FIXTURES / fixture).read_bytes(), feed)

    def test_rss(self):
        stories = self._parse("tamilnadu_rss.xml")
        self.assertEqual(len(stories), 6)
        self.assertTrue(stories[0].title.startswith("தூய்மைப்"))
        self.assertIn("2,500", stories[0].summary)
        self.assertNotIn("<p>", stories[0].summary)

    def test_atom(self):
        stories = self._parse("world_atom.xml")
        self.assertEqual(len(stories), 3)
        self.assertEqual(stories[0].url, "https://example.test/world/strait")
        self.assertTrue(all(s.published for s in stories))

    def test_atom_html_content_is_cleaned(self):
        stories = self._parse("world_atom.xml")
        self.assertNotIn("<p>", stories[1].summary)
        self.assertIn("temporary channel", stories[1].summary)

    def test_limit_is_honoured(self):
        feed = news.Feed("F", "https://example.test/f", "S", limit=2)
        self.assertEqual(len(self._parse("tamilnadu_rss.xml", feed)), 2)

    def test_malformed_xml_raises_named_error(self):
        feed = news.Feed("Broken Feed", "https://example.test/b", "S")
        with self.assertRaises(news.FeedError) as caught:
            news.parse_feed((FIXTURES / "broken.xml").read_bytes(), feed)
        self.assertIn("Broken Feed", str(caught.exception))

    def test_feed_without_items_raises(self):
        feed = news.Feed("Empty", "https://example.test/e", "S")
        with self.assertRaises(news.FeedError):
            news.parse_feed(b"<rss><channel></channel></rss>", feed)


class TestFetch(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.feeds = seed_cache(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_offline_fetch_reads_every_feed(self):
        stories, report = news.fetch(self.feeds, day=DAY, cache_dir=self.tmp, offline=True)
        self.assertEqual(len(report.failed), 0, report.failed)
        self.assertEqual(len(report.ok), len(self.feeds))
        self.assertGreater(len(stories), 8)

    def test_old_story_is_dropped(self):
        stories, report = news.fetch(self.feeds, day=DAY, cache_dir=self.tmp, offline=True)
        self.assertGreaterEqual(report.dropped_old, 1)
        self.assertFalse(any("பழைய செய்தி" in s.summary for s in stories))

    def test_undated_story_is_kept(self):
        stories, _ = news.fetch(self.feeds, day=DAY, cache_dir=self.tmp, offline=True)
        self.assertTrue(any(s.url.endswith("/undated") for s in stories))

    def test_duplicate_across_feeds_is_dropped_once(self):
        stories, report = news.fetch(self.feeds, day=DAY, cache_dir=self.tmp, offline=True)
        self.assertEqual(report.dropped_duplicate, 1)
        metro = [s for s in stories if "metro-md" in s.url]
        self.assertEqual(len(metro), 1)

    def test_window_admits_the_previous_evening(self):
        yesterday_only = [f for f, _ in FEEDS if f.section == "விளையாட்டு"]
        without, _ = news.fetch(yesterday_only, day=DAY, cache_dir=self.tmp, offline=True)
        with_window, _ = news.fetch(yesterday_only, day=DAY, window_hours=36,
                                    cache_dir=self.tmp, offline=True)
        self.assertGreater(len(with_window), len(without))

    def test_stories_come_back_newest_first(self):
        stories, _ = news.fetch(self.feeds, day=DAY, cache_dir=self.tmp, offline=True)
        dated = [s.published for s in stories if s.published]
        self.assertEqual(dated, sorted(dated, reverse=True))

    def test_one_bad_feed_does_not_sink_the_edition(self):
        broken = news.Feed("Broken Feed", "https://example.test/broken.rss", "தமிழ்நாடு")
        feeds = seed_cache(self.tmp, extra=[(broken, "broken.xml")])
        stories, report = news.fetch(feeds, day=DAY, cache_dir=self.tmp, offline=True)
        self.assertEqual(len(report.failed), 1)
        self.assertEqual(report.failed[0][0], "Broken Feed")
        self.assertGreater(len(stories), 8)

    def test_missing_cache_in_offline_mode_is_reported(self):
        absent = news.Feed("Nothing Cached", "https://example.test/none.rss", "தமிழ்நாடு")
        _, report = news.fetch([absent], day=DAY, cache_dir=self.tmp, offline=True)
        self.assertEqual(len(report.failed), 1)


class TestCompose(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        feeds = seed_cache(self.tmp)
        self.stories, _ = news.fetch(feeds, day=DAY, cache_dir=self.tmp, offline=True)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _edition(self, cols=5, rows=11):
        return compose.compose(self.stories, sections=SECTIONS, cols=cols, rows=rows,
                               day=DAY, preset="tabloid")

    def test_every_page_grid_is_filled_exactly(self):
        edition = self._edition()
        for page in edition["pages"]:
            used = sum(b["col"] * b["row"] for b in page["blocks"])
            self.assertEqual(used, page["cols"] * page["rows"],
                             f"page {page['number']} covers {used} cells")

    def test_no_block_exceeds_the_page(self):
        edition = self._edition()
        for page in edition["pages"]:
            for block in page["blocks"]:
                self.assertLessEqual(block["col"], page["cols"])
                self.assertLessEqual(block["row"], page["rows"])

    def test_every_story_block_credits_its_source(self):
        edition = self._edition()
        for page in edition["pages"]:
            for block in page["blocks"]:
                if block["type"] == "story":
                    self.assertTrue(block["source"].startswith("ஆதாரம்:"), block["source"])

    def test_body_copy_is_only_what_the_feed_gave(self):
        """The composer must never invent prose. Every sentence it lays out has
        to appear in the summary it came from."""
        edition = self._edition()
        summaries = {s.title: s.summary for s in self.stories}
        for page in edition["pages"]:
            for block in page["blocks"]:
                if block["type"] != "story":
                    continue
                original = summaries.get(block["headline"], "")
                for paragraph in block["body"]:
                    stripped = paragraph.rstrip(".").strip()
                    self.assertIn(stripped[:40], original,
                                  f"invented copy in {block['id']}: {paragraph[:60]}")

    def test_no_sources_box_unless_asked_for(self):
        """Apparatus is off by default: the credit under each story is the
        attribution, and a page of URLs is not news."""
        edition = self._edition()
        boxes = [b for p in edition["pages"] for b in p["blocks"]
                 if b["type"] == "sources"]
        self.assertEqual(boxes, [])

    def test_sources_box_can_be_asked_for(self):
        edition = compose.compose(self.stories, sections=SECTIONS, cols=5, rows=11,
                                  day=DAY, preset="tabloid", sources_box=True)
        last = edition["pages"][-1]
        boxes = [b for b in last["blocks"] if b["type"] == "sources"]
        self.assertEqual(len(boxes), 1)
        self.assertGreaterEqual(len(boxes[0]["items"]), 3)

    def test_first_page_is_the_front(self):
        edition = self._edition()
        self.assertEqual(edition["pages"][0]["kind"], "front")
        self.assertTrue(all(p["kind"] == "inner" for p in edition["pages"][1:]))

    def test_drafted_blocks_are_marked(self):
        """Every block still carrying a publisher's own words must say so, so
        the editor can find what is left to rewrite."""
        edition = self._edition()
        blocks = [b for p in edition["pages"] for b in p["blocks"]]
        carrying = [b for b in blocks if b["type"] in {"story", "briefs"}]
        self.assertTrue(carrying)
        self.assertTrue(all(b.get("draft") for b in carrying))

    def test_short_wire_items_become_briefs_not_underfilled_stories(self):
        """A two-sentence summary cannot hold a story block. Sizing it as one
        is what leaves a page of quarter-filled boxes."""
        edition = self._edition()
        for page in edition["pages"]:
            for block in page["blocks"]:
                if block["type"] != "story":
                    continue
                words = sum(len(p.split()) for p in block["body"])
                self.assertGreaterEqual(
                    words, compose.MIN_STORY_CELLS * compose.WORDS_PER_CELL * 0.5,
                    f"{block['id']} was set as a story on {words} words")

    def test_page_count_follows_the_copy(self):
        """Fifteen short items are one page, not one page per section."""
        edition = self._edition()
        self.assertLessEqual(len(edition["pages"]), 2)

    def test_press_is_chosen_to_fit_the_copy(self):
        from tamilpaper import press as press_module
        chosen = compose.choose_press(self.stories, press_module.PRESETS)
        self.assertIn(chosen, press_module.PRESETS)
        # This little copy belongs on a small sheet.
        self.assertIn(chosen, {"a4", "a3"})

    def test_empty_input_is_refused(self):
        with self.assertRaises(compose.ComposeError):
            compose.compose([], sections=SECTIONS, cols=5, rows=11, day=DAY)

    def test_composes_for_every_press_preset(self):
        for key, preset in press.PRESETS.items():
            with self.subTest(preset=key):
                edition = compose.compose(self.stories, sections=SECTIONS,
                                          cols=preset.cols, rows=preset.rows,
                                          day=DAY, preset=key)
                for page in edition["pages"]:
                    used = sum(b["col"] * b["row"] for b in page["blocks"])
                    self.assertEqual(used, page["cols"] * page["rows"])


class TestEndToEnd(unittest.TestCase):
    """The composed edition must survive the real loader and printer."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        feeds = seed_cache(cls.tmp)
        stories, _ = news.fetch(feeds, day=DAY, cache_dir=cls.tmp, offline=True)
        chosen = compose.choose_press(stories, press.PRESETS)
        preset = press.get(chosen)
        edition = compose.compose(stories, sections=SECTIONS,
                                  cols=preset.cols, rows=preset.rows,
                                  day=DAY, preset=chosen)
        cls.path = cls.tmp / "draft.json"
        cls.path.write_text(json.dumps(edition, ensure_ascii=False, indent=2),
                            encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_loader_accepts_the_composed_edition(self):
        loaded = content.load(self.path)
        self.assertGreaterEqual(len(loaded["pages"]), 1)
        self.assertEqual(loaded["warnings"], [], loaded["warnings"])

    def test_it_prints_to_a_pdf(self):
        out = self.tmp / "draft.pdf"
        result = subprocess.run(
            [sys.executable, str(ROOT / "build.py"), str(self.path), "-o", str(out), "--quiet"],
            capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 20_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)

class NewEditionSkeleton(unittest.TestCase):
    """The morning routine starts from a generated skeleton, so it has to be
    valid on any date — a broken one means no paper that morning."""

    def _build(self, iso):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "new_edition", ROOT / "tools" / "new_edition.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, mod.build(date.fromisoformat(iso))

    def test_every_page_covers_its_grid(self):
        for iso in ("2026-08-31", "2026-09-15", "2027-01-01", "2026-12-25"):
            _, edition = self._build(iso)
            for page in edition["pages"]:
                used = sum(b["col"] * b["row"] for b in page["blocks"])
                self.assertEqual(used, page["cols"] * page["rows"],
                                 f"{iso} page {page['number']} leaves the grid uncovered")

    def test_it_loads_like_any_edition(self):
        """A skeleton that will not load is a morning with no paper."""
        _, edition = self._build("2026-08-31")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "skeleton.json"
            path.write_text(json.dumps(edition, ensure_ascii=False), encoding="utf-8")
            loaded = content.load(path)
        self.assertEqual(len(loaded["pages"]), 3)

    def test_weekday_is_named_in_tamil(self):
        _, edition = self._build("2026-08-31")          # a Monday
        self.assertEqual(edition["paper"]["weekday_ta"], "திங்கட்கிழமை")

    def test_tamil_month_is_blank_rather_than_guessed(self):
        """Counting off the one sourced anchor is safe inside Aavani and
        nowhere else, so a far-off date must leave the field empty."""
        mod, _ = self._build("2026-08-31")
        self.assertEqual(mod.tamil_month_day(date(2026, 8, 30)), "ஆவணி 13")
        self.assertEqual(mod.tamil_month_day(date(2027, 3, 1)), "")

