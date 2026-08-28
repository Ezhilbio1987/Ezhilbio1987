"""Turning a pile of fetched stories into a laid-out edition.

The hard part is not the layout, it is the honesty of it. A syndication feed
gives a headline and a sentence or two — nowhere near what a written story
holds. A composer that pretended otherwise would either invent copy or leave
half the page white. So this one measures the text it actually has and picks
block sizes to match: a day with three substantial items and twenty short ones
becomes a page with three stories and a column of briefs, not five stories
padded out.

What comes out is a *draft*. The structure, the sourcing and the make-up are
finished; the prose is still the feed's own summary, in the feed's own
language. Rewriting that into the paper's voice is the editor's job, and the
draft marks every block that still needs it.
"""

from __future__ import annotations

import math
from datetime import datetime
from urllib.parse import urlparse

from .news import Story, Feed, IST

# Roughly how many words one grid cell (one column x one row) holds at the
# body size the presets use, measured against the built editions.
WORDS_PER_CELL = 15

# The smallest story block worth setting, in cells. Below this a story is not
# a story — it is a brief, and pretending otherwise is what leaves a page full
# of quarter-filled boxes. A syndication summary is usually two or three
# sentences, so on a wire-fed draft most items land here, and the page becomes
# what it honestly is: a few reports and a column of news in brief.
MIN_STORY_CELLS = 6

# A brief item wants about this many cells, panel furniture included.
CELLS_PER_BRIEF = 1.5

# Band shapes a page is built from, per page width. Each is a list of block
# widths that together span the page.
BANDS: dict[int, list[list[int]]] = {
    4: [[4], [2, 2], [3, 1]],
    5: [[5], [3, 2], [2, 3]],
    6: [[6], [4, 2], [3, 3], [2, 2, 2]],
}

TAMIL_MONTHS = ["ஜனவரி", "பிப்ரவரி", "மார்ச்", "ஏப்ரல்", "மே", "ஜூன்",
                "ஜூலை", "ஆகஸ்ட்", "செப்டம்பர்", "அக்டோபர்", "நவம்பர்", "டிசம்பர்"]
TAMIL_WEEKDAYS = ["திங்கள்கிழமை", "செவ்வாய்க்கிழமை", "புதன்கிழமை", "வியாழக்கிழமை",
                  "வெள்ளிக்கிழமை", "சனிக்கிழமை", "ஞாயிற்றுக்கிழமை"]

VARIANTS = [(12, "lead"), (7, "major"), (3, "minor"), (0, "brief")]


class ComposeError(ValueError):
    pass


def _words(story: Story) -> int:
    return len(story.summary.split())


def _weight(story: Story) -> float:
    """How much of the page a story has earned. Length is the honest signal we
    have — a feed gives no other measure of importance — with a nudge for
    recency so the evening's news leads over the morning's."""
    score = float(_words(story))
    if story.published:
        hours = max(0.0, (datetime.now(IST) - story.published.astimezone(IST))
                    .total_seconds() / 3600)
        score += max(0.0, 24 - hours) * 0.6
    return score


def _variant(cells: int) -> str:
    for threshold, name in VARIANTS:
        if cells >= threshold:
            return name
    return "brief"


def _paragraphs(story: Story) -> list[str]:
    """The feed's summary, broken at sentence ends so it sets as copy rather
    than one long block. Nothing is added to it."""
    text = story.summary.strip()
    if not text:
        return []
    parts, current = [], ""
    for chunk in text.replace("। ", ". ").split(". "):
        chunk = chunk.strip()
        if not chunk:
            continue
        current = f"{current} {chunk}." if current else f"{chunk}."
        if len(current) > 220:
            parts.append(current.strip())
            current = ""
    if current:
        parts.append(current.strip())
    return parts or [text]


def _credit(story: Story) -> str:
    when = story.published.astimezone(IST) if story.published else None
    date = f", {when.day} {TAMIL_MONTHS[when.month - 1]} {when.year}" if when else ""
    return f"ஆதாரம்: {story.source}{date}"


def story_block(story: Story, width: int, height: int, index: int) -> dict:
    cells = width * height
    return {
        "id": f"s{index}",
        "type": "story",
        "col": width, "row": height, "columns": width,
        "variant": _variant(cells),
        "rule": "accent" if cells >= 9 else "hairline",
        "kicker": story.section,
        "headline": story.title,
        "byline": {"name": story.source, "role": ""},
        "body": _paragraphs(story),
        "source": _credit(story),
        "draft": True,
        "language": story.language,
    }


def briefs_title(stories: list[Story]) -> str:
    """Name a briefs panel after what is in it, so two panels on the same page
    are not both headed 'news in brief'."""
    sections: list[str] = []
    for story in stories:
        if story.section and story.section not in sections:
            sections.append(story.section)
    if not sections:
        return "செய்திகள் சுருக்கம்"
    if len(sections) > 2:
        return f"{sections[0]} · {sections[1]} · பிற"
    return " · ".join(sections)


def briefs_block(stories: list[Story], width: int, height: int, index: int,
                 title: str | None = None) -> dict:
    return {
        "id": f"b{index}",
        "type": "briefs",
        "col": width, "row": height,
        "title": title or briefs_title(stories),
        "items": [
            {"headline": s.title,
             "text": (s.summary or s.title) + f"  — {s.source}"}
            for s in stories
        ],
        "draft": True,
    }


def sources_block(stories: list[Story], width: int, height: int) -> dict:
    """One credit per publication used, with a representative link.

    Few credits set in one column so the box fills; many set in two so they
    fit. The alternative is a half-empty box or a dropped source, and neither
    belongs on a page whose whole job is saying where the news came from.
    """
    seen: dict[str, str] = {}
    for story in stories:
        if story.source not in seen and story.url:
            host = urlparse(story.url).netloc.replace("www.", "")
            path = urlparse(story.url).path
            seen[story.source] = f"{host}{path}"[:78]
    return {
        "id": "sources",
        "type": "sources",
        "col": width, "row": height,
        "columns": 1 if len(seen) <= 3 else 2,
        "title": "இந்த இதழின் செய்தி ஆதாரங்கள்",
        "items": [{"label": name, "url": url} for name, url in seen.items()],
        # No standing note under the list. The credits are the statement; a
        # paragraph repeating them in prose only takes room from the page.
        "note": "",
    }


def _band(cols: int, slots: int) -> list[int]:
    """A band of `slots` blocks spanning the full page width."""
    if slots <= 1:
        return [cols]
    for shape in BANDS[cols]:
        if len(shape) == slots:
            return shape
    return [cols]


def _wanted_cells(story: Story, words_per_cell: int) -> int:
    return max(MIN_STORY_CELLS, math.ceil(_words(story) / words_per_cell))


def plan_page(stories: list[Story], cols: int, rows: int, number: int,
              section: str, kind: str, reserve: list[dict] | None = None,
              words_per_cell: int = WORDS_PER_CELL) -> tuple[dict, list[Story]]:
    """Lay one page out of the stories given; return it and what did not fit.

    Blocks are sized from the words each story actually carries. Items too
    short to hold a block become briefs instead of underfilled stories. The
    page is built as a stack of full-width bands, so the grid is always
    covered exactly — a page with a hole in it is a bug, not a style.

    Any blocks in ``reserve`` (the sources box) are set at the foot of the
    page and their rows taken out of the budget first.
    """
    if cols not in BANDS:
        raise ComposeError(f"no band templates for a {cols}-column page")

    reserve = list(reserve or [])
    for block in reserve:
        block["col"] = cols
    budget = rows - sum(block["row"] for block in reserve)
    if budget < 2:
        raise ComposeError(
            f"page {number}: the reserved blocks leave only {budget} row(s) for copy")

    queue = sorted(stories, key=_weight, reverse=True)

    # Decide the split between reports and briefs before placing anything.
    # Only items with the words to carry a block become reports, and only as
    # many as the page has rows for once the briefs have their share.
    reports: list[Story] = []
    briefs: list[Story] = list(queue)
    rows_left = budget
    while briefs:
        candidate = briefs[0]
        wanted = _wanted_cells(candidate, words_per_cell)
        if _words(candidate) < MIN_STORY_CELLS * words_per_cell:
            break
        height = max(2, math.ceil(wanted / cols))
        briefs_need = math.ceil(CELLS_PER_BRIEF * (len(briefs) - 1) / cols)
        if height + min(briefs_need, 3) > rows_left:
            break
        reports.append(briefs.pop(0))
        rows_left -= height
    blocks: list[dict] = []
    bands: list[list[int]] = []
    remaining = budget
    index = 0

    while reports and remaining >= 2:
        slots = 2 if (len(reports) >= 2 and cols >= 4) else 1
        shape = _band(cols, slots)
        take = reports[:len(shape)]
        if len(take) < len(shape):
            shape = _band(cols, len(take))

        need = max(
            math.ceil(_wanted_cells(story, words_per_cell) / width)
            for story, width in zip(take, shape))
        # Hold rows back for the briefs that follow.
        cap = remaining if not briefs and len(reports) <= len(take) else max(2, remaining - 2)
        height = max(2, min(need, cap, remaining))

        band: list[int] = []
        for story, width in zip(take, shape):
            index += 1
            blocks.append(story_block(story, width, height, index))
            band.append(len(blocks) - 1)
        bands.append(band)
        reports = reports[len(take):]
        remaining -= height

    briefs.extend(reports)      # anything the rows could not reach

    if remaining > 0:
        if briefs:
            # Split into panels so each holds a sensible number of items.
            capacity = max(1, math.ceil(remaining * cols / CELLS_PER_BRIEF))
            slots = 2 if (len(briefs) >= 6 and cols >= 4 and capacity >= 6) else 1
            shape = _band(cols, slots)
            share = math.ceil(len(briefs) / len(shape))
            chunks = [briefs[i * share:(i + 1) * share] for i in range(len(shape))]
            chunks = [chunk for chunk in chunks if chunk]
            if len(chunks) < len(shape):
                shape = _band(cols, len(chunks))
            for slot, (width, chunk) in enumerate(zip(shape, chunks)):
                blocks.append(briefs_block(chunk, width, remaining, slot + 1))
            briefs = []
        elif bands:
            for position in bands[-1]:
                blocks[position]["row"] += remaining
        else:
            raise ComposeError(f"page {number}: nothing to place")
        remaining = 0

    blocks.extend(reserve)

    covered = sum(b["col"] * b["row"] for b in blocks)
    if covered != cols * rows:
        raise ComposeError(
            f"page {number}: blocks cover {covered} of {cols * rows} cells; "
            f"this is a bug in the composer")

    return {
        "number": number, "kind": kind, "section": section,
        "cols": cols, "rows": rows, "blocks": blocks,
    }, briefs


def masthead(name: str, latin: str, day: datetime, pages: int,
             edition_label: str) -> dict:
    return {
        "name": name,
        "latin_name": latin,
        "tagline": edition_label,
        "place": "சென்னை",
        "credo": ["உண்மை சொல்வோம்", "உரிமை காப்போம்", "ஊரோடு நிற்போம்"],
        "credo_sub": "இணையப் பதிப்பு",
        "ear_right": ["இந்த இதழ் வெளியான", "ஊடகச் செய்திகளிலிருந்து",
                       "தானியங்கி முறையில்", "தொகுக்கப்பட்டது"],
        "ear_right_sub": "Auto-compiled draft",
        "registration": f"தானியங்கித் தொகுப்பு · {day:%d.%m.%Y %H:%M} IST · ஆதாரங்கள் பக்கம் {pages}",
        "weekday_ta": TAMIL_WEEKDAYS[day.weekday()],
        "date_ta": f"{TAMIL_WEEKDAYS[day.weekday()]}, {day.day} {TAMIL_MONTHS[day.month - 1]} {day.year}",
        "date_numeric": f"{day:%d.%m.%Y}",
        "footline_note": "தானியங்கித் தொகுப்பு · செய்திகள் வெளியான ஊடக அறிக்கைகளிலிருந்து",
        "dateline_ta": [edition_label, "சென்னை", TAMIL_WEEKDAYS[day.weekday()],
                         f"{day:%d.%m.%Y}", "இணையப் பதிப்பு", f"பக்கம் – {pages}"],
        "dateline_en": ["Draft edition", "Chennai", f"{day:%A}",
                         f"{day:%d.%m.%Y}", "Online", f"Pages – {pages}"],
    }


def page_capacity_cells(stories: list[Story], words_per_cell: int = WORDS_PER_CELL) -> int:
    """How many grid cells this many stories want, at the sizes they earn."""
    total = 0.0
    for story in stories:
        if _words(story) >= MIN_STORY_CELLS * words_per_cell:
            total += _wanted_cells(story, words_per_cell)
        else:
            total += CELLS_PER_BRIEF
    return math.ceil(total)


def _split_into_pages(by_section: dict[str, list[Story]], order: list[str],
                      page_cells: int, first_page_cells: int,
                      words_per_cell: int) -> list[list[Story]]:
    """Group the stories into page-sized batches, keeping sections together
    where they fit.

    The number of pages comes from how much copy there is, not from how many
    sections were configured. Five thin sections make one page, not five
    quarter-empty ones.
    """
    batches: list[list[Story]] = []
    current: list[Story] = []
    capacity = first_page_cells

    for section in order:
        for story in by_section[section]:
            cost = page_capacity_cells([story], words_per_cell)
            if current and page_capacity_cells(current, words_per_cell) + cost > capacity:
                batches.append(current)
                current = []
                capacity = page_cells
            current.append(story)
    if current:
        batches.append(current)
    return batches or [[]]


def choose_press(stories: list[Story], presets: dict, target_fill: float = 0.82,
                 words_per_cell: int = WORDS_PER_CELL) -> str:
    """Pick the sheet the day's copy actually fills.

    A wire digest of twenty short items is an A4 news sheet, not a broadsheet
    with half a page of white. Rather than stretch the copy, choose the format
    it fits — smallest first, so a thin day prints as a thin paper.
    """
    needed = page_capacity_cells(stories, words_per_cell)
    order = ["a4", "a3", "tabloid", "berliner", "broadsheet", "indian-broadsheet"]
    best, best_gap = None, None
    for key in order:
        preset = presets.get(key)
        if preset is None:
            continue
        grid = preset.cols * preset.rows
        # Room for the sources box on the last page.
        pages = max(1, math.ceil((needed + preset.cols * 2) / grid))
        fill = (needed + preset.cols * 2) / (grid * pages)
        if fill >= target_fill:
            return key
        gap = abs(fill - target_fill)
        if best_gap is None or gap < best_gap:
            best, best_gap = key, gap
    return best or "tabloid"


def compose(stories: list[Story], sections: list[str], cols: int, rows: int,
            day: datetime | None = None, preset: str = "tabloid",
            name: str = "பீனிக்ஸ் மலர் செய்தி", latin: str = "Phoenix Malar Seithi",
            edition_label: str = "மாலைப் பதிப்பு",
            accents: dict[str, str] | None = None,
            palette: str = "civic",
            words_per_cell: int = WORDS_PER_CELL) -> dict:
    """Build a complete, valid edition from fetched stories.

    The page count follows the copy. Sections are kept in the order given and
    run on together when neither fills a page on its own; the sources box goes
    at the foot of the last page.
    """
    if not stories:
        raise ComposeError("no stories to compose — check the fetch report")

    day = day or datetime.now(IST)
    accents = accents or {}
    by_section: dict[str, list[Story]] = {}
    for story in stories:
        by_section.setdefault(story.section, []).append(story)

    order = [s for s in sections if by_section.get(s)]
    order += [s for s in by_section if s not in order]
    if not order:
        raise ComposeError("stories carry no section any page was planned for")

    # The front page loses rows to the nameplate; the last loses them to the
    # sources box.
    grid = cols * rows
    sources = sources_block(stories, cols, 2)
    batches = _split_into_pages(
        by_section, order,
        page_cells=grid, first_page_cells=int(grid * 0.8),
        words_per_cell=words_per_cell)

    # The sources box has to fit on the last page; if it will not, run another.
    if page_capacity_cells(batches[-1], words_per_cell) + cols * 2 > grid:
        batches.append([])
    if not batches[-1]:
        # An empty last page carries the sources box and whatever the page
        # before it can spare.
        if len(batches) > 1 and batches[-2]:
            batches[-1] = [batches[-2].pop()]

    pages: list[dict] = []
    for position, batch in enumerate(batches):
        if not batch and position:
            batch = [batches[position - 1].pop()] if batches[position - 1] else []
        if not batch:
            continue
        present = []
        for story in batch:
            if story.section not in present:
                present.append(story.section)
        reserve = [sources] if position == len(batches) - 1 else []
        page, overflow = plan_page(
            batch, cols, rows, len(pages) + 1, " · ".join(present),
            "front" if not pages else "inner", reserve=reserve,
            words_per_cell=words_per_cell)
        page["accent"] = accents.get(present[0], "") if present else ""
        pages.append(page)
        if overflow and position + 1 < len(batches):
            batches[position + 1] = overflow + batches[position + 1]

    if not pages:
        raise ComposeError("nothing could be placed on any page")

    return {
        "paper": masthead(name, latin, day, len(pages), edition_label),
        "press": {"preset": preset},
        "palette": palette,
        "pages": pages,
    }
