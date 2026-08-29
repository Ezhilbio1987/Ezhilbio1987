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

**This is a digest, not a magazine.** The edition runs **five pages** and
carries **140 items or more** — that is the floor, not the target; if a page
has room, fill it with another item. **No story runs past 200 words.** Breadth beats depth: a reader wants to
know what happened across the state, the country and the world, not one story
at length. So:

- 8 to 12 items get a block of their own, at 100–200 words;
- everything else runs as a **brief** — a headline and two or three sentences
  in a panel. Most of the paper is briefs, and that is correct;
- one fact per item is often enough. Resist adding background the source did
  not carry;
- **leave no gap deeper than two lines.** Run `tools/refit.py`, then fill what
  it reports as slack with more items.

**The five zones that must appear every day.** Whatever else the day gives,
the paper leads on these and gives each of them room:

1. **The top political event** — the assembly, the courts, the parties, the
   Union–state relationship. This is page one's lead unless something bigger
   displaces it.
2. **Government scheme announcements, state and central.** Both, every day.
   A central announcement is usually an instruction to the states, so
   **always carry what it means for Tamil Nadu** — a subsidy against the
   delta's samba season, a GST cut against Tiruppur knitwear, a tariff change
   against the state's exporters. The instruction alone is only half the item.
3. **Public protest and demand** — strikes, hunger strikes, walkouts,
   deputations, village agitations. These are the stories other papers bury
   inside; run them with names, places and dates.
4. **Employment calls** — TNPSC, TRB, railway, SSC, banking and state
   recruitment notifications, with the closing date and the eligibility line.
   A reader should be able to act on the item.
5. **Appreciation, success and the event of the day** — awards, titles won,
   a school that opened, the day's observance. End the reader's page on
   something that happened well.

**Cover every sector.** A page should not be one beat: politics, education,
health, agriculture, city and civic, courts, culture, science, business,
economy, sport and world all belong in the paper. The five pages run roughly:

| page | sections |
| --- | --- |
| 1 | the day's political lead, the second lead, weather box, two briefs panels |
| 2 | government schemes — state, then central with its Tamil Nadu impact — plus city and districts |
| 3 | appreciation and success, public protest, the weather map, the panchangam |
| 4 | sport: national first, then Tamil Nadu, then world |
| 5 | economy, employment calls, education, science, world |

**Run the panchangam every day.** A `table` block on page 3 carrying the
year, month and day, tithi, natchathiram, yogam, karanam, sunrise and sunset,
the auspicious hours, Rahu kalam, Emakandam, Kuligai, Chandrashtamam, soolam
and the day's observance. Source it and date it like any other item — it is
the page readers turn to first, so a wrong Aavani date is a real error.

**Sport runs national first, then Tamil Nadu.** The national panel leads —
cricket, hockey, chess, badminton, whatever the day gave — and the Tamil Nadu
panel follows it, never the other way round. World sport comes after both.

If a beat yields nothing, drop it and give the room to one that did. Search
beat by beat — Tamil Nadu government, Chennai civic, districts, courts,
education, health, agriculture, transport, weather, prices, business,
national, world, Tamil Nadu sport, national and international sport, cinema —
because one broad query returns almanac pages while narrow ones return
stories.

**The rules, in order of importance:**

1. **Never invent a fact.** Not a number, not a name, not a quote, not a
   date. If a detail is not in the source, it does not go in the paper.
2. **Credit every story.** Each story block takes a `source` line —
   `"ஆதாரம்: <publication>, <date>"` — and every publication used goes in the
   `sources` block on the last page.
3. **Print only what is corroborated.** If two sources disagree, or a search
   summary looks garbled, leave it out. A shorter paper is not a worse one.
4. **Credit in the story, nowhere else.** Each story carries a one-line
   `source` credit under its last column — the way a paper credits agency
   copy. That is the whole of it. Do **not** run an "about this edition"
   panel, a sources box, a note under a list, a footline disclaimer, or a
   declaration in the masthead ear. Apparatus is not news, and the page is
   for news. The footline carries the edition and date; the right-hand ear
   carries the day's flashes.
5. **Ask for a subject, not a picture.** A figure says
   `{"subject": "sattamandram"}` and the builder decides: the filed
   photograph if `assets/photos/library.json` has one for that subject,
   otherwise the scene drawn for it. File a photograph later and every story
   that asks for the subject upgrades, with no edition to edit.

   Subjects filed today: `sattamandram` (a real chamber photograph),
   `assembly`, `secretariat`, `scheme`, `cricket`, `hockey`, `stadium`,
   `protest`, `farm`, `city`, `market`, `science`.

   **Match the subject to the actual event.** A hockey report does not get
   the cricket ground — stumps and a pitch strip in a hockey picture is the
   wrong picture, not a stylistic choice. Add a scene rather than reuse a
   near-miss.

   To file a photograph: put it in `assets/photos/library/<subject>.jpg`,
   add `file` and `credit` to that subject in `library.json`. A reused
   photograph is credited `கோப்புப் படம்: <source>`; a one-off from today's
   reporting is `படம்: <source>`. Only a drawing is `விளக்கப் படம்`.

   Note that no image host is reachable from the build environment — every
   one answers 403 at the proxy — so photographs arrive only as files, and
   the library is how they earn their keep across editions.

6. **Use a real photograph wherever one exists.** A genuine picture is what
   makes the page trustworthy, so a drawn stand-in is the fallback, never the
   default. Put the file in `assets/photos/` and name it in the figure as
   `"src": "assets/photos/<date>-<subject>.jpg"`; the builder inlines it as a
   data URI so the PDF carries it. Credit it `"படம்: <source>"`.
   - **Never lift an advertisement or a designed poster** out of a source and
     run it as a news picture. If a campaign graphic has a real photograph
     inset in it, crop the photograph out and use only that.
   - A drawn stand-in is credited `விளக்கப் படம்` and never
     `கோப்புப் படம்` or `நிருபர் படம்` — it is not a photograph and must not
     read as one.
   - A photo story needs **three columns**. A picture spanning a two-column
     block breaks the make-up and the fitter will silently drop paragraphs.
7. **No house advertisements.** Space on the page belongs to news. If a block
   has nothing to fill it, run local briefs there — Chennai civic, transport,
   water, corporation and neighbourhood items are always worth the room.
8. **Do not translate a claim into a stronger one.** "may rise" is not
   "will rise"; "sources said" is not "the government announced".

## 3. Build

```bash
python3 build.py content/daily.json -o output/daily/$(date +%F).pdf
python3 tools/refit.py content/daily.json      # resize blocks to the copy
python3 build.py content/daily.json -o output/daily/$(date +%F).pdf
```

`refit.py` closes the loop: it reads how full each block came out and resizes
every block to what its copy actually needs, re-packing each page so the grid
is still covered exactly. Run it, then build again. It never edits copy — if
a page still has room to spare, the answer is another item, not bigger type.

Read the copy-fitting report. It is the make-up editor's eye:

- a block that **cut paragraphs** is over-set — shorten the copy or give the
  block another row;
- a block **filling under 88%** will leave a hole — lengthen it, shrink it,
  or move it;
- **the same item running twice** is reported by headline — an edition
  assembled from several panels repeats itself if nobody is watching. The
  check only catches identical headlines, so read the panels yourself for the
  same story told twice under different words;
- fix these before publishing.

**Size the paper to the copy, never the copy to the paper.** Count the cells
the copy needs against the cells the pages have — a tabloid page is 55. Sixty
short items came to about 165 cells, which is three pages, not four. Run
fewer pages rather than four slack ones, and drop to `a3` or `a4` on a thin
day. Padding a page with invented sentences is the one failure mode this
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

Two rules, and they do not conflict — hold both.

**Never fabricate.** Not a number, a name, a quote or a date. A paper of
invented news is not recoverable.

**Always deliver something.** A thin day means a *shorter paper*, not no
paper. Drop to four pages, or three; run the sections that have copy and cut
the ones that do not; say plainly at the end what was thin. Sizing the paper
to the copy is the normal response to a quiet day — it is what section 2 asks
for — and it is not a failure worth withholding the edition over.

The failure mode this replaces is real: on 29 August the 6 am routine ran for
thirty-three minutes, reported success, and delivered nothing at all. Reading
"do not fabricate" as "send nothing" is the wrong reading. The reader wanted a
paper and got silence, which is worse than a three-page paper would have been.

Send nothing only if the build itself is broken or every source is
unreachable — and then say so explicitly, in a message to the reader. Finishing
quietly is never an outcome.

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
