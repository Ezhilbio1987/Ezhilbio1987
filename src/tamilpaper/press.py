"""Press presets — physical page sizes and the type they are set at.

Sizes are the real trim sizes used by the presses they are named for. The
default, ``indian-broadsheet``, is the 350 x 520 mm sheet most Tamil dailies
are printed on.
"""

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Press:
    key: str
    label: str
    width: str
    height: str
    margin_top: str
    margin_side: str
    margin_bottom: str
    gutter: str
    body_size: str
    cols: int
    rows: int

    def as_dict(self) -> dict:
        return asdict(self)


PRESETS: dict[str, Press] = {
    "indian-broadsheet": Press(
        key="indian-broadsheet",
        label="இந்திய பிராட்ஷீட் · 350 × 520 mm",
        width="350mm", height="520mm",
        margin_top="8mm", margin_side="9mm", margin_bottom="7mm",
        gutter="4.6mm", body_size="9.4pt", cols=6, rows=12,
    ),
    "broadsheet": Press(
        key="broadsheet",
        label="US broadsheet · 12 × 22 in",
        width="305mm", height="559mm",
        margin_top="9mm", margin_side="9mm", margin_bottom="8mm",
        gutter="4.4mm", body_size="9.2pt", cols=6, rows=13,
    ),
    "berliner": Press(
        key="berliner",
        label="Berliner · 315 × 470 mm",
        width="315mm", height="470mm",
        margin_top="8mm", margin_side="9mm", margin_bottom="7mm",
        gutter="4.4mm", body_size="9.2pt", cols=5, rows=11,
    ),
    "tabloid": Press(
        key="tabloid",
        label="Tabloid · 11 × 17 in",
        width="279mm", height="432mm",
        margin_top="8mm", margin_side="8mm", margin_bottom="7mm",
        gutter="4.2mm", body_size="9.0pt", cols=5, rows=11,
    ),
    "a3": Press(
        key="a3",
        label="A3 · 297 × 420 mm",
        width="297mm", height="420mm",
        margin_top="8mm", margin_side="8mm", margin_bottom="7mm",
        gutter="4.2mm", body_size="8.9pt", cols=5, rows=10,
    ),
    "a4": Press(
        key="a4",
        label="A4 · 210 × 297 mm",
        width="210mm", height="297mm",
        margin_top="7mm", margin_side="7mm", margin_bottom="6mm",
        gutter="3.6mm", body_size="8.2pt", cols=4, rows=9,
    ),
}

DEFAULT = "indian-broadsheet"


def get(key: str | None) -> Press:
    if not key:
        return PRESETS[DEFAULT]
    if key not in PRESETS:
        raise ValueError(
            f"unknown press preset {key!r}; choose one of {', '.join(sorted(PRESETS))}"
        )
    return PRESETS[key]
