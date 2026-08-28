"""Fetching a day's news from syndication feeds.

The paper is only as good as what it is built from, so this module's job is
narrow and strict: read RSS or Atom feeds, take the fields the publisher
actually put there, and hand back records that say where each one came from.
It invents nothing. Anything it cannot parse it reports and skips, because a
newspaper that quietly drops half its sources is worse than one that says so.

Only the standard library is used, so the fetcher runs anywhere Python does.
"""

from __future__ import annotations

import gzip
import hashlib
import html
import json
import re
import socket
import ssl
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree

USER_AGENT = "tamilpaper/1.0 (+https://github.com/Ezhilbio1987)"

# India Standard Time. A paper's "today" is its own local day, not UTC's.
IST = timezone(timedelta(hours=5, minutes=30))

# Namespaces feeds actually use in the wild.
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "content": "http://purl.org/rss/1.0/modules/content/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "media": "http://search.yahoo.com/mrss/",
}

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


class FeedError(RuntimeError):
    """A feed could not be read or parsed. Always carries the feed's name."""


@dataclass
class Story:
    title: str
    summary: str
    url: str
    source: str          # the publication's display name
    section: str         # which page of the paper it is destined for
    published: datetime | None
    language: str = "en"
    feed: str = ""       # the feed URL it came from

    @property
    def key(self) -> str:
        """Identity for de-duplication: the link if there is one, else the
        title, both normalised. Wire copy reaches several outlets with the
        same headline and different tracking parameters."""
        if self.url:
            cleaned = re.sub(r"[?#].*$", "", self.url.strip().lower())
            return hashlib.sha1(cleaned.encode()).hexdigest()
        return hashlib.sha1(normalise_title(self.title).encode()).hexdigest()

    def as_dict(self) -> dict:
        data = asdict(self)
        data["published"] = self.published.isoformat() if self.published else None
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Story":
        published = data.get("published")
        return cls(
            title=data["title"], summary=data.get("summary", ""),
            url=data.get("url", ""), source=data.get("source", ""),
            section=data.get("section", ""),
            published=datetime.fromisoformat(published) if published else None,
            language=data.get("language", "en"), feed=data.get("feed", ""),
        )


@dataclass
class Feed:
    name: str            # publication name, printed as the credit
    url: str
    section: str
    language: str = "en"
    limit: int = 12      # most items to take from this feed


@dataclass
class FetchReport:
    """What happened, feed by feed. Printed by the CLI so a thin edition is
    never a mystery."""
    ok: list[tuple[str, int]] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    dropped_old: int = 0
    dropped_duplicate: int = 0

    @property
    def total(self) -> int:
        return sum(count for _, count in self.ok)


# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------

def clean_text(raw: str | None) -> str:
    """Feed summaries arrive as escaped HTML fragments. Reduce to plain text."""
    if not raw:
        return ""
    text = html.unescape(raw)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"</p\s*>", " ", text, flags=re.I)
    text = _TAG.sub("", text)
    text = html.unescape(text)          # entities can survive one pass
    text = text.replace(" ", " ")
    return _SPACE.sub(" ", text).strip()


def _is_latin(ch: str) -> bool:
    return "LATIN" in unicodedata.name(ch, "")


def normalise_title(title: str) -> str:
    """Fold a headline for comparison: case, punctuation, spacing, and accents
    on Latin letters only.

    The accent stripping has to be script-aware. In Tamil a vowel sign *is* a
    combining character, so folding them away turns "சென்னை மெட்ரோ" into
    "ச ன ன ம ட ர" and makes unrelated headlines collide. Latin diacritics are
    dropped, because "Café" and "Cafe" really are the same headline; Tamil
    marks are kept, because they are the word.
    """
    decomposed = unicodedata.normalize("NFKD", title.casefold())
    kept: list[str] = []
    base_is_latin = False
    for ch in decomposed:
        if unicodedata.combining(ch):
            if not base_is_latin:
                kept.append(ch)
            continue
        base_is_latin = _is_latin(ch)
        kept.append(ch)
    # Drop punctuation, symbols and separators; keep letters, digits, marks.
    # `\w` will not do here — it is defined on str.isalnum(), which is False
    # for a Tamil vowel sign.
    folded = "".join(
        " " if unicodedata.category(ch)[0] in "PSZC" else ch for ch in kept)
    return _SPACE.sub(" ", unicodedata.normalize("NFC", folded)).strip()


def _first(element, *paths: str) -> str | None:
    for path in paths:
        found = element.find(path, NS)
        if found is not None:
            if found.text and found.text.strip():
                return found.text
            href = found.get("href")
            if href:
                return href
    return None


def parse_date(raw: str | None) -> datetime | None:
    """Feeds date things in RFC 822, ISO 8601, and several near misses."""
    if not raw:
        return None
    raw = raw.strip()
    try:
        parsed = parsedate_to_datetime(raw)
        if parsed is not None:
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        pass
    candidate = raw.replace("Z", "+00:00")
    for attempt in (candidate, candidate[:19], candidate[:10]):
        try:
            parsed = datetime.fromisoformat(attempt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------

def fetch_bytes(url: str, timeout: float = 20.0, retries: int = 2) -> bytes:
    """GET a URL, following redirects, with a couple of polite retries.

    Feeds go down, time out and rate-limit; one flaky publisher should not
    take the edition with it, so failures are raised as FeedError for the
    caller to record and carry on.
    """
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
        "Accept-Encoding": "gzip",
    })
    last: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    payload = gzip.decompress(payload)
                return payload
        except (urllib.error.URLError, urllib.error.HTTPError,
                socket.timeout, ssl.SSLError, OSError) as err:
            last = err
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
    raise FeedError(f"{url}: {last}")


def parse_feed(payload: bytes, feed: Feed) -> list[Story]:
    """Read RSS 2.0 or Atom. Both are common; neither is going away."""
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as err:
        raise FeedError(f"{feed.name}: not valid XML — {err}") from err

    entries = root.findall(".//item")
    atom = False
    if not entries:
        entries = root.findall(".//atom:entry", NS)
        atom = True
    if not entries:
        raise FeedError(f"{feed.name}: no <item> or <entry> elements found")

    stories: list[Story] = []
    for entry in entries[: feed.limit]:
        title = clean_text(_first(entry, "title", "atom:title"))
        if not title:
            continue
        summary = clean_text(_first(
            entry, "description", "atom:summary", "atom:content", "content:encoded"))
        link = _first(entry, "link", "atom:link", "guid") or ""
        if atom and not link.startswith("http"):
            found = entry.find("atom:link", NS)
            link = (found.get("href") if found is not None else "") or ""
        published = parse_date(_first(
            entry, "pubDate", "atom:published", "atom:updated", "dc:date"))
        stories.append(Story(
            title=title, summary=summary, url=link.strip(), source=feed.name,
            section=feed.section, published=published,
            language=feed.language, feed=feed.url,
        ))
    return stories


def _same_day(moment: datetime, day: datetime) -> bool:
    local = moment.astimezone(day.tzinfo)
    return (local.year, local.month, local.day) == (day.year, day.month, day.day)


def fetch(feeds: list[Feed], day: datetime | None = None, window_hours: int = 0,
          cache_dir: Path | None = None, offline: bool = False,
          ) -> tuple[list[Story], FetchReport]:
    """Read every feed and return the day's stories, newest first.

    ``day`` defaults to today in IST. ``window_hours`` widens the filter to
    include the previous evening's copy, which an early edition wants.
    Undated items are kept: plenty of feeds omit the date, and dropping them
    would silently lose whole publications.

    With ``cache_dir`` set, each feed's raw bytes are written there and, in
    ``offline`` mode, read back instead of fetched — which makes a build
    reproducible and lets the pipeline be tested without a network.
    """
    day = day or datetime.now(IST)
    report = FetchReport()
    collected: list[Story] = []

    for feed in feeds:
        cache_path = None
        if cache_dir:
            cache_dir = Path(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            stem = hashlib.sha1(feed.url.encode()).hexdigest()[:12]
            cache_path = cache_dir / f"{stem}.xml"
        try:
            if offline:
                if not (cache_path and cache_path.exists()):
                    raise FeedError(f"{feed.name}: nothing cached for offline use")
                payload = cache_path.read_bytes()
            else:
                payload = fetch_bytes(feed.url)
                if cache_path:
                    cache_path.write_bytes(payload)
            stories = parse_feed(payload, feed)
        except FeedError as err:
            report.failed.append((feed.name, str(err)))
            continue

        kept = []
        for story in stories:
            if story.published is not None:
                age = day - story.published.astimezone(day.tzinfo)
                if not _same_day(story.published, day) and not (
                        window_hours and timedelta(0) <= age <= timedelta(hours=window_hours)):
                    report.dropped_old += 1
                    continue
            kept.append(story)
        report.ok.append((feed.name, len(kept)))
        collected.extend(kept)

    seen: set[str] = set()
    unique: list[Story] = []
    for story in collected:
        if story.key in seen:
            report.dropped_duplicate += 1
            continue
        seen.add(story.key)
        unique.append(story)

    unique.sort(key=lambda s: s.published or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True)
    return unique, report


# --------------------------------------------------------------------------
# Feed configuration
# --------------------------------------------------------------------------

def load_feeds(path: str | Path) -> list[Feed]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    feeds = []
    for entry in data["feeds"]:
        missing = {"name", "url", "section"} - set(entry)
        if missing:
            raise ValueError(f"feed entry missing {', '.join(sorted(missing))}: {entry}")
        feeds.append(Feed(
            name=entry["name"], url=entry["url"], section=entry["section"],
            language=entry.get("language", "en"), limit=int(entry.get("limit", 12)),
        ))
    return feeds
