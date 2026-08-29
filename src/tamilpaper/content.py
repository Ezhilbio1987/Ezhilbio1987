"""Loading and normalising an edition file.

The edition JSON is written the way an editor thinks about a page — a list of
blocks with a headline and some paragraphs. This turns it into the shape the
template renders: story copy becomes a flow of typed items, pictures get their
artwork resolved, and every block is validated before make-up starts.
"""

import base64
import json
from pathlib import Path

from . import artwork, press, weather
from .layout import place_blocks, coverage

ROOT = Path(__file__).resolve().parents[2]

BLOCK_TYPES = {"story", "briefs", "index", "table", "quote", "advert", "classifieds",
               "picture", "weather", "sources"}

REQUIRED = {
    "story": ("headline",),
    "briefs": ("title", "items"),
    "index": ("title", "items"),
    "table": ("title", "items"),
    "quote": ("text", "source"),
    "advert": ("headline",),
    "classifieds": ("title", "ads"),
    "picture": ("figure",),
    "weather": ("title", "categories"),
    "sources": ("title", "items"),
}


class ContentError(ValueError):
    pass


# Optional keys, with the value the template should see when the editor leaves
# them out. Declaring them here keeps StrictUndefined switched on, so a
# misspelled key in an edition file is still an error rather than a blank.
DEFAULTS: dict[str, dict] = {
    "story": {
        "variant": "minor", "rule": "", "editorial": False, "jump": "",
        "standfirst": "", "kicker": "", "deck": "", "byline": None,
        "place": "", "columns": 1, "source": "",
    },
    "briefs": {"plain": False},
    "index": {},
    "table": {"note": ""},
    "quote": {},
    "advert": {"eyebrow": "", "body": "", "footer": ""},
    "classifieds": {},
    "picture": {"rule": ""},
    "weather": {"map": "tamilnadu", "labels": True, "hide_labels": []},
    "sources": {"note": "", "columns": 2},
}

FIGURE_DEFAULTS = {"svg": "", "src": "", "alt": "", "caption": "", "credit": "",
                   "ratio": "3 / 2", "palette": None, "subject": ""}


def _apply_defaults(block: dict) -> None:
    for key, value in DEFAULTS[block["type"]].items():
        block.setdefault(key, value)
    if block.get("byline"):
        block["byline"].setdefault("name", "")
        block["byline"].setdefault("role", "")


PHOTO_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
               ".webp": "image/webp", ".gif": "image/gif"}


def _inline_photo(src: str) -> str:
    """Read a photograph off disk and return it as a ``data:`` URI.

    A real picture beats a drawn stand-in, so the edition can name a file in
    ``assets/photos``. It has to be inlined rather than linked: the page is
    printed by a browser from a temporary directory, and a relative link that
    resolves while the HTML sits next to the assets does not survive being
    moved. Inlining also means one PDF carries everything it needs.
    """
    path = Path(src)
    if not path.is_absolute():
        path = ROOT / src
    if not path.is_file():
        raise ContentError(f"picture not found: {src}")
    mime = PHOTO_TYPES.get(path.suffix.lower())
    if mime is None:
        raise ContentError(f"unsupported picture type: {path.suffix} ({src})")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


_LIBRARY_PATH = ROOT / "assets" / "photos" / "library.json"
_library_cache: dict | None = None


def picture_library() -> dict:
    """Standing file pictures, keyed by subject.

    A paper keeps a picture library: when a story is about the assembly you
    run the assembly picture, not a shape. The edition names a ``subject`` and
    this decides what it gets — the filed photograph when one exists, and the
    scene drawn for that subject when it does not. Filing a photograph later
    upgrades every story that asks for the subject, with no edition to edit.
    """
    global _library_cache
    if _library_cache is None:
        if _LIBRARY_PATH.is_file():
            _library_cache = json.loads(_LIBRARY_PATH.read_text(encoding="utf-8")).get("subjects", {})
        else:
            _library_cache = {}
    return _library_cache


def _apply_subject(fig: dict) -> None:
    """Fill a figure's picture from the library entry its subject names."""
    subject = fig.get("subject")
    if not subject:
        return
    entry = picture_library().get(subject)
    if entry is None:
        known = ", ".join(sorted(picture_library())) or "none filed"
        raise ContentError(f"unknown picture subject {subject!r}; filed subjects: {known}")
    filed = entry.get("file")
    if filed and (ROOT / filed).is_file() and not fig.get("src"):
        fig["src"] = filed
        if not fig.get("credit"):
            fig["credit"] = entry.get("credit", "")
    elif not fig.get("src") and not fig.get("scene"):
        fig["scene"] = entry.get("scene", "")
        if not fig.get("credit"):
            fig["credit"] = "விளக்கப் படம்"
    if not fig.get("alt"):
        fig["alt"] = entry.get("alt", "")


def _resolve_figure(fig: dict, seed: str, palette: str | None = None) -> dict:
    """Inline a real photograph, or draw a stand-in from ``scene``."""
    fig = dict(fig)
    for key, value in FIGURE_DEFAULTS.items():
        fig.setdefault(key, value)
    _apply_subject(fig)
    src = fig.get("src")
    if src and not src.startswith(("data:", "http://", "https://")):
        fig["src"] = _inline_photo(src)
    elif fig.get("scene") and not src:
        try:
            fig["svg"] = artwork.render(fig["scene"], fig.get("seed", seed),
                                        fig.get("palette") or palette)
        except KeyError as err:
            raise ContentError(str(err)) from err
    return fig


def _build_flow(block: dict, seed: str, palette: str | None = None) -> list[dict]:
    """Interleave paragraphs, crossheads and inline pictures into one flow.

    ``body`` is a list of paragraph strings. A paragraph starting with ``## ``
    becomes a crosshead. A figure with ``after: n`` is dropped into the copy
    after the nth paragraph, which is how a picture gets set into made-up
    columns.
    """
    paragraphs = block.get("body") or []
    if not isinstance(paragraphs, list):
        raise ContentError(f"{block.get('id')}: 'body' must be a list of paragraphs")

    figures: list[tuple[int, dict]] = []
    for i, fig in enumerate(block.get("figures") or ([block["figure"]] if "figure" in block else [])):
        figures.append((int(fig.get("after", 1)), _resolve_figure(fig, f"{seed}:{i}", palette)))
    figures.sort(key=lambda pair: pair[0])

    flow: list[dict] = []
    para_no = 0
    has_place = bool(block.get("place"))

    def drop_figures_at(n: int) -> None:
        while figures and figures[0][0] == n:
            flow.append({"kind": "figure", "figure": figures.pop(0)[1]})

    drop_figures_at(0)
    for text in paragraphs:
        if isinstance(text, str) and text.startswith("## "):
            flow.append({"kind": "crosshead", "text": text[3:].strip()})
            continue
        para_no += 1
        kind = "lede" if (para_no == 1 and has_place) else "para"
        flow.append({"kind": kind, "text": text})
        drop_figures_at(para_no)
    # Anything pinned past the end of the copy still goes in, at the end.
    while figures:
        flow.append({"kind": "figure", "figure": figures.pop(0)[1]})
    return flow


def _validate(block: dict, page_label: str, index: int) -> None:
    kind = block.get("type")
    label = block.get("id") or f"block #{index + 1}"
    if kind not in BLOCK_TYPES:
        raise ContentError(
            f"{page_label}: {label} has type {kind!r}; expected one of "
            f"{', '.join(sorted(BLOCK_TYPES))}"
        )
    for field in REQUIRED[kind]:
        if not block.get(field):
            raise ContentError(f"{page_label}: {label} ({kind}) is missing '{field}'")


def load(path: str | Path) -> dict:
    """Read an edition file and normalise it for the template."""
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise ContentError(f"{path}: invalid JSON — {err}") from err

    for key in ("paper", "pages"):
        if key not in data:
            raise ContentError(f"{path}: missing top-level '{key}'")

    preset = press.get((data.get("press") or {}).get("preset"))
    data["press"] = preset.as_dict()

    paper = data["paper"]
    data.setdefault("palette", None)
    data["dateline_ta"] = paper.get("dateline_ta") or []
    data["dateline_en"] = paper.get("dateline_en") or []

    warnings: list[str] = []

    for page_no, page in enumerate(data["pages"], start=1):
        page.setdefault("number", page_no)
        page.setdefault("kind", "front" if page_no == 1 else "inner")
        cols = int(page.get("cols") or preset.cols)
        rows = int(page.get("rows") or preset.rows)
        page["cols"], page["rows"] = cols, rows
        # A section colour, and a default palette for the pictures on the page.
        page.setdefault("accent", "")
        palette = page.get("palette") or data.get("palette")
        page_label = f"page {page['number']}"

        blocks = page.get("blocks") or []
        if not blocks:
            raise ContentError(f"{page_label}: has no blocks")

        for i, block in enumerate(blocks):
            block.setdefault("id", f"p{page['number']}-b{i + 1}")
            _validate(block, page_label, i)
            _apply_defaults(block)
            seed = f"{block['id']}"
            if block["type"] == "story":
                block["flow"] = _build_flow(block, seed, palette)
            elif block["type"] == "picture":
                block["figure"] = _resolve_figure(block["figure"], seed, palette)
            elif block["type"] == "weather":
                try:
                    weather.prepare(block)
                except weather.WeatherError as err:
                    raise ContentError(f"{page_label}: {err}") from err

        place_blocks(blocks, cols, rows, page_label)

        filled = coverage(blocks, cols, rows)
        if filled < 0.92:
            warnings.append(
                f"{page_label}: blocks fill only {filled:.0%} of the "
                f"{cols}×{rows} grid — the page will have a white hole"
            )

    warnings.extend(_duplicate_headlines(data))
    data["warnings"] = warnings
    return data


def _duplicate_headlines(data: dict) -> list[str]:
    """Catch the same story running twice in one edition.

    An edition assembled from several panels will repeat itself if nobody is
    watching — the same item in a page's briefs and in the front-page summary.
    Comparison is on the folded headline, so punctuation and spacing do not
    hide a duplicate.
    """
    import re
    import unicodedata

    def fold(text: str) -> str:
        text = unicodedata.normalize("NFKC", text.casefold())
        text = "".join(" " if unicodedata.category(c)[0] in "PSZC" else c
                       for c in text)
        return re.sub(r"\s+", " ", text).strip()

    seen: dict[str, str] = {}
    found: list[str] = []
    for page in data["pages"]:
        for block in page["blocks"]:
            headlines = []
            if block["type"] == "story":
                headlines.append(block.get("headline", ""))
            for item in block.get("items", []) or []:
                if isinstance(item, dict) and item.get("headline"):
                    headlines.append(item["headline"])
            for headline in headlines:
                key = fold(headline)
                if not key:
                    continue
                where = f"page {page['number']}/{block['id']}"
                if key in seen:
                    found.append(
                        f"the same item runs twice — {seen[key]} and {where}: "
                        f"{headline[:56]}")
                else:
                    seen[key] = where
    return found
