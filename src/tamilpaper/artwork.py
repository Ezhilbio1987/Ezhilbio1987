"""Stand-in press pictures.

Real editions drop in photographs. So the sample edition can ship without any
binary assets, this draws duotone SVG scenes with a halftone screen over them,
which is roughly what a photograph looks like once it has been through a
newspaper press. Swap any of them for a real picture by giving the figure a
``src`` instead of a ``scene``.
"""

import hashlib

W, H = 300, 200

# Seven steps, darkest first. Print editions run the grey ramp — newsprint
# never reaches true black. An online edition is not paying for ink, so the
# scenes can carry colour; each palette is the same seven steps tinted, so a
# scene drawn against one works against any of them.
PALETTES = {
    "grey":  ["#26242c", "#3d3a45", "#57535f", "#77727e", "#a49fa8", "#cbc6c0", "#e6e1d7"],
    "civic": ["#111d3d", "#1f3companion", "#2f5390", "#5b7fbe", "#9db4d8", "#c9d7ea", "#e8eef7"],
    "dusk":  ["#331a12", "#5c2b18", "#8c4420", "#c06a2e", "#e0975a", "#f0c496", "#fae4cd"],
    "field": ["#14301c", "#1f4a2a", "#356b3c", "#5e9455", "#94bd80", "#c3ddad", "#e6f2d8"],
    "sea":   ["#062b33", "#0c4a54", "#136e78", "#2c98a0", "#6dbfc2", "#a9dcdb", "#dcf1ef"],
    "rose":  ["#3a0f1c", "#5f1a2c", "#8c2740", "#bb4a63", "#d98395", "#eeb7c2", "#fadfe5"],
}
PALETTES["civic"][1] = "#1f3a68"

# The palette each scene reaches for when the edition does not name one.
SCENE_PALETTE = {
    "portrait": "civic", "dais": "civic", "assembly": "civic", "crowd": "civic",
    "chamber": "civic", "secretariat": "civic", "hockey": "sea",
    "city": "dusk", "stadium": "field", "field": "field", "lab": "sea",
    "chart": "civic", "stage": "rose",
}

TONE = PALETTES["grey"]


class _Rand:
    """Small deterministic PRNG so a given seed always draws the same scene."""

    def __init__(self, seed: str):
        self._state = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16], 16)

    def next(self) -> float:
        self._state = (self._state * 6364136223846793005 + 1442695040888963407) % (2**64)
        return (self._state >> 11) / float(2**53)

    def between(self, lo: float, hi: float) -> float:
        return lo + (hi - lo) * self.next()

    def pick(self, seq):
        return seq[int(self.next() * len(seq)) % len(seq)]


def _defs(uid: str) -> str:
    """Halftone screen plus a soft vertical gradient for depth."""
    return f"""
  <defs>
    <pattern id="ht{uid}" width="4" height="4" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="0.85" fill="#000" opacity="0.17"/>
    </pattern>
    <linearGradient id="sky{uid}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{TONE[5]}"/>
      <stop offset="100%" stop-color="{TONE[6]}"/>
    </linearGradient>
    <linearGradient id="vig{uid}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#000" stop-opacity="0.20"/>
      <stop offset="45%" stop-color="#000" stop-opacity="0"/>
      <stop offset="100%" stop-color="#000" stop-opacity="0.22"/>
    </linearGradient>
  </defs>"""


def _figure(x: float, base: float, height: float, tone: str, lean: float = 0.0) -> str:
    """A standing human silhouette: head, shoulders, torso."""
    head_r = height * 0.115
    head_y = base - height + head_r
    shoulder_y = head_y + head_r * 1.7
    half = height * 0.20
    return (
        f'<g fill="{tone}">'
        f'<circle cx="{x + lean:.1f}" cy="{head_y:.1f}" r="{head_r:.1f}"/>'
        f'<path d="M{x - half:.1f} {base:.1f} '
        f'C{x - half:.1f} {shoulder_y:.1f} {x - half * 0.72 + lean:.1f} {shoulder_y - 3:.1f} {x + lean:.1f} {shoulder_y - 3:.1f} '
        f'C{x + half * 0.72 + lean:.1f} {shoulder_y - 3:.1f} {x + half:.1f} {shoulder_y:.1f} {x + half:.1f} {base:.1f} Z"/>'
        f"</g>"
    )


def _portrait(r: _Rand, uid: str) -> str:
    cx = W * r.between(0.44, 0.56)
    body = []
    body.append(f'<rect width="{W}" height="{H}" fill="url(#sky{uid})"/>')
    # Backdrop bands, like a studio curtain or an office wall.
    for i in range(4):
        y = H * (0.12 + i * 0.2)
        body.append(
            f'<rect x="0" y="{y:.1f}" width="{W}" height="{H * 0.1:.1f}" '
            f'fill="{TONE[5 - (i % 2)]}" opacity="0.55"/>'
        )
    shoulder_y = H * 0.72
    body.append(
        f'<path d="M{cx - 108:.0f} {H} C{cx - 100:.0f} {shoulder_y:.0f} '
        f'{cx - 52:.0f} {shoulder_y - 14:.0f} {cx:.0f} {shoulder_y - 16:.0f} '
        f'C{cx + 52:.0f} {shoulder_y - 14:.0f} {cx + 100:.0f} {shoulder_y:.0f} '
        f'{cx + 108:.0f} {H} Z" fill="{TONE[1]}"/>'
    )
    body.append(f'<ellipse cx="{cx:.0f}" cy="{H * 0.40:.0f}" rx="40" ry="47" fill="{TONE[3]}"/>')
    body.append(
        f'<path d="M{cx - 41:.0f} {H * 0.36:.0f} C{cx - 38:.0f} {H * 0.13:.0f} '
        f'{cx + 38:.0f} {H * 0.13:.0f} {cx + 41:.0f} {H * 0.36:.0f} '
        f'C{cx + 26:.0f} {H * 0.26:.0f} {cx - 26:.0f} {H * 0.26:.0f} '
        f'{cx - 41:.0f} {H * 0.36:.0f} Z" fill="{TONE[0]}"/>'
    )
    # Collar
    body.append(
        f'<path d="M{cx - 26:.0f} {shoulder_y - 14:.0f} L{cx:.0f} {shoulder_y + 20:.0f} '
        f'L{cx + 26:.0f} {shoulder_y - 14:.0f} Z" fill="{TONE[5]}"/>'
    )
    return "".join(body)


def _dais(r: _Rand, uid: str) -> str:
    body = [f'<rect width="{W}" height="{H}" fill="url(#sky{uid})"/>']
    # Backdrop banner
    body.append(f'<rect x="18" y="16" width="{W - 36}" height="86" fill="{TONE[2]}"/>')
    body.append(f'<rect x="26" y="24" width="{W - 52}" height="70" fill="{TONE[4]}" opacity="0.5"/>')
    for i in range(3):
        y = 40 + i * 17
        wdt = r.between(0.42, 0.78) * (W - 80)
        body.append(f'<rect x="40" y="{y:.0f}" width="{wdt:.0f}" height="6" fill="{TONE[5]}" opacity="0.8"/>')
    # Speakers behind a table
    base = H * 0.80
    n = int(r.between(3, 5.99))
    for i in range(n):
        x = W * (i + 0.5) / n + r.between(-8, 8)
        body.append(_figure(x, base, r.between(74, 88), TONE[r.pick([0, 1, 1, 2])]))
    body.append(f'<rect x="0" y="{base:.0f}" width="{W}" height="{H - base:.0f}" fill="{TONE[1]}"/>')
    body.append(f'<rect x="0" y="{base:.0f}" width="{W}" height="4" fill="{TONE[0]}"/>')
    # Microphones on the table
    for i in range(3):
        x = W * (0.25 + i * 0.25)
        body.append(f'<rect x="{x:.0f}" y="{base - 16:.0f}" width="1.6" height="16" fill="{TONE[0]}"/>')
        body.append(f'<circle cx="{x + 0.8:.0f}" cy="{base - 17:.0f}" r="3.2" fill="{TONE[0]}"/>')
    return "".join(body)


def _assembly(r: _Rand, uid: str) -> str:
    body = [f'<rect width="{W}" height="{H}" fill="url(#sky{uid})"/>']
    body.append(f'<rect x="0" y="0" width="{W}" height="{H * 0.34:.0f}" fill="{TONE[4]}" opacity="0.45"/>')
    for row in range(4):
        base = H * (0.44 + row * 0.16)
        tone = TONE[max(0, 3 - row)]
        count = 7 - row
        for i in range(count):
            x = W * (i + 0.5) / count + r.between(-6, 6)
            body.append(_figure(x, base, 44 + row * 7, tone))
        body.append(
            f'<rect x="0" y="{base:.0f}" width="{W}" height="{H * 0.055:.0f}" '
            f'fill="{TONE[min(6, 4 + row // 2)]}"/>'
        )
    return "".join(body)


def _city(r: _Rand, uid: str) -> str:
    body = [f'<rect width="{W}" height="{H}" fill="url(#sky{uid})"/>']
    body.append(f'<circle cx="{W * r.between(0.6, 0.82):.0f}" cy="{H * 0.24:.0f}" r="17" fill="{TONE[5]}"/>')
    for layer, (tone, base, lo, hi) in enumerate(
        [(TONE[4], H * 0.74, 40, 78), (TONE[2], H * 0.84, 55, 105), (TONE[0], H, 40, 88)]
    ):
        x = -10.0
        while x < W + 10:
            bw = r.between(16, 34)
            bh = r.between(lo, hi)
            body.append(f'<rect x="{x:.0f}" y="{base - bh:.0f}" width="{bw:.0f}" height="{bh:.0f}" fill="{tone}"/>')
            if layer == 2:
                for wy in range(int(base - bh) + 8, int(base) - 6, 12):
                    for wx in range(int(x) + 4, int(x + bw) - 4, 9):
                        if r.next() > 0.42:
                            body.append(f'<rect x="{wx}" y="{wy}" width="4" height="6" fill="{TONE[5]}" opacity="0.75"/>')
            x += bw + r.between(2, 7)
    return "".join(body)


def _stadium(r: _Rand, uid: str) -> str:
    """A cricket ground under lights — floodlights, stands, boundary, pitch."""
    cx = W / 2
    body = [f'<rect width="{W}" height="{H}" fill="url(#sky{uid})"/>']
    # Floodlight pylons
    for x in (30, W - 30):
        body.append(f'<rect x="{x - 1.5:.0f}" y="26" width="3" height="52" fill="{TONE[1]}"/>')
        body.append(f'<rect x="{x - 18:.0f}" y="12" width="36" height="18" rx="2" fill="{TONE[0]}"/>')
        for row in range(2):
            for col in range(5):
                body.append(
                    f'<circle cx="{x - 14 + col * 7:.0f}" cy="{17 + row * 8}" r="2.4" '
                    f'fill="{TONE[6]}" opacity="0.9"/>'
                )
    # Tiered stands, curving round the top of the ground
    body.append(f'<path d="M0 96 Q{cx:.0f} 56 {W} 96 L{W} 74 Q{cx:.0f} 36 0 74 Z" fill="{TONE[1]}"/>')
    body.append(f'<path d="M0 112 Q{cx:.0f} 74 {W} 112 L{W} 96 Q{cx:.0f} 56 0 96 Z" fill="{TONE[2]}"/>')
    for _ in range(150):
        u = r.next()
        x = u * W
        arc = 96 - 40 * (1 - ((x - cx) / cx) ** 2)
        y = arc + r.between(-20, 14)
        body.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r.between(1.1, 2.2):.1f}" '
            f'fill="{TONE[r.pick([0, 4, 5, 6])]}" opacity="0.8"/>'
        )
    # Sightscreen behind the bowler's end
    body.append(f'<rect x="{cx - 24:.0f}" y="86" width="48" height="16" fill="{TONE[6]}" opacity="0.9"/>')
    # Outfield, with mown bands
    body.append(f'<path d="M0 112 Q{cx:.0f} 74 {W} 112 L{W} {H} L0 {H} Z" fill="{TONE[3]}"/>')
    for i in range(6):
        if i % 2:
            continue
        y0 = 118 + i * 14
        body.append(
            f'<path d="M0 {y0} Q{cx:.0f} {y0 - 30:.0f} {W} {y0} L{W} {y0 + 14} '
            f'Q{cx:.0f} {y0 - 16:.0f} 0 {y0 + 14} Z" fill="{TONE[4]}" opacity="0.28"/>'
        )
    # Boundary rope
    body.append(
        f'<path d="M0 126 Q{cx:.0f} 88 {W} 126" stroke="{TONE[6]}" '
        f'stroke-width="1.8" fill="none" opacity="0.85"/>'
    )
    # The square, and the pitch running away in perspective
    body.append(f'<ellipse cx="{cx:.0f}" cy="168" rx="66" ry="26" fill="{TONE[4]}" opacity="0.35"/>')
    body.append(
        f'<path d="M{cx - 9:.0f} 138 L{cx + 9:.0f} 138 L{cx + 19:.0f} 196 '
        f'L{cx - 19:.0f} 196 Z" fill="{TONE[6]}" opacity="0.92"/>'
    )
    for y, half in ((142, 7), (190, 15)):
        body.append(
            f'<line x1="{cx - half:.0f}" y1="{y}" x2="{cx + half:.0f}" y2="{y}" '
            f'stroke="{TONE[2]}" stroke-width="1.2" opacity="0.8"/>'
        )
    # Stumps at both ends
    for y, sp, hgt in ((142, 2.2, 7), (190, 3.4, 11)):
        for k in (-1, 0, 1):
            body.append(
                f'<rect x="{cx + k * sp:.1f}" y="{y - hgt:.0f}" width="1.2" '
                f'height="{hgt}" fill="{TONE[0]}"/>'
            )
    # Batter, bowler, a fielder wide of the square
    body.append(_figure(cx - 13, 192, 26, TONE[0]))
    body.append(_figure(cx + 6, 146, 17, TONE[0]))
    body.append(_figure(W * r.between(0.14, 0.28), 176, 20, TONE[1]))
    body.append(_figure(W * r.between(0.74, 0.88), 170, 19, TONE[1]))
    return "".join(body)


def _chamber(r: _Rand, uid: str) -> str:
    """A legislature chamber — the picture a political story wants.

    Tiered benches curving away from a raised speaker's dais. Drawn rather
    than photographed, so it carries no claim to be a particular sitting.
    """
    cx = W / 2
    body = [f'<rect width="{W}" height="{H}" fill="url(#sky{uid})"/>']
    # Panelled rear wall
    body.append(f'<rect x="0" y="0" width="{W}" height="{H * 0.40:.0f}" fill="{TONE[3]}" opacity="0.55"/>')
    for x in range(0, W, 15):
        body.append(f'<rect x="{x}" y="0" width="7" height="{H * 0.40:.0f}" fill="{TONE[2]}" opacity="0.30"/>')
    # Speaker's canopy, chair and dais
    body.append(f'<path d="M{cx - 38:.0f} 40 L{cx + 38:.0f} 40 L{cx + 27:.0f} 10 L{cx - 27:.0f} 10 Z" fill="{TONE[1]}"/>')
    body.append(f'<rect x="{cx - 15:.0f}" y="40" width="30" height="26" rx="3" fill="{TONE[0]}"/>')
    body.append(f'<circle cx="{cx:.0f}" cy="26" r="7" fill="{TONE[5]}" opacity="0.85"/>')
    body.append(f'<rect x="{cx - 30:.0f}" y="66" width="60" height="9" fill="{TONE[1]}"/>')
    # Four tiers of benches, each a shallow arc, members seated behind
    for row in range(4):
        base = H * (0.50 + row * 0.125)
        seats = 6 - row
        tone = TONE[max(0, 2 - row // 2)]
        for i in range(seats):
            x = W * (i + 0.5) / seats + r.between(-5, 5)
            if abs(x - cx) < 22 and row == 0:
                continue
            body.append(_figure(x, base + 3, 30 + row * 5, tone))
        dip = 7 + row * 2
        body.append(
            f'<path d="M0 {base:.0f} Q{cx:.0f} {base + dip:.0f} {W} {base:.0f} '
            f'L{W} {base + 15 + row * 3:.0f} L0 {base + 15 + row * 3:.0f} Z" '
            f'fill="{TONE[min(6, 4 + row // 2)]}"/>'
        )
        body.append(
            f'<path d="M0 {base:.0f} Q{cx:.0f} {base + dip:.0f} {W} {base:.0f}" '
            f'stroke="{TONE[1]}" stroke-width="1.2" fill="none" opacity="0.55"/>'
        )
        # desk microphones
        for i in range(seats):
            x = W * (i + 0.5) / seats
            if abs(x - cx) < 22 and row == 0:
                continue
            my = base + dip * (1 - ((x - cx) / cx) ** 2) + 4
            body.append(f'<rect x="{x:.0f}" y="{my - 9:.0f}" width="1.2" height="9" fill="{TONE[0]}" opacity="0.8"/>')
    return "".join(body)


def _secretariat(r: _Rand, uid: str) -> str:
    """A government building front — for scheme and administration stories."""
    body = [f'<rect width="{W}" height="{H}" fill="url(#sky{uid})"/>']
    cx = W / 2
    ground = H * 0.86
    # Dome and flagstaff over a central bay
    body.append(f'<rect x="{cx - 1:.0f}" y="14" width="2" height="20" fill="{TONE[1]}"/>')
    body.append(f'<path d="M{cx - 2:.0f} 15 L{cx + 20:.0f} 21 L{cx - 2:.0f} 27 Z" fill="{TONE[2]}"/>')
    body.append(f'<path d="M{cx - 26:.0f} 62 Q{cx:.0f} 24 {cx + 26:.0f} 62 Z" fill="{TONE[1]}"/>')
    body.append(f'<rect x="{cx - 30:.0f}" y="62" width="60" height="6" fill="{TONE[0]}"/>')
    # Facade with an arcade of arches on two storeys
    body.append(f'<rect x="14" y="68" width="{W - 28}" height="{ground - 68:.0f}" fill="{TONE[2]}"/>')
    body.append(f'<rect x="14" y="68" width="{W - 28}" height="7" fill="{TONE[0]}"/>')
    for storey, (top, hgt) in enumerate([(84, 34), (128, 34)]):
        for i in range(9):
            x = 22 + i * ((W - 44) / 9)
            aw = (W - 44) / 9 - 8
            body.append(
                f'<path d="M{x:.0f} {top + hgt:.0f} L{x:.0f} {top + aw / 2:.0f} '
                f'Q{x + aw / 2:.0f} {top - 2:.0f} {x + aw:.0f} {top + aw / 2:.0f} '
                f'L{x + aw:.0f} {top + hgt:.0f} Z" fill="{TONE[max(0, 5 - storey * 4)]}" opacity="0.9"/>'
            )
        body.append(f'<rect x="14" y="{top + hgt + 2:.0f}" width="{W - 28}" height="4" fill="{TONE[1]}"/>')
    body.append(f'<rect x="0" y="{ground:.0f}" width="{W}" height="{H - ground:.0f}" fill="{TONE[4]}"/>')
    for i in range(4):
        body.append(_figure(W * r.between(0.12, 0.88), H * r.between(0.94, 0.99), r.between(20, 28), TONE[0]))
    return "".join(body)


def _hockey(r: _Rand, uid: str) -> str:
    """A floodlit hockey pitch — goal, striking circle, players.

    Kept separate from the cricket ground on purpose: a hockey report
    illustrated with stumps and a pitch strip is simply the wrong picture.
    """
    cx = W / 2
    body = [f'<rect width="{W}" height="{H}" fill="url(#sky{uid})"/>']
    for x in (32, W - 32):
        body.append(f'<rect x="{x - 1.5:.0f}" y="24" width="3" height="46" fill="{TONE[1]}"/>')
        body.append(f'<rect x="{x - 16:.0f}" y="12" width="32" height="15" rx="2" fill="{TONE[0]}"/>')
        for col in range(4):
            body.append(f'<circle cx="{x - 11 + col * 7:.0f}" cy="19" r="2.2" fill="{TONE[6]}" opacity="0.9"/>')
    # Stand and crowd behind the goal
    body.append(f'<path d="M0 100 Q{cx:.0f} 66 {W} 100 L{W} 72 Q{cx:.0f} 40 0 72 Z" fill="{TONE[2]}"/>')
    for _ in range(110):
        x = r.next() * W
        arc = 100 - 34 * (1 - ((x - cx) / cx) ** 2)
        body.append(
            f'<circle cx="{x:.0f}" cy="{arc + r.between(-20, 8):.0f}" r="{r.between(1.1, 2.1):.1f}" '
            f'fill="{TONE[r.pick([0, 4, 5, 6])]}" opacity="0.8"/>'
        )
    # Blue synthetic turf
    body.append(f'<path d="M0 100 Q{cx:.0f} 66 {W} 100 L{W} {H} L0 {H} Z" fill="{TONE[3]}"/>')
    body.append(f'<path d="M0 118 Q{cx:.0f} 86 {W} 118" stroke="{TONE[6]}" stroke-width="1.4" fill="none" opacity="0.7"/>')
    # Goal and the striking circle in front of it
    body.append(f'<rect x="{cx - 26:.0f}" y="96" width="52" height="22" fill="{TONE[6]}" opacity="0.22"/>')
    body.append(f'<rect x="{cx - 26:.0f}" y="96" width="52" height="22" stroke="{TONE[6]}" stroke-width="1.6" fill="none"/>')
    body.append(
        f'<path d="M{cx - 78:.0f} 152 Q{cx:.0f} 104 {cx + 78:.0f} 152" '
        f'stroke="{TONE[6]}" stroke-width="1.5" fill="none" opacity="0.85"/>'
    )
    body.append(f'<circle cx="{cx:.0f}" cy="150" r="2.4" fill="{TONE[6]}"/>')
    # Players, sticks lowered toward the ball
    for x, base, hgt, tone in (
        (cx - 34, 168, 34, TONE[0]), (cx + 22, 160, 30, TONE[1]),
        (cx + 52, 182, 33, TONE[0]), (cx - 66, 178, 31, TONE[1]),
        (cx - 6, 132, 22, TONE[0]),
    ):
        body.append(_figure(x, base, hgt, tone))
        body.append(
            f'<path d="M{x + 5:.0f} {base - hgt * 0.34:.0f} L{x + 13:.0f} {base - 3:.0f} '
            f'Q{x + 16:.0f} {base:.0f} {x + 11:.0f} {base:.0f}" stroke="{TONE[6]}" '
            f'stroke-width="1.6" fill="none" opacity="0.9"/>'
        )
    return "".join(body)


def _field(r: _Rand, uid: str) -> str:
    body = [f'<rect width="{W}" height="{H}" fill="url(#sky{uid})"/>']
    body.append(f'<path d="M0 84 L52 54 L96 82 L150 44 L206 80 L260 58 L{W} 86 L{W} 110 L0 110 Z" fill="{TONE[4]}"/>')
    body.append(f'<rect x="0" y="104" width="{W}" height="{H - 104}" fill="{TONE[5]}"/>')
    for i in range(9):
        y = 112 + i * 10
        body.append(f'<path d="M0 {y} Q{W / 2:.0f} {y - 7} {W} {y}" stroke="{TONE[3]}" stroke-width="{1 + i * 0.35:.1f}" fill="none" opacity="0.55"/>')
    for x, h in [(34, 62), (268, 74), (232, 50)]:
        top = 108 - h
        body.append(f'<rect x="{x:.0f}" y="{top:.0f}" width="3" height="{h:.0f}" fill="{TONE[1]}"/>')
        for a in (-52, -22, 0, 22, 52):
            body.append(
                f'<path d="M{x + 1.5:.0f} {top:.0f} q{a * 0.45:.0f} {-9 - abs(a) * 0.06:.0f} '
                f'{a:.0f} {abs(a) * 0.26 + 4:.0f}" stroke="{TONE[1]}" stroke-width="3" fill="none" stroke-linecap="round"/>'
            )
    body.append(_figure(W * 0.55, H * 0.94, 52, TONE[0]))
    return "".join(body)


def _lab(r: _Rand, uid: str) -> str:
    body = [f'<rect width="{W}" height="{H}" fill="url(#sky{uid})"/>']
    body.append(f'<rect x="0" y="0" width="{W}" height="72" fill="{TONE[4]}" opacity="0.4"/>')
    for i in range(3):
        y = 16 + i * 20
        body.append(f'<rect x="16" y="{y}" width="{W - 32}" height="2.4" fill="{TONE[3]}"/>')
        for j in range(9):
            bx = 24 + j * 30 + r.between(-4, 4)
            bh = r.between(8, 15)
            body.append(f'<rect x="{bx:.0f}" y="{y - bh:.0f}" width="8" height="{bh:.0f}" fill="{TONE[r.pick([2, 3, 5])]}"/>')
    body.append(f'<rect x="0" y="126" width="{W}" height="{H - 126}" fill="{TONE[2]}"/>')
    body.append(f'<rect x="0" y="126" width="{W}" height="3" fill="{TONE[0]}"/>')
    for i, (x, hh) in enumerate([(64, 34), (108, 26), (208, 30)]):
        body.append(f'<path d="M{x - 11} 126 L{x - 4} {126 - hh + 8} L{x - 4} {126 - hh} L{x + 4} {126 - hh} L{x + 4} {126 - hh + 8} L{x + 11} 126 Z" fill="{TONE[5]}"/>')
        body.append(f'<path d="M{x - 8} 126 L{x - 3.4} {126 - hh * 0.5} L{x + 3.4} {126 - hh * 0.5} L{x + 8} 126 Z" fill="{TONE[1]}"/>')
    body.append(_figure(W * 0.76, 126, 74, TONE[0]))
    return "".join(body)


def _crowd(r: _Rand, uid: str) -> str:
    body = [f'<rect width="{W}" height="{H}" fill="url(#sky{uid})"/>']
    body.append(f'<rect x="0" y="0" width="{W}" height="{H * 0.4:.0f}" fill="{TONE[5]}"/>')
    for row in range(5):
        base = H * (0.40 + row * 0.15)
        tone = TONE[max(0, 4 - row)]
        count = 12 - row
        for i in range(count):
            x = W * (i + 0.5) / count + r.between(-9, 9)
            body.append(_figure(x, base, 34 + row * 9, tone))
    return "".join(body)


def _chart(r: _Rand, uid: str) -> str:
    body = [f'<rect width="{W}" height="{H}" fill="{TONE[6]}"/>']
    body.append(f'<rect x="14" y="12" width="{W - 28}" height="{H - 24}" fill="{TONE[5]}" stroke="{TONE[2]}" stroke-width="1.4"/>')
    base = H - 34
    for i in range(4):
        y = base - i * 26
        body.append(f'<line x1="30" y1="{y:.0f}" x2="{W - 26}" y2="{y:.0f}" stroke="{TONE[4]}" stroke-width="0.8"/>')
    n = 7
    prev = None
    for i in range(n):
        x = 34 + i * ((W - 74) / (n - 1))
        h = r.between(24, 96)
        body.append(f'<rect x="{x - 9:.0f}" y="{base - h:.0f}" width="18" height="{h:.0f}" fill="{TONE[r.pick([1, 2, 3])]}"/>')
        pt = (x, base - h - 12)
        if prev:
            body.append(f'<line x1="{prev[0]:.0f}" y1="{prev[1]:.0f}" x2="{pt[0]:.0f}" y2="{pt[1]:.0f}" stroke="{TONE[0]}" stroke-width="1.8"/>')
        body.append(f'<circle cx="{pt[0]:.0f}" cy="{pt[1]:.0f}" r="2.4" fill="{TONE[0]}"/>')
        prev = pt
    body.append(f'<line x1="30" y1="{base:.0f}" x2="{W - 26}" y2="{base:.0f}" stroke="{TONE[0]}" stroke-width="1.6"/>')
    return "".join(body)


def _stage(r: _Rand, uid: str) -> str:
    body = [f'<rect width="{W}" height="{H}" fill="{TONE[0]}"/>']
    # Backdrop wash and stage lighting
    body.append(f'<rect x="0" y="0" width="{W}" height="{H * 0.62:.0f}" fill="{TONE[1]}"/>')
    for i in range(4):
        x = W * (0.16 + i * 0.23)
        body.append(
            f'<path d="M{x:.0f} 0 L{x - 26:.0f} {H * 0.66:.0f} L{x + 26:.0f} {H * 0.66:.0f} Z" '
            f'fill="{TONE[4]}" opacity="0.22"/>'
        )
    body.append(f'<rect x="0" y="0" width="{W}" height="12" fill="{TONE[0]}"/>')
    for i in range(6):
        x = 24 + i * 50
        body.append(f'<rect x="{x:.0f}" y="6" width="12" height="9" rx="1.6" fill="{TONE[3]}"/>')
    # Performers with drums
    base = H * 0.80
    for i in range(5):
        x = W * (i + 0.5) / 5 + r.between(-7, 7)
        body.append(_figure(x, base, r.between(62, 76), TONE[r.pick([5, 5, 6])]))
        dy = base - r.between(16, 22)
        body.append(f'<ellipse cx="{x:.0f}" cy="{dy:.0f}" rx="13" ry="9" fill="{TONE[4]}"/>')
        body.append(f'<ellipse cx="{x:.0f}" cy="{dy - 2:.0f}" rx="13" ry="9" fill="{TONE[6]}"/>')
    body.append(f'<rect x="0" y="{base:.0f}" width="{W}" height="{H - base:.0f}" fill="{TONE[0]}"/>')
    body.append(f'<rect x="0" y="{base:.0f}" width="{W}" height="3" fill="{TONE[3]}"/>')
    return "".join(body)


SCENES = {
    "portrait": _portrait,
    "chamber": _chamber,
    "hockey": _hockey,
    "secretariat": _secretariat,
    "dais": _dais,
    "assembly": _assembly,
    "city": _city,
    "stadium": _stadium,
    "field": _field,
    "lab": _lab,
    "crowd": _crowd,
    "chart": _chart,
    "stage": _stage,
}


def render(scene: str, seed: str = "", palette: str | None = None) -> str:
    """Return an inline SVG for the named scene.

    ``palette`` picks the colour ramp; omit it and the scene uses the one that
    suits it. Pass ``"grey"`` for a print edition.
    """
    global TONE
    if scene not in SCENES:
        raise KeyError(
            f"unknown picture scene {scene!r}; choose one of {', '.join(sorted(SCENES))}"
        )
    name = palette or SCENE_PALETTE.get(scene, "grey")
    if name not in PALETTES:
        raise KeyError(
            f"unknown picture palette {name!r}; choose one of {', '.join(sorted(PALETTES))}"
        )
    uid = hashlib.sha1(f"{scene}:{seed}:{name}".encode()).hexdigest()[:6]
    rand = _Rand(f"{scene}:{seed}")
    previous, TONE = TONE, PALETTES[name]
    try:
        inner = SCENES[scene](rand, uid)
    finally:
        TONE = previous
    previous, TONE = TONE, PALETTES[name]
    try:
        defs = _defs(uid)
    finally:
        TONE = previous
    # The halftone screen is what a photograph looks like on newsprint, so it
    # belongs on the grey ramp and nowhere else. It is also expensive: the
    # printer expands the pattern into one circle per cell, thousands per
    # picture, and that is most of the weight of a finished PDF. A colour
    # edition read on a phone wants neither the look nor the megabytes.
    screen = f'<rect width="{W}" height="{H}" fill="url(#ht{uid})"/>' if name == "grey" else ""
    return (
        f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" '
        f'xmlns="http://www.w3.org/2000/svg" role="img">'
        f"{defs}{inner}"
        f'<rect width="{W}" height="{H}" fill="url(#vig{uid})"/>'
        f"{screen}"
        f"</svg>"
    )
