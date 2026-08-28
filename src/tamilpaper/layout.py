"""Grid make-up.

Each page is a fixed column x row grid. A block declares how many columns and
rows it occupies; this module assigns it an explicit position with a first-fit
scan, so placement is deterministic rather than left to the browser's auto
flow. Knowing the exact column also tells us which blocks need a hairline in
the gutter to their left.
"""

from dataclasses import dataclass


class LayoutError(ValueError):
    pass


@dataclass
class Placement:
    col: int   # 1-based starting column
    row: int   # 1-based starting row


def place_blocks(blocks: list[dict], cols: int, rows: int, page_label: str) -> None:
    """Assign grid_col / grid_row / ruled to every block, in place.

    Blocks are placed in the order given. A block may pin itself with an
    explicit ``at`` of ``[col, row]``; everything else takes the first free
    slot scanning left to right, top to bottom.
    """
    occupied = [[False] * cols for _ in range(rows)]

    def fits(c0: int, r0: int, w: int, h: int) -> bool:
        if c0 + w > cols or r0 + h > rows:
            return False
        return all(
            not occupied[r][c]
            for r in range(r0, r0 + h)
            for c in range(c0, c0 + w)
        )

    def occupy(c0: int, r0: int, w: int, h: int) -> None:
        for r in range(r0, r0 + h):
            for c in range(c0, c0 + w):
                occupied[r][c] = True

    for index, block in enumerate(blocks):
        w = int(block.get("col", 1))
        h = int(block.get("row", 1))
        label = block.get("id") or f"block #{index + 1}"

        if w < 1 or h < 1:
            raise LayoutError(f"{page_label}: {label} has a non-positive span ({w}x{h})")
        if w > cols or h > rows:
            raise LayoutError(
                f"{page_label}: {label} spans {w}x{h}, larger than the "
                f"{cols}x{rows} page grid"
            )

        spot: Placement | None = None
        if "at" in block:
            c0, r0 = int(block["at"][0]) - 1, int(block["at"][1]) - 1
            if not fits(c0, r0, w, h):
                raise LayoutError(
                    f"{page_label}: {label} is pinned at column {c0 + 1}, row "
                    f"{r0 + 1} but that area is off-grid or already taken"
                )
            spot = Placement(c0, r0)
        else:
            for r0 in range(rows):
                for c0 in range(cols):
                    if fits(c0, r0, w, h):
                        spot = Placement(c0, r0)
                        break
                if spot:
                    break

        if spot is None:
            raise LayoutError(
                f"{page_label}: no room left for {label} ({w}x{h}). Give the "
                f"page more rows, or shrink the blocks above it."
            )

        occupy(spot.col, spot.row, w, h)
        block["grid_col"] = spot.col + 1
        block["grid_row"] = spot.row + 1
        block["col"] = w
        block["row"] = h
        # A hairline goes in the gutter to the left of any block that does not
        # start at the page edge.
        block["ruled"] = spot.col > 0


def coverage(blocks: list[dict], cols: int, rows: int) -> float:
    """Fraction of the page grid the blocks fill. Useful for warning about
    white holes left in the make-up."""
    used = sum(int(b["col"]) * int(b["row"]) for b in blocks)
    return used / float(cols * rows)
