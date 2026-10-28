"""Where the test Minecraft instance lives.

Projects sit outside the instance, so its path comes from $MC_INSTANCE or
from instance.txt next to the project folder (one line: a Modrinth profile).
"""

import os
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]


def instance_dir():
    path = os.environ.get("MC_INSTANCE")
    if not path:
        txt = PROJECT.parent / "instance.txt"
        if not txt.exists():
            raise SystemExit(f"Which Minecraft instance? Put its path in {txt} or set MC_INSTANCE.")
        path = txt.read_text().strip()
    return Path(path).expanduser()


def modrinth_meta(instance):
    """Modrinth's shared folder (Minecraft jars and libraries) for a profile in .../ModrinthApp/profiles/<name>."""
    return instance.parents[1] / "meta"
