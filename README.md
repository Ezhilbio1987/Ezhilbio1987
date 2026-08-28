# பீனிக்ஸ் மலர் செய்தி — a Tamil newspaper you can print

A press-ready Tamil daily, generated from a plain JSON file.

Write the edition as copy — headlines, paragraphs, a picture here and there —
and the builder lays it out on a real broadsheet grid and prints it to PDF at
true press size (350 × 520 mm by default, the sheet most Tamil dailies run on).

```bash
pip install -r requirements.txt
python3 -m playwright install chromium     # skip if Chromium is already installed
python3 build.py --preview
open output/edition.pdf
```

The sample edition in `content/edition.json` is a complete four-page paper:
a front page, a Tamil Nadu page, a weather page built around a real district
map of the state, and a world/business/sport page.

> **The sample content is fiction.** Every story, name, figure and weather
> reading in `content/edition.json` was invented to fill the pages. Replace it
> with your own copy before the paper means anything.

## Why the type comes out right

Tamil is a complex script: vowel signs reorder around the consonant they
attach to, and consonant clusters form ligatures. Get that wrong and the page
is unreadable.

- **Chromium does the shaping.** The page is laid out in headless Chromium and
  printed from there, so HarfBuzz handles the reordering and ligatures.
- **The PDF carries real Unicode.** Text in the output is selectable,
  searchable and copy-pastable. Many Tamil papers are still set in the legacy
  TAB/TAM 8-bit encodings, where copying a headline out of the PDF gives you
  mojibake.
- **The face is condensed on purpose.** Tamil words are long, so a narrow
  justified column fits few of them per line and the word spaces stretch into
  rivers. Noto Serif/Sans Tamil carry a width axis (62.5–100%), and body copy
  is set at 88% width, headlines at 76%. That is what news text faces have
  always done, and it is one `font-stretch` declaration here.

## Copy fitting

Every block sits in a fixed box on the page grid, so the copy has to be made to
fit it — the job a make-up editor does by hand. `assets/js/fit.js` runs in the
page before it prints and, per block:

1. binary-searches a type scale between 84% and 112% that makes the copy fill
   its box,
2. if the copy still overruns at the smallest size, drops trailing paragraphs
   and sets a jump line,
3. reports what it had to do.

The build prints that report, so you can see which blocks were squeezed and
which came up short:

```
  · p1-lead: type 85%, fills 98%
  · p3-weather: type 112%, fills 100%
  ! p3-agri: type 97%, fills 77%, short — add copy or shrink the block
```

`fills` is the fraction of the box the type actually covers. Under 88% the
build warns you: the page will have a white hole, and the fix is more copy or
fewer rows.

## Writing an edition

`content/edition.json` has three parts: `paper` (masthead and dateline),
`press` (which sheet to print on) and `pages`.

### A page

```json
{
  "number": 2,
  "kind": "inner",
  "section": "தமிழ்நாடு",
  "cols": 6,
  "rows": 12,
  "blocks": [ ... ]
}
```

`kind` is `front` (nameplate and dateline bar) or `inner` (folio bar). Every
page is a `cols` × `rows` grid; each block declares how many of those cells it
takes, and blocks are placed first-fit in the order you list them. A block can
pin itself with `"at": [col, row]`.

### A story

```json
{
  "type": "story",
  "col": 3, "row": 5, "columns": 3,
  "variant": "major",
  "kicker": "சுகாதாரம்",
  "headline": "மாவட்ட மருத்துவமனைகளில் இரவு நேர சிறப்புச் சிகிச்சைப் பிரிவு",
  "deck": "32 இடங்களில் இன்று தொடக்கம்",
  "byline": { "name": "ப. அன்பரசி", "role": "நிருபர்" },
  "place": "சென்னை, ஆக. 28",
  "figures": [
    { "scene": "lab", "after": 3, "caption": "…", "credit": "நிருபர் படம்" }
  ],
  "body": [
    "First paragraph — `place` is set into it as the dateline.",
    "## A crosshead",
    "More copy."
  ]
}
```

- `col` / `row` — size on the page grid. `columns` — how many text columns the
  copy sets in; matching it to `col` keeps every column on the page the same
  measure.
- `variant` — `lead`, `major`, `minor` or `brief`; sets the headline size and,
  for `lead`, the drop cap.
- `rule` — `accent` (red), `hairline` or `norule` for the rule above the story.
- A `body` entry beginning `## ` becomes a crosshead.
- `figures[].after: n` drops the picture into the copy after the *n*th
  paragraph, so it sets into the column flow the way a made-up picture does.
- `jump` — the continuation line to run if the copy has to be cut.
- `editorial: true` with `standfirst` sets the leader column.

### Other blocks

| `type` | what it is |
| --- | --- |
| `briefs` | a panel of short items — news in brief, readers' letters |
| `index` | the "இன்றைய இதழில்" contents box |
| `table` | label/value rows — weather, market rates |
| `quote` | a pulled quotation between heavy rules |
| `advert` | a boxed display advertisement |
| `classifieds` | small ads in two columns |
| `picture` | a standalone photograph with a caption |
| `weather` | the district weather map and its panels |

### The weather page

```json
{
  "type": "weather",
  "col": 6, "row": 5,
  "title": "இன்றைய வானிலை நிலவரம்",
  "categories": [
    { "label": "கனமழை பெய்ய வாய்ப்பு", "color": "#16357c",
      "districts": ["kanniyakumari", "tirunelveli", "thoothukudi"] }
  ],
  "temperature": [ { "range": "35° – 38°", "label": "அதிக வெப்பம்", "where": "வேலூர்" } ],
  "advisories": [ { "title": "பொதுமக்களுக்கு", "text": "…" } ]
}
```

Each category names the districts it covers, and they are filled with its
colour on the map. Name a district that does not exist and the build stops and
lists the valid slugs. The map keeps its own proportions, filling the height it
is given and leaving the rest of the width to the panels either side, so it
needs no hand-tuning when you resize the block.

The shipped map is Tamil Nadu and Puducherry, drawn from GADM district
boundaries via [geohacker/india](https://github.com/geohacker/india). It is the
pre-2019 district set, so districts created by later splits appear inside their
parent district — the sample edition says so in its footnote. To rebuild it, or
to build a map of somewhere else:

```bash
python3 tools/build_map.py path/to/district.geojson --state "Tamil Nadu"
```

### Pictures without photographs

So the sample edition ships without binary assets, `scene` draws a duotone SVG
under a halftone screen — roughly what a photograph looks like once it has been
through a newspaper press. Available scenes: `portrait`, `dais`, `assembly`,
`city`, `stadium`, `field`, `lab`, `crowd`, `chart`, `stage`. Give a figure a
`src` instead and it uses your image.

## Press sizes

```
$ python3 build.py --list-presets
 * indian-broadsheet    350mm × 520mm   grid 6×12   இந்திய பிராட்ஷீட்
   broadsheet           305mm × 559mm   grid 6×13   US broadsheet · 12 × 22 in
   berliner             315mm × 470mm   grid 5×11   Berliner
   tabloid              279mm × 432mm   grid 5×11   Tabloid · 11 × 17 in
   a3                   297mm × 420mm   grid 5×10   A3
   a4                   210mm × 297mm   grid 4×9    A4
```

Set one in the edition file (`"press": {"preset": "a3"}`) or override it for a
single build with `--press a3`. The copy fitter will resize the type into the
new boxes; a much smaller sheet will need the copy cut to suit.

## Command line

```
python3 build.py [edition.json] [-o out.pdf] [--press NAME]
                 [--preview] [--keep-html] [--quiet] [--list-presets]
```

`--preview` writes a full-length PNG proof beside the PDF. `--keep-html` keeps
the intermediate HTML, which is the quickest way to inspect a layout — open it
in a browser and the page looks exactly as it prints.

## Layout of the repository

```
build.py                  CLI
src/tamilpaper/
  content.py              loads and validates an edition, normalises it
  layout.py               places blocks on the page grid
  press.py                sheet sizes
  weather.py              the district map
  artwork.py              SVG stand-in press pictures
  render.py               HTML from the template
  pdf.py                  Chromium print-to-PDF
templates/edition.html.j2
assets/css/               newspaper.css, fonts.css
assets/js/fit.js          copy fitting
assets/fonts/             Noto Serif/Sans Tamil, variable
assets/maps/tamilnadu.json
tools/build_map.py        regenerate the map from boundary data
content/edition.json      the sample edition
output/edition.pdf        the sample edition, printed
```

## Licences

The fonts are Noto Serif Tamil and Noto Sans Tamil, under the SIL Open Font
License 1.1 — see `assets/fonts/LICENSE-*.txt`. The district boundaries come
from GADM via geohacker/india.
