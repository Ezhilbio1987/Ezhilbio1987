#!/usr/bin/env python3
"""Write a dated three-page skeleton the morning routine can fill in.

Composing a page grid by hand is the fiddly part of making an edition: every
page has to be covered exactly or the build refuses, and getting there costs
more effort than writing the copy does. That is a poor use of an unattended
run's budget, and it is why the 6 am routine twice finished with nothing to
show. So the shape is generated and the routine only writes words.

    python3 tools/new_edition.py -o content/daily.json

The result builds as it stands — a valid, if empty-headed, paper. Replace the
placeholder headlines and briefs with the day's news and rebuild.
"""

import argparse
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

WEEKDAY_TA = ["திங்கட்கிழமை", "செவ்வாய்க்கிழமை", "புதன்கிழமை", "வியாழக்கிழமை",
              "வெள்ளிக்கிழமை", "சனிக்கிழமை", "ஞாயிற்றுக்கிழமை"]
MONTH_TA = ["ஜனவரி", "பிப்ரவரி", "மார்ச்", "ஏப்ரல்", "மே", "ஜூன்",
            "ஜூலை", "ஆகஸ்ட்", "செப்டம்பர்", "அக்டோபர்", "நவம்பர்", "டிசம்பர்"]

# Rahu kalam, Emakandam, Kuligai and soolam are fixed by weekday, so they can
# be printed without an almanac. Tithi and natchathiram cannot — they need the
# day's panchangam, and are left for the routine to fill or leave out.
WEEKDAY_PANCHANGAM = {
    0: ("காலை 07.30–09.00", "காலை 10.30–12.00", "பிற்பகல் 01.30–03.00", "கிழக்கு"),
    1: ("பிற்பகல் 03.00–04.30", "காலை 09.00–10.30", "பகல் 12.00–01.30", "வடக்கு"),
    2: ("பகல் 12.00–01.30", "பிற்பகல் 07.30–09.00", "காலை 10.30–12.00", "வடக்கு"),
    3: ("பிற்பகல் 01.30–03.00", "காலை 06.00–07.30", "காலை 09.00–10.30", "தெற்கு"),
    4: ("காலை 10.30–12.00", "பிற்பகல் 03.00–04.30", "காலை 07.30–09.00", "மேற்கு"),
    5: ("காலை 09.00–10.30", "பிற்பகல் 01.30–03.00", "காலை 06.00–07.30", "கிழக்கு"),
    6: ("மாலை 04.30–06.00", "பகல் 12.00–01.30", "பிற்பகல் 03.00–04.30", "மேற்கு"),
}

# The one Tamil-calendar date this repo has from a source: 30 August 2026 was
# Aavani 13. Counting off that anchor is safe inside Aavani and nowhere else,
# so outside it the field is left blank rather than guessed at.
ANCHOR_DATE, ANCHOR_MONTH, ANCHOR_DAY, ANCHOR_LEN = dt.date(2026, 8, 30), "ஆவணி", 13, 31


def tamil_month_day(day: dt.date) -> str:
    offset = (day - ANCHOR_DATE).days + ANCHOR_DAY
    if 1 <= offset <= ANCHOR_LEN:
        return f"{ANCHOR_MONTH} {offset}"
    return ""


# Placeholder copy is sized like the real thing on purpose. A skeleton filled
# with one-word stubs would report every block as under-filled and tell you
# nothing about whether the slot counts are right; at roughly the length of a
# real brief, the fill figures in the build report mean something.
BRIEF_STUB = ("இங்கே செய்திச் சுருக்கம் வரும். இரண்டு அல்லது மூன்று வாக்கியங்களில் "
              "செய்தியின் சாரத்தை எழுத வேண்டும். — ஆதாரம்")
PARA_STUB = ("இங்கே செய்தி உரை வரும். ஒரு பத்தியில் ஐம்பது சொற்களுக்கு மிகாமல், "
             "செய்தியின் முக்கியத் தகவலை முதல் வாக்கியத்திலேயே தர வேண்டும். "
             "மேற்கோள்களும் எண்களும் ஆதாரத்தில் இருந்தே வர வேண்டும்.")


def briefs(bid, title, col, row, n):
    return {"id": bid, "type": "briefs", "col": col, "row": row, "title": title,
            "items": [{"headline": f"{title} — தலைப்பு {i + 1}", "text": BRIEF_STUB}
                      for i in range(n)]}


def story(sid, col, row, columns, kicker, headline, place, variant, subject=None, paras=4):
    block = {"id": sid, "type": "story", "variant": variant, "col": col, "row": row,
             "columns": columns, "kicker": kicker, "headline": headline,
             "place": place, "source": "ஆதாரம்: ",
             "body": [PARA_STUB for _ in range(paras)]}
    block["figures"] = ([{"subject": subject, "after": 2, "ratio": "3 / 2", "caption": ""}]
                        if subject else [])
    return block


def build(day: dt.date) -> dict:
    numeric = day.strftime("%d.%m.%Y")
    weekday = WEEKDAY_TA[day.weekday()]
    tamil_day = tamil_month_day(day)
    rahu, emakandam, kuligai, soolam = WEEKDAY_PANCHANGAM[day.weekday()]

    paper = {
        "name": "பீனிக்ஸ் மலர் செய்தி", "latin_name": "Phoenix Malar Seithi",
        "tagline": "காலைப் பதிப்பு", "place": "சென்னை",
        "credo": ["உண்மை சொல்வோம்", "உரிமை காப்போம்", "ஊரோடு நிற்போம்"],
        "credo_sub": "இணையப் பதிப்பு",
        "ear_right": ["முதல் தலைப்பு", "இரண்டாம் தலைப்பு",
                      "மூன்றாம் தலைப்பு", "நான்காம் தலைப்பு"],
        "ear_right_sub": "இன்றைய சுருக்கம்",
        "registration": "இணையப் பதிப்பு  ·  தொகுப்பு நேரம்: காலை 6:00",
        "weekday_ta": weekday,
        "date_ta": f"{weekday}, {day.day} {MONTH_TA[day.month - 1]} {day.year}",
        "date_numeric": numeric,
        "footline_note": f"காலைப் பதிப்பு · {numeric}",
        "dateline_ta": ["காலைப் பதிப்பு", "சென்னை", weekday, tamil_day, numeric,
                        "இணையப் பதிப்பு", "பக்கம் – 3"],
        "dateline_en": ["Morning Edition", "Chennai", day.strftime("%A"),
                        tamil_day, numeric, "Online", "Pages – 3"],
    }

    page1 = {"number": 1, "kind": "front", "cols": 5, "rows": 11,
             "accent": "#c0141f", "palette": "civic", "blocks": [
        story("s-lead", 3, 4, 3, "அரசியல்", "இன்றைய முதன்மைச் செய்தி",
              f"சென்னை, {day.day}", "lead", "sattamandram", 5),
        story("s-second", 2, 4, 2, "செய்தி", "இரண்டாவது முக்கியச் செய்தி",
              f"சென்னை, {day.day}", "major", None, 4),
        {"id": "t-weather", "type": "table", "col": 2, "row": 3,
         "title": "இன்றைய வானிலை",
         "items": [{"k": "சென்னை", "v": ""}, {"k": "கோயம்புத்தூர்", "v": ""},
                   {"k": "மதுரை", "v": ""}, {"k": "திருச்சி", "v": ""},
                   {"k": "சேலம்", "v": ""}, {"k": "நீலகிரி", "v": ""},
                   {"k": "புதுச்சேரி", "v": ""}, {"k": "கடலோரப் பகுதிகள்", "v": ""},
                   {"k": "காற்று", "v": ""}, {"k": "சூரிய உதயம்", "v": ""},
                   {"k": "சூரிய அஸ்தமனம்", "v": ""}],
         "note": "மாவட்ட வரைபடம் — பக்கம் 3."},
        briefs("b-front", "இன்றைய முக்கியச் செய்திகள்", 3, 3, 8),
        briefs("b-nation", "நாடு", 5, 4, 12),
    ]}

    page2 = {"number": 2, "kind": "inner", "section": "அரசுத் திட்டங்கள் · நகரம் · மாவட்டங்கள்",
             "cols": 5, "rows": 11, "accent": "#0f766e", "palette": "sea", "blocks": [
        story("s-scheme", 3, 4, 3, "மாநிலத் திட்டம்", "அரசுத் திட்ட அறிவிப்பு",
              f"சென்னை, {day.day}", "lead", "secretariat", 6),
        story("s-central", 2, 4, 2, "மத்திய அறிவிப்பு", "மத்திய அறிவிப்பும் தமிழகத் தாக்கமும்",
              f"புதுடெல்லி, {day.day}", "major", None, 4),
        briefs("b-schemes", "மாநிலத் திட்டங்கள்", 3, 4, 12),
        briefs("b-central", "மத்திய அறிவிப்புகள் · தமிழகத் தாக்கம்", 2, 4, 8),
        briefs("b-city", "சென்னை", 3, 3, 9),
        briefs("b-districts", "மாவட்டங்கள்", 2, 3, 6),
    ]}

    page3 = {"number": 3, "kind": "inner", "section": "போராட்டம் · பாராட்டு · வானிலை",
             "cols": 5, "rows": 12, "accent": "#b45309", "palette": "civic", "blocks": [
        story("s-protest", 3, 3, 3, "மக்கள் போராட்டம்", "போராட்டச் செய்தி",
              f"சென்னை, {day.day}", "lead", None, 5),
        {"id": "t-panchangam", "type": "table", "col": 2, "row": 3,
         "title": "இன்றைய பஞ்சாங்கம்",
         "items": [{"k": "மாதம் · நாள்", "v": f"{tamil_day} · {weekday}".strip(" ·")},
                   {"k": "ராகு காலம்", "v": rahu},
                   {"k": "எமகண்டம்", "v": emakandam},
                   {"k": "குளிகை", "v": kuligai},
                   {"k": "சூலம்", "v": soolam},
                   {"k": "சூரிய உதயம்", "v": ""},
                   {"k": "சூரிய அஸ்தமனம்", "v": ""},
                   {"k": "நல்ல நேரம்", "v": ""},
                   {"k": "பருவகாலம்", "v": ""},
                   {"k": "சந்திராஷ்டமம்", "v": ""},
                   {"k": "வருடம்", "v": ""},
                   {"k": "இன்றைய சிறப்பு", "v": ""}],
         "note": "வாரநாளுக்குரிய நிலையான நேரங்கள்."},
        briefs("b-success", "இன்றைய நிகழ்வுகள் · சாதனை", 3, 3, 8),
        briefs("b-jobs", "வேலைவாய்ப்பு அழைப்பு", 2, 3, 6),
        {"id": "wx-map", "type": "weather", "col": 5, "row": 3,
         "title": "இன்றைய வானிலை நிலவரம்", "subtitle": "தமிழகத்தில் இன்று எப்படி?",
         "summary": "வானிலை நிலவரம்.", "label_size": 21,
         "categories": [{"key": "m", "label": "மிதமான மழை", "color": "#16357c",
                         "districts": ["chennai"]},
                        {"key": "l", "label": "லேசான மழை", "color": "#7fb0d4",
                         "districts": ["madurai"]}],
         "temperature": [{"range": "", "label": "சென்னை", "where": "அதிக / குறை"},
                         {"range": "", "label": "காற்று", "where": "கி.மீ./மணி"},
                         {"range": "", "label": "சூரிய உதயம்", "where": "காலை"}],
         "note": "ஆதாரம்: இந்திய வானிலை ஆய்வு மையம், சென்னை."},
        briefs("b-world", "உலகம் · பொருளாதாரம்", 5, 3, 12),
    ]}

    for page in (page1, page2, page3):
        used = sum(b["col"] * b["row"] for b in page["blocks"])
        want = page["cols"] * page["rows"]
        assert used == want, f"page {page['number']}: covers {used} of {want} cells"

    return {"paper": paper, "press": {"preset": "tabloid"}, "palette": "civic",
            "pages": [page1, page2, page3]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", default=dt.date.today().isoformat(),
                    help="edition date, YYYY-MM-DD (default: today)")
    ap.add_argument("-o", "--out", default="content/daily.json")
    args = ap.parse_args()

    edition = build(dt.date.fromisoformat(args.date))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(edition, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    items = sum(len(b["items"]) for p in edition["pages"] for b in p["blocks"]
                if b["type"] == "briefs")
    stories = sum(1 for p in edition["pages"] for b in p["blocks"] if b["type"] == "story")
    print(f"{out}  ·  3 pages, {stories} story slots, {items} brief slots")
    if not tamil_month_day(dt.date.fromisoformat(args.date)):
        print("  note: Tamil month left blank — outside the range this can count off. "
              "Fill it from today's panchangam.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
