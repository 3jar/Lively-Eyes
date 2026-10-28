"""Write the Modrinth description from README.md.

  python3 -m lively_eyes.modrinth

README.md shows images from art/, which GitHub resolves but Modrinth doesn't.
This swaps each art/ path for the same image in the Modrinth gallery and
writes dist/MODRINTH.md (run with src/ on PYTHONPATH).
"""

import argparse
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
GALLERY = "https://cdn.modrinth.com/data/fl6UhkVu/images/"

# art/ file -> its copy on Modrinth. Upload a new image to the gallery and add it here.
IMAGES = {
    "art/banner.png": "https://cdn.modrinth.com/data/cached_images/4cf7c63e67ace5479dbc4e029e36cc287d3854fe.png",
    "art/gaze.gif": GALLERY + "6ef4751c9e422bb8175c09d5bb0ccd4726abb985.gif",
    "art/hit.gif": GALLERY + "0b494815f2979ba7c9cf7d17b182e85f9416badb.gif",
    "art/surface.gif": GALLERY + "31af3c83f68aa2e5a2f7a96f65c0f8e9b6382a0e.gif",
    "art/doze.gif": GALLERY + "90edb117ec251e0b6e6889673e90e6c6ce40b9c3.gif",
    "art/order.png": "https://cdn.modrinth.com/data/cached_images/e36a4d09f5162d18d4dcd043b3c223713abfb9b2.png",
}

# an art/ path inside ![](...) or src="..."
ART = re.compile(r'(?<=[("])art/[^)"\s]+')


def description(readme):
    missing = sorted({path for path in ART.findall(readme) if path not in IMAGES})
    if missing:
        raise SystemExit(f"no Modrinth image for {', '.join(missing)}: upload it to the gallery and add it to IMAGES")
    return ART.sub(lambda m: IMAGES[m.group()], readme)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=PROJECT / "dist")
    args = parser.parse_args()
    text = description((PROJECT / "README.md").read_text())
    args.dist.mkdir(parents=True, exist_ok=True)
    out = args.dist / "MODRINTH.md"
    out.write_text(text)
    print("wrote", out)


if __name__ == "__main__":
    main()
