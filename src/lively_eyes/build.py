"""Build the resource pack.

  python3 -m lively_eyes.build [--install [RESOURCEPACKS_DIR]] [--debug]

--install alone copies into the test instance's resourcepacks (see instance.py).

Writes dist/<name>-<version>.zip (run with src/ on PYTHONPATH).
"""

import argparse
import json
import shutil
import zipfile
from pathlib import Path

from . import anim, geometry
from .config import AUTHOR, GAME_VERSIONS, NAME, PREFIX, RESOURCE_FORMAT, VERSION
from .expr import to_json_blocks
from .instance import instance_dir

PROJECT = Path(__file__).resolve().parents[2]
CEM = "assets/minecraft/emf/cem"
CREDIT = f"{NAME} {VERSION} by {AUTHOR}"

PACK_MCMETA = {
    "pack": {
        "pack_format": RESOURCE_FORMAT,
        "min_format": RESOURCE_FORMAT,
        "max_format": RESOURCE_FORMAT,
        "description": f"§b{NAME} §7{VERSION} · {AUTHOR}\n§7Reactive eyes · Fresh Animations compatible",
    }
}

CREDITS = f"""{NAME} {VERSION}
by {AUTHOR}. All rights reserved; see LICENSE.txt.
For Minecraft {GAME_VERSIONS}.

Reactive eye animations for Entity Model Features player models.
All models and animations in this pack are original work.

Compatibility
- Skins: reads the eye-slot layout used by skins made for Fresh Moves, so
  those skins work unchanged. No Fresh Moves files are included.
- Fresh Animations: when Fresh Animations' player model is active, this pack
  fills its player_face.jpm slot. No Fresh Animations files are included or
  modified. This pack is not affiliated with Fresh Animations.

Requires Entity Model Features and Entity Texture Features.
With Fresh Animations Player, place this pack BELOW it.
"""


def face_jpm(debug=False):
    submodels, part_blocks = geometry.build()
    blocks = anim.logic() + (anim.debug() if debug else []) + part_blocks + anim.fa_adapter()
    return {
        "credit": CREDIT,
        "textureSize": [64, 64],
        "submodels": submodels,
        "animations": to_json_blocks(blocks),
    }


def host_jem():
    """Standalone host: vanilla player + our face; attach keeps vanilla boxes."""
    return {
        "credit": CREDIT,
        "textureSize": [64, 64],
        "models": [
            {"part": "head", "id": f"{PREFIX}host", "attach": True, "animations": to_json_blocks(anim.host_flag())},
            {"part": "head", "id": f"{PREFIX}face", "translate": [0, 0, 0], "attach": True, "model": "player_face.jpm"},
            {"part": "head", "id": f"{PREFIX}head", "attach": True, "animations": to_json_blocks(anim.host_head())},
        ],
    }


def pack_files(debug=False):
    host = json.dumps(host_jem(), indent=1)
    return {
        "pack.mcmeta": json.dumps(PACK_MCMETA, indent=2, ensure_ascii=False),
        "pack.png": (PROJECT / "art" / "icon.png").read_bytes(),
        "CREDITS.txt": CREDITS,
        "LICENSE.txt": (PROJECT / "LICENSE.txt").read_text(),
        f"{CEM}/player_face.jpm": json.dumps(face_jpm(debug), indent=1),
        f"{CEM}/player.jem": host,
        f"{CEM}/player_slim.jem": host,
    }


def build(dist, debug=False):
    dist.mkdir(parents=True, exist_ok=True)
    out = dist / f"{NAME.replace(' ', '')}-{VERSION}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, text in pack_files(debug).items():
            zf.writestr(name, text)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=Path(__file__).resolve().parents[2] / "dist")
    parser.add_argument("--install", nargs="?", const="", type=str, metavar="DIR",
                        help="copy the zip into DIR, or into the test instance's resourcepacks")
    parser.add_argument("--debug", action="store_true", help="log key values to latest.log every 30 frames")
    args = parser.parse_args()
    out = build(args.dist, args.debug)
    print("built", out)
    if args.install is not None:
        dest = Path(args.install) if args.install else instance_dir() / "resourcepacks"
        shutil.copy2(out, dest / out.name)
        print("installed", dest / out.name)


if __name__ == "__main__":
    main()
