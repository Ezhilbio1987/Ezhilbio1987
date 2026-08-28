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
    body = [f'<rect width="{W}" height="{H}" fill="url(#sky{uid})"/>']
    for x in (36, W - 36):
        body.append(f'<rect x="{x - 1.5:.0f}" y="14" width="3" height="62" fill="{TONE[1]}"/>')
        body.append(f'<rect x="{x - 17:.0f}" y="8" width="34" height="16" rx="2" fill="{TONE[0]}"/>')
    body.append(f'<path d="M0 92 Q{W / 2:.0f} 58 {W} 92 L{W} 128 Q{W / 2:.0f} 96 0 128 Z" fill="{TONE[2]}"/>')
    for i in range(46):
        x = r.between(4, W - 4)
        y = r.between(70, 122)
        body.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r.between(1.4, 2.8):.1f}" fill="{TONE[r.pick([0, 4, 5])]}" opacity="0.85"/>')
    body.append(f'<path d="M0 128 Q{W / 2:.0f} 96 {W} 128 L{W} {H} L0 {H} Z" fill="{TONE[3]}"/>')
    body.append(f'<path d="M0 150 Q{W / 2:.0f} 128 {W} 150" stroke="{TONE[6]}" stroke-width="1.6" fill="none" opacity="0.8"/>')
    body.append(f'<circle cx="{W / 2:.0f}" cy="172" r="22" stroke="{TONE[6]}" stroke-width="1.6" fill="none" opacity="0.8"/>')
    for i in range(3):
        body.append(_figure(W * r.between(0.2, 0.8), H * r.between(0.82, 0.96), r.between(28, 40), TONE[0]))
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
