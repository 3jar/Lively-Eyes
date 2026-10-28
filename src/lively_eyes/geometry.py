"""Face parts built from the skin format, plus their per-part animations.

Frame: plain Minecraft model space relative to the head pivot (neck), with
no invertAxis anywhere: face column c spans x [c-4, c-3], face row r spans
y [r-8, r-7] (y grows downward), and the front face sits at z = -4 (smaller
z is in front). invertAxis is avoided because the jpm is shared by
player.jem and player_slim.jem and its parts came out un-inverted in game.

Anything that moves is a zero-translate "mover" under a static anchor, so
animations only ever write offsets and scales, never absolute positions.
"""

from .config import BROW_RZ_SIGN, BROWS, BROWS_OVER_HAIR, TX_SIGN, TY_SIGN
from .expr import expand, num
from .skin_format import BROW_SLOTS, LASHES, SLOTS, Layer

DEPTH = 0.01
Z_COVER = -0.005
Z_SCLERA = -0.010
Z_PUPIL = -0.020
Z_LASH = -0.025
Z_LID = -0.030
Z_BROW = -0.035
# In front of the hair: the vanilla hat layer is at z -4.5; Skin Layers 3D puts
# its voxels inside the head and scales them by its head voxel size (default
# 1.18) around the head center, so its bangs reach about z -4.72.
Z_BROW_OVER_HAIR = -0.85


def _uv(layer):
    u0, v0, u1, v1 = layer.uv
    return [u1, v0, u0, v1] if layer.mirror else [u0, v0, u1, v1]


def _center(rect):
    c0, c1, r0, r1 = rect
    return (c0 + c1) / 2 - 4, (r0 + r1) / 2 - 8


def _box(layer, pivot, z):
    """Box for a face layer, relative to a pivot in model x/y."""
    c0, c1, r0, r1 = layer.face
    x0, y0 = c0 - 4 - pivot[0], r0 - 8 - pivot[1]
    return {"coordinates": [num(x0), num(y0), z, num(c1 - c0), num(r1 - r0), DEPTH], "uvNorth": _uv(layer)}


def _part(part_id, translate=(0, 0, 0), boxes=(), submodels=()):
    part = {"id": expand(part_id), "translate": [num(v) for v in translate]}
    if boxes:
        part["boxes"] = list(boxes)
    if submodels:
        part["submodels"] = list(submodels)
    return part


def _travel(offset, lo, hi, k, cap):
    """Pupil offset clamped to the eye, but past an edge it keeps going a little.

    With 2-px eyes one pupil always sits at an edge, so a hard clamp would move
    only one eye; the overshoot makes both eyes follow the gaze. Vertically most
    eyes have no room at all, so up/down is overshoot only.
    """
    inside = f"clamp({offset}, {lo}, {hi})"
    return f"{inside} + clamp({k} * ({offset} - {inside}), -{cap}, {cap})"


def _eye(key, side, eye):
    """One eye: anchor (widen scale) > sclera box, pupil anchor > mover, lid."""
    tag = f"{key}{side}"
    cx, cy = _center(eye.rect)
    children, anims = [], [(f"@e_{tag}.sy", "$eye_sy")]
    # the white column is stretched across the whole eye so the pupil can leave its spot
    sclera = Layer(eye.rect, eye.white.uv, eye.white.mirror) if eye.white else None
    boxes = [_box(sclera, (cx, cy), Z_SCLERA)] if sclera else []

    if eye.pupil:
        pcx, pcy = _center(eye.pupil.face)
        mover = _part(f"@pm_{tag}", boxes=[_box(eye.pupil, (pcx, pcy), Z_PUPIL)])
        children.append(_part(f"@pa_{tag}", (pcx - cx, pcy - cy, 0), submodels=[mover]))
        ec0, ec1, er0, er1 = eye.rect
        pc0, pc1, pr0, pr1 = eye.pupil.face
        col_lo, col_hi = num(ec0 - pc0), num(ec1 - pc1)
        row_lo, row_hi = num(er0 - pr0), num(er1 - pr1)
        anims.append((f"@pm_{tag}.tx", f"{TX_SIGN} * ({_travel('$oc', col_lo, col_hi, '#pupil_over_k', '#pupil_over_max')})"))
        anims.append((f"@pm_{tag}.ty", f"{TY_SIGN} * ({_travel('$or', row_lo, row_hi, '#pupil_over_k_v', '#pupil_over_max_v')})"))
        anims += [(f"@pm_{tag}.sx", "$pupil_s"), (f"@pm_{tag}.sy", "$pupil_s")]

    if eye.lid:
        top = eye.lid.face[2] - 8  # hinge on the top edge; the box hangs down from it
        children.append(_part(f"@l_{tag}", (0, top - cy, 0), boxes=[_box(eye.lid, (cx, top), Z_LID)]))
        anims += [(f"@l_{tag}.sy", "$lid"), (f"@l_{tag}.visible", "$lid > 0.01")]

    return _part(f"@e_{tag}", (cx, cy, -4), boxes=boxes, submodels=children), anims


def _lashes():
    parts, anims = [], []
    for side in ("r", "l"):
        top = LASHES[f"top_{side}"]
        cx, cy = _center(top.face)
        mover = _part(f"@ltm_{side}", boxes=[_box(top, (cx, cy), Z_LASH)])
        parts.append(_part(f"@lt_{side}", (cx, cy, -4), submodels=[mover]))
        anims.append((f"@ltm_{side}.ty", f"{TY_SIGN} * $lash_ty"))

        lash = LASHES[f"side_{side}"]
        cx, cy = _center(lash.face)
        parts.append(_part(f"@ls_{side}", (cx, cy, -4), boxes=[_box(lash, (cx, cy), Z_LASH)]))
        anims.append((f"@ls_{side}.sy", "$eye_sy"))
    return parts, anims


def _brows():
    """Each brow: a static cover over the face's own brow, and a moving brow on top."""
    parts, anims = [], []
    z = Z_BROW_OVER_HAIR if BROWS_OVER_HAIR else Z_BROW
    for slot in BROW_SLOTS:
        children = []
        for side, brow in slot.brows:
            tag = f"{slot.key}{side}"
            cx, cy = _center(brow.brow.face)
            if brow.cover:
                children.append(_part(f"@bc_{tag}", (0, 0, -4), boxes=[_box(brow.cover, (0, 0), Z_COVER)]))
            mover = _part(f"@bm_{tag}", boxes=[_box(brow.brow, (cx, cy), z)])
            children.append(_part(f"@b_{tag}", (cx, cy, -4), submodels=[mover]))
            anims.append((f"@bm_{tag}.ty", f"{TY_SIGN} * $brow_ty"))
            tilt = {"r": BROW_RZ_SIGN, "l": -BROW_RZ_SIGN}.get(side)
            if tilt:
                anims.append((f"@bm_{tag}.rz", f"torad({tilt} * $brow_rz)"))
        parts.append(_part(f"@brows_{slot.key}", submodels=children))
    return parts, anims


def build():
    """Return (submodels, animation blocks) for every slot and the lashes."""
    submodels, blocks = [], []
    for slot in SLOTS:
        eyes, anims = [], []
        for side, eye in (("r", slot.right), ("l", slot.left)):
            part, part_anims = _eye(slot.key, side, eye)
            eyes.append(part)
            anims += part_anims
        submodels.append(_part(f"@slot_{slot.key}", submodels=eyes))
        blocks.append(anims)
    lash_parts, lash_anims = _lashes()
    submodels.append(_part("@lashes", submodels=lash_parts))
    blocks.append(lash_anims)
    if BROWS:
        brow_parts, brow_anims = _brows()
        submodels += brow_parts
        blocks.append(brow_anims)
    return submodels, blocks
