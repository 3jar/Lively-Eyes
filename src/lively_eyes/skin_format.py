"""Skin eye-slot layout, compatible with skins made for Fresh Moves.

This module is a description of a *skin format*: which pixels in the unused
areas of a 64x64 skin hold eye parts, and where on the face each one shows.
Skins draw eyes in exactly one slot; the others stay transparent, so every
slot can be rendered at once and only the painted one is visible.

Coordinates:
  face rect  (c0, c1, r0, r1)  front-face columns/rows, 0..8, column 0 is the
                               texture's left edge (the character's right).
  uv rect    (u0, v0, u1, v1)  skin texture pixels.
  mirror     the uv rect is flipped horizontally on the face.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Layer:
    face: tuple
    uv: tuple
    mirror: bool = False


@dataclass(frozen=True)
class Eye:
    rect: tuple
    white: Layer | None = None
    pupil: Layer | None = None
    lid: Layer | None = None


@dataclass(frozen=True)
class Slot:
    key: str
    right: Eye
    left: Eye


def _one_row(key, k):
    r0, r1, v = 7 - k, 8 - k, 8 - 2 * k
    return Slot(
        key,
        right=Eye(
            (1, 3, r0, r1),
            white=Layer((1, 2, r0, r1), (4, v + 1, 5, v + 2)),
            pupil=Layer((2, 3, r0, r1), (5, v + 1, 6, v + 2)),
            lid=Layer((1, 3, r0, r1), (4, v, 6, v + 1), mirror=True),
        ),
        left=Eye(
            (5, 7, r0, r1),
            pupil=Layer((5, 6, r0, r1), (6, v + 1, 7, v + 2)),
            white=Layer((6, 7, r0, r1), (7, v + 1, 8, v + 2)),
            lid=Layer((5, 7, r0, r1), (6, v, 8, v + 1), mirror=True),
        ),
    )


def _two_row(key, r0, u, v):
    r1 = r0 + 2
    return Slot(
        key,
        right=Eye(
            (1, 3, r0, r1),
            white=Layer((1, 2, r0, r1), (u, v + 1, u + 1, v + 3)),
            pupil=Layer((2, 3, r0, r1), (u + 1, v + 1, u + 2, v + 3)),
            lid=Layer((1, 3, r0, r1), (u, v, u + 2, v + 1), mirror=True),
        ),
        left=Eye(
            (5, 7, r0, r1),
            pupil=Layer((5, 6, r0, r1), (u + 2, v + 1, u + 3, v + 3)),
            white=Layer((6, 7, r0, r1), (u + 3, v + 1, u + 4, v + 3)),
            lid=Layer((5, 7, r0, r1), (u + 2, v, u + 4, v + 1), mirror=True),
        ),
    )


def _three_wide(key, r0, v):
    r1 = r0 + 1
    return Slot(
        key,
        right=Eye(
            (0, 3, r0, r1),
            white=Layer((0, 3, r0, r1), (32, v + 1, 35, v + 2), mirror=True),
            pupil=Layer((1, 2, r0, r1), (35, v + 1, 36, v + 2)),
            lid=Layer((-0.025, 3, r0, r1), (32, v, 35, v + 1), mirror=True),
        ),
        left=Eye(
            (5, 8, r0, r1),
            white=Layer((5, 8, r0, r1), (37, v + 1, 40, v + 2), mirror=True),
            pupil=Layer((6, 7, r0, r1), (36, v + 1, 37, v + 2)),
            lid=Layer((5, 8.025, r0, r1), (37, v, 40, v + 1), mirror=True),
        ),
    )


def _pupil_only(key, k):
    r0, r1, v = 7 - k, 8 - k, 9 - 2 * k
    return Slot(
        key,
        right=Eye((1, 3, r0, r1), pupil=Layer((2, 3, r0, r1), (2, v, 3, v + 1))),
        left=Eye((5, 7, r0, r1), pupil=Layer((5, 6, r0, r1), (3, v, 4, v + 1))),
    )


def _lid_only(key, right_face, left_face, v):
    return Slot(
        key,
        right=Eye(right_face, lid=Layer(right_face, (0, v, 1, v + 1), mirror=True)),
        left=Eye(left_face, lid=Layer(left_face, (1, v, 2, v + 1), mirror=True)),
    )


SLOTS = [
    # 1-row eyes, white+pupil row under a lid row, four heights
    *(_one_row(f"a{k}", k) for k in range(1, 5)),
    # 2-row eyes
    _two_row("b1", 5, 24, 5),
    _two_row("b2", 4, 24, 2),
    _two_row("b3", 3, 28, 5),
    _two_row("b4", 2, 28, 2),
    # 3-row eyes: pupil covers the top two rows and can drop one
    Slot(
        "c",
        right=Eye(
            (1, 3, 4, 7),
            white=Layer((1, 2, 4, 7), (32, 5, 33, 8)),
            pupil=Layer((2, 3, 4, 6), (33, 5, 34, 7)),
            lid=Layer((1, 3, 4, 7), (32, 4, 34, 5), mirror=True),
        ),
        left=Eye(
            (5, 7, 4, 7),
            pupil=Layer((5, 6, 4, 6), (34, 5, 35, 7)),
            white=Layer((6, 7, 4, 7), (35, 5, 36, 8)),
            lid=Layer((5, 7, 4, 7), (34, 4, 36, 5), mirror=True),
        ),
    ),
    # 3-wide eyes with a centered pupil
    _three_wide("d1", 5, 2),
    _three_wide("d2", 4, 0),
    # pupil-only overlays
    *(_pupil_only(f"e{k}", k) for k in range(1, 5)),
    # eyes set one column outward
    Slot(
        "f",
        right=Eye(
            (0, 2.025, 5, 6),
            white=Layer((0, 1.025, 5, 6), (36, 7, 37, 8)),
            pupil=Layer((1, 2.025, 5, 6), (37, 7, 38, 8)),
            lid=Layer((0, 2.025, 5, 6), (36, 6, 38, 7), mirror=True),
        ),
        left=Eye(
            (5.975, 8, 5, 6),
            pupil=Layer((5.975, 7, 5, 6), (38, 7, 39, 8)),
            white=Layer((6.975, 8, 5, 6), (39, 7, 40, 8)),
            lid=Layer((5.975, 8, 5, 6), (38, 6, 40, 7), mirror=True),
        ),
    ),
    # lid-only (blink/squint) overlays for small eyes
    _lid_only("g1", (1, 2.025, 4, 5), (5.975, 7, 4, 5), 7),
    _lid_only("g2", (1, 2.025, 3, 4), (5.975, 7, 3, 4), 6),
    _lid_only("g3", (2, 3.025, 4, 5), (4.975, 6, 4, 5), 5),
    _lid_only("g4", (2, 3.025, 3, 4), (4.975, 6, 3, 4), 4),
    _lid_only("g5", (2, 3.025, 4, 6), (4.975, 6, 4, 6), 3),
    _lid_only("g6", (2, 3.025, 3, 5), (4.975, 6, 3, 5), 2),
    _lid_only("g7", (2, 3.025, 3, 6), (4.975, 6, 3, 6), 1),
    _lid_only("g8", (2, 3.025, 2, 5), (4.975, 6, 2, 5), 0),
]

# Eyelashes: a top lash over each eye and a side lash at each outer corner.
LASHES = {
    "top_r": Layer((1, 3, 4, 5), (56, 0, 58, 1), mirror=True),
    "top_l": Layer((5, 7, 4, 5), (58, 0, 60, 1), mirror=True),
    "side_r": Layer((0, 1, 5, 7), (56, 1, 57, 3)),
    "side_l": Layer((7, 8, 5, 7), (59, 1, 60, 3)),
}


@dataclass(frozen=True)
class Brow:
    """A brow and the patch that hides the face's own brow when ours moves."""
    brow: Layer
    cover: Layer | None = None


@dataclass(frozen=True)
class BrowSlot:
    key: str
    brows: tuple  # ((side, Brow), ...); side "r", "l" or "c" for a unibrow


def _brow_row(key, row, u, v, cover_v=None):
    def side(cols, du):
        face = (*cols, row, row + 1)
        cover = Layer(face, (u + du, cover_v, u + du + 2, cover_v + 1), mirror=True) if cover_v is not None else None
        return Brow(Layer(face, (u + du, v, u + du + 2, v + 1)), cover)
    return BrowSlot(key, (("r", side((1, 3), 0)), ("l", side((5, 7), 2))))


BROW_SLOTS = [
    # brows over the eye rows, with cover patches: x 60-63
    _brow_row("w1", 5, 60, 7, 6),
    _brow_row("w2", 4, 60, 5, 4),
    _brow_row("w3", 3, 60, 3, 2),
    _brow_row("w4", 2, 60, 1, 0),
    # brows without cover patches: x 56-59, below the eyelash pixels
    _brow_row("w5", 5, 56, 7),
    _brow_row("w6", 4, 56, 6),
    _brow_row("w7", 3, 56, 5),
    _brow_row("w8", 2, 56, 4),
    # brows set one column outward
    BrowSlot("w9", (
        ("r", Brow(Layer((0, 2, 3, 4), (36, 5, 38, 6)), Layer((0, 2, 3, 4), (36, 4, 38, 5), mirror=True))),
        ("l", Brow(Layer((6, 8, 3, 4), (38, 5, 40, 6)), Layer((6, 8, 3, 4), (38, 4, 40, 5), mirror=True))),
    )),
    # unibrow across the face
    BrowSlot("wu", (
        ("c", Brow(Layer((0.99, 7.01, 3, 4), (24, 1, 29, 2)), Layer((0.99, 7.01, 3, 4), (24, 0, 29, 1), mirror=True))),
    )),
]
