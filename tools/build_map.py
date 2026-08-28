#!/usr/bin/env python3
"""Turn district boundary data into the compact SVG map the weather page uses.

This is a one-off generator, kept in the repo so the map data can be rebuilt
or swapped for a different state. It reads a GADM-style district GeoJSON,
keeps the districts of one state, simplifies the rings enough to print
cleanly at newspaper size, projects them, and writes a small JSON file of SVG
path data plus a label anchor per district.

    python3 tools/build_map.py india_district.geojson --state "Tamil Nadu"

Source used for the shipped map: geohacker/india (district boundaries),
derived from GADM. The district set is the pre-2019 one, so districts created
by later splits appear inside their parent district.
"""

import argparse
import json
import math
import sys
from pathlib import Path

# Coastline rings run to thousands of vertices; the simplifier recurses once
# per split.
sys.setrecursionlimit(200_000)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "maps" / "tamilnadu.json"

# GADM spellings -> the Tamil names the paper prints.
TAMIL_NAMES = {
    "Ariyalur": "அரியலூர்",
    "Chennai": "சென்னை",
    "Coimbatore": "கோயம்புத்தூர்",
    "Cuddalore": "கடலூர்",
    "Dharmapuri": "தருமபுரி",
    "Dindigul": "திண்டுக்கல்",
    "Erode": "ஈரோடு",
    "Kancheepuram": "காஞ்சிபுரம்",
    "Kanniyakumari": "கன்னியாகுமரி",
    "Karur": "கரூர்",
    "Madurai": "மதுரை",
    "Nagapattinam": "நாகப்பட்டினம்",
    "Namakkal": "நாமக்கல்",
    "Nilgiris": "நீலகிரி",
    "Perambalur": "பெரம்பலூர்",
    "Pudukkottai": "புதுக்கோட்டை",
    "Ramanathapuram": "ராமநாதபுரம்",
    "Salem": "சேலம்",
    "Sivaganga": "சிவகங்கை",
    "Thanjavur": "தஞ்சாவூர்",
    "Theni": "தேனி",
    "Thiruvallur": "திருவள்ளூர்",
    "Thiruvarur": "திருவாரூர்",
    "Thoothukudi": "தூத்துக்குடி",
    "Tiruchchirappalli": "திருச்சி",
    "Tirunelveli Kattabo": "திருநெல்வேலி",
    "Tiruvannamalai": "திருவண்ணாமலை",
    "Vellore": "வேலூர்",
    "Villupuram": "விழுப்புரம்",
    "Virudhunagar": "விருதுநகர்",
    "Puducherry": "புதுச்சேரி",
    "Karaikal": "காரைக்கால்",
}

# Slugs the edition file refers to districts by.
SLUGS = {
    "Tiruchchirappalli": "tiruchirappalli",
    "Tirunelveli Kattabo": "tirunelveli",
    "Thiruvallur": "tiruvallur",
    "Thiruvarur": "tiruvarur",
    "Kancheepuram": "kancheepuram",
    "Kanniyakumari": "kanniyakumari",
}


def slug(name: str) -> str:
    return SLUGS.get(name) or name.lower().replace(" ", "-")


def perpendicular_distance(pt, start, end) -> float:
    (x, y), (x1, y1), (x2, y2) = pt, start, end
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(x - x1, y - y1)
    return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / math.hypot(dx, dy)


def simplify(points: list, tolerance: float) -> list:
    """Ramer–Douglas–Peucker. Keeps the shape of a coastline while dropping the
    vertex count by an order of magnitude, which is what makes the map small
    enough to inline in the page."""
    if len(points) < 3:
        return points
    worst, index = 0.0, 0
    for i in range(1, len(points) - 1):
        d = perpendicular_distance(points[i], points[0], points[-1])
        if d > worst:
            worst, index = d, i
    if worst <= tolerance:
        return [points[0], points[-1]]
    left = simplify(points[: index + 1], tolerance)
    right = simplify(points[index:], tolerance)
    return left[:-1] + right


def ring_area(ring: list) -> float:
    total = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2


def ring_centroid(ring: list) -> tuple:
    cx = cy = a = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        cross = x1 * y2 - x2 * y1
        a += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if a == 0:
        return ring[0]
    a *= 0.5
    return (cx / (6 * a), cy / (6 * a))


def rings_of(geometry: dict) -> list:
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"][0]]
    if geometry["type"] == "MultiPolygon":
        return [poly[0] for poly in geometry["coordinates"]]
    raise ValueError(f"unsupported geometry {geometry['type']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("geojson", help="district-level GeoJSON (GADM style properties)")
    ap.add_argument("--state", default="Tamil Nadu")
    ap.add_argument("--also", nargs="*", default=["Puducherry"],
                    help="other NAME_1 values to include (enclaves, union territories)")
    ap.add_argument("--tolerance", type=float, default=0.006,
                    help="simplification tolerance in degrees (~0.006 = 650 m)")
    ap.add_argument("--min-area", type=float, default=0.0008,
                    help="drop islets smaller than this, in square degrees")
    ap.add_argument("--width", type=float, default=1000.0, help="SVG viewBox width")
    ap.add_argument("-o", "--output", default=str(OUT))
    args = ap.parse_args()

    data = json.loads(Path(args.geojson).read_text())
    wanted = {args.state, *args.also}
    features = [f for f in data["features"] if f["properties"]["NAME_1"] in wanted]
    # Puducherry's far-flung enclaves are not in this state's map.
    features = [f for f in features if f["properties"]["NAME_2"] not in {"Mahe", "Yanam"}]
    if not features:
        raise SystemExit(f"no districts found for {args.state!r}")

    collected = []
    for feature in features:
        name = feature["properties"]["NAME_2"]
        rings = []
        for ring in rings_of(feature["geometry"]):
            ring = [(float(x), float(y)) for x, y in ring]
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            if ring_area(ring) < args.min_area:
                continue
            simplified = simplify(ring, args.tolerance)
            if len(simplified) >= 4:
                rings.append(simplified)
        if rings:
            collected.append((name, rings))

    lons = [x for _, rings in collected for ring in rings for x, _ in ring]
    lats = [y for _, rings in collected for ring in rings for _, y in ring]
    lon0, lon1 = min(lons), max(lons)
    lat0, lat1 = min(lats), max(lats)
    # Equirectangular, with longitudes squeezed by cos(latitude) so the state
    # keeps its true proportions on the page.
    k = math.cos(math.radians((lat0 + lat1) / 2))
    span_x = (lon1 - lon0) * k
    span_y = lat1 - lat0
    scale = args.width / span_x
    height = span_y * scale

    def project(x, y):
        return ((x - lon0) * k * scale, (lat1 - y) * scale)

    districts = []
    for name, rings in collected:
        paths = []
        for ring in rings:
            pts = [project(x, y) for x, y in ring]
            d = "M" + " L".join(f"{px:.1f} {py:.1f}" for px, py in pts) + " Z"
            paths.append(d)
        biggest = max(rings, key=ring_area)
        cx, cy = project(*ring_centroid(biggest))
        districts.append({
            "slug": slug(name),
            "name_en": name,
            "name_ta": TAMIL_NAMES.get(name, name),
            "d": " ".join(paths),
            "label": [round(cx, 1), round(cy, 1)],
            "area": round(sum(ring_area(r) for r in rings), 5),
        })

    districts.sort(key=lambda item: item["slug"])
    out = {
        "viewBox": [0, 0, round(args.width, 1), round(height, 1)],
        "state": args.state,
        "source": "GADM district boundaries via geohacker/india; pre-2019 district set",
        "districts": districts,
    }
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n",
                    encoding="utf-8")
    vertices = sum(item["d"].count("L") + item["d"].count("M") for item in districts)
    print(f"{len(districts)} districts, {vertices} vertices -> {path} "
          f"({path.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
