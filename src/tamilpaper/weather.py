"""The weather page: a district map, coloured by what the day is expected to do.

The map data is built once by ``tools/build_map.py`` and lives in
``assets/maps/``. Here it is turned into an SVG with each district filled
according to the rainfall category the edition puts it in, which is how Tamil
papers run their daily weather graphic.
"""

import json
from pathlib import Path

MAPS = Path(__file__).resolve().parents[2] / "assets" / "maps"

# Fallback ramp, darkest for the heaviest rain, used when a category in the
# edition file does not name its own colour.
RAMP = ["#16357c", "#38699f", "#7ba3c4", "#b9cfe0", "#ece7db"]

UNCLASSIFIED = "#f2eee5"


class WeatherError(ValueError):
    pass


def load_map(name: str = "tamilnadu") -> dict:
    path = MAPS / f"{name}.json"
    if not path.exists():
        raise WeatherError(
            f"no map data at {path}. Build it with: "
            f"python3 tools/build_map.py <district.geojson>"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_map(block: dict) -> str:
    """Return the inline SVG for a weather block's district map."""
    data = load_map(block.get("map", "tamilnadu"))
    known = {d["slug"]: d for d in data["districts"]}

    fills: dict[str, str] = {}
    for index, category in enumerate(block.get("categories") or []):
        colour = category.get("color") or RAMP[min(index, len(RAMP) - 1)]
        category["color"] = colour
        unknown = [s for s in category.get("districts", []) if s not in known]
        if unknown:
            raise WeatherError(
                f"weather block {block.get('id')}: unknown district(s) "
                f"{', '.join(unknown)}. Known slugs: {', '.join(sorted(known))}"
            )
        for slug in category.get("districts", []):
            fills[slug] = colour

    vb = data["viewBox"]
    label_size = float(block.get("label_size", 21))
    show_labels = block.get("labels", True)

    out = [
        f'<svg viewBox="{vb[0]} {vb[1]} {vb[2]} {vb[3]}" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="{_escape(block.get("title", "weather map"))}">',
        # Sea behind the coastline, so the state reads as a shape not a blob.
        f'<rect x="{vb[0]}" y="{vb[1]}" width="{vb[2]}" height="{vb[3]}" fill="#ffffff"/>',
        '<g stroke="#ffffff" stroke-width="2.4" stroke-linejoin="round">',
    ]
    for district in data["districts"]:
        colour = fills.get(district["slug"], UNCLASSIFIED)
        out.append(f'<path d="{district["d"]}" fill="{colour}"/>')
    out.append("</g>")

    # A heavier outline around the whole state, drawn by stroking every
    # district again with no fill — cheaper than computing a true union and
    # visually the same once the interior rules sit on top.
    out.append('<g fill="none" stroke="#1d1b22" stroke-width="1.1" stroke-linejoin="round">')
    for district in data["districts"]:
        out.append(f'<path d="{district["d"]}"/>')
    out.append("</g>")

    if show_labels:
        out.append(
            f'<g font-family="Paper Sans, sans-serif" font-size="{label_size}" '
            f'font-weight="600" text-anchor="middle" fill="#14131a">'
        )
        for district in data["districts"]:
            if district["slug"] in (block.get("hide_labels") or []):
                continue
            x, y = district["label"]
            name = _escape(district["name_ta"])
            # A white casing under the label keeps it legible over dark fills.
            out.append(
                f'<text x="{x}" y="{y}" stroke="#ffffff" stroke-width="{label_size * 0.30:.1f}" '
                f'stroke-linejoin="round" paint-order="stroke">{name}</text>'
            )
        out.append("</g>")

    out.append("</svg>")
    return "".join(out)


def prepare(block: dict) -> None:
    """Resolve a weather block: build its map and total up its district counts."""
    for field in ("title", "categories"):
        if not block.get(field):
            raise WeatherError(f"weather block {block.get('id')} is missing '{field}'")

    data = load_map(block.get("map", "tamilnadu"))
    names = {d["slug"]: d["name_ta"] for d in data["districts"]}

    block["svg"] = render_map(block)
    # The page sizes the map box from the map's own proportions, so it always
    # fills the height it is given and takes only the width it needs.
    vb = load_map(block.get("map", "tamilnadu"))["viewBox"]
    block["map_aspect"] = f"{vb[2]} / {vb[3]}"
    for category in block["categories"]:
        slugs = category.get("districts", [])
        category["names"] = "， ".join(names[s] for s in slugs).replace("， ", ", ")
        category["count"] = len(slugs)

    classified = {s for c in block["categories"] for s in c.get("districts", [])}
    block["unclassified"] = sorted(set(names) - classified)
    block.setdefault("subtitle", "")
    block.setdefault("summary", "")
    block.setdefault("note", "")
    block.setdefault("temperature", [])
    block.setdefault("advisories", [])
