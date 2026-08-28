# The daily edition — standing procedure

This is the checklist the 6 am job follows. It exists so every morning's paper
comes out the same way, and so the rules that matter are written down rather
than remembered.

**Working branch:** `claude/tamil-newspaper-creation-8toaev`
**Output:** `output/daily/<YYYY-MM-DD>.pdf`, committed and pushed.

---

## 0. Set up

```bash
git fetch origin claude/tamil-newspaper-creation-8toaev
git checkout claude/tamil-newspaper-creation-8toaev
git pull --ff-only origin claude/tamil-newspaper-creation-8toaev
bash tools/setup.sh
```

## 1. Gather the news

Try the fetcher first. It is the cheaper and more reproducible path:

```bash
python3 tools/fetch_news.py --check-feeds
```

**If the feeds are reachable**, build the draft and then rewrite it:

```bash
python3 tools/fetch_news.py --window 14 -o content/daily.json
```

**If they are not** — many environments block news domains at the egress
proxy — fall back to `WebSearch`, which reaches a different network path.
Search for the day's news beat by beat rather than in one sweep; general
queries return almanac pages, specific ones return stories:

- `Tamil Nadu Chennai news today <date>`
- `<date> Chennai <a publication you know files daily>`
- `Tamil Nadu weather rain forecast IMD <date>`
- `India news <date> <a concrete subject>`
- `gold silver rate Chennai <date>`
- `<sport in season> result <date>`
- **Tamil Nadu's own sport, every day** — the state league or tournament in
  season, Chennai clubs and franchises, state teams and school championships.
  A Tamil paper that covers only national cricket is missing its own back
  page. Search the competition by name: `TNPL <date>`, `Tamil Thalaivas`,
  `Tamil Nadu <sport> championship <date>`.
- world: search the running story by name, not "world news"

## 2. Write it

Write the copy in Tamil, in newspaper register. The layout is already good;
what makes the paper is the writing.

**The rules, in order of importance:**

1. **Never invent a fact.** Not a number, not a name, not a quote, not a
   date. If a detail is not in the source, it does not go in the paper.
2. **Credit every story.** Each story block takes a `source` line —
   `"ஆதாரம்: <publication>, <date>"` — and every publication used goes in the
   `sources` block on the last page.
3. **Print only what is corroborated.** If two sources disagree, or a search
   summary looks garbled, leave it out. A shorter paper is not a worse one.
4. **Say what this edition is** — but briefly. The masthead ear, the `source`
   line under each story and the sources box on the last page carry it. Do
   **not** run a separate "about this edition" panel; the credits do the work
   and the panel only takes space a story could use.
5. **Do not translate a claim into a stronger one.** "may rise" is not
   "will rise"; "sources said" is not "the government announced".

## 3. Build

```bash
python3 build.py content/daily.json -o output/daily/$(date +%F).pdf
```

Read the copy-fitting report. It is the make-up editor's eye:

- a block that **cut paragraphs** is over-set — shorten the copy or give the
  block another row;
- a block **filling under 88%** will leave a hole — lengthen it, shrink it,
  or move it;
- fix these before publishing. Both are one number in the edition file.

**Size the sheet to the copy, never the copy to the sheet.** With a normal
day's material `tabloid` is right. With very little, drop to `a3` or `a4`.
Padding a broadsheet with invented sentences is the one failure mode this
whole pipeline exists to prevent.

## 4. Publish

Keep the last 30 editions and drop the rest — a paper a day at a couple of
megabytes would grow the repository by about a gigabyte a year, and nothing is
lost that cannot be rebuilt from the edition file beside it:

```bash
ls -1 output/daily/*.pdf | sort | head -n -30 | xargs -r git rm --quiet
git add content/daily.json output/daily/
git commit -m "Edition of <date>"
git push origin claude/tamil-newspaper-creation-8toaev
```

Then send the PDF with `SendUserFile`, and give the raw GitHub link as well —
it is the reliable route on a phone:

```
https://github.com/Ezhilbio1987/Ezhilbio1987/raw/claude/tamil-newspaper-creation-8toaev/output/daily/<date>.pdf
```

`build.py` repacks the PDF on the way out, which roughly halves it. If it is
still over about 4 MB, also render the pages to PNG and send those; large
downloads stall on mobile.

```bash
python3 -c "
import pymupdf, sys
d = pymupdf.open(sys.argv[1])
for i, p in enumerate(d):
    p.get_pixmap(dpi=105).save(f'output/daily/page-{i+1}.png')
" output/daily/<date>.pdf
```

## 5. When the news will not come

If neither the feeds nor search yield enough for a page, **do not fabricate an
edition**. Send a short message saying what was unavailable and why. A missed
morning is recoverable; a paper of invented news is not.

---

## Reference

**Standing sections.** Tamil Nadu and Chennai lead; then the weather page with
its district map; then world and business; then sport, which always includes a
Tamil Nadu sports panel alongside any national or international result.

**Pictures.** The drawn stand-ins are credited `விளக்கப் படம்` — illustration.
Never credit them as a photograph (`கோப்புப் படம்`, `நிருபர் படம்`): they are
not one. Use those credits only for a real image supplied with `src`.

- Content schema, block types, press presets: `README.md`
- Weather page and district map: `README.md`, `tools/build_map.py`
- Colour: `page.accent`, `palette` — see `README.md`
- Worked example with real sourcing: `content/evening-edition.json`
