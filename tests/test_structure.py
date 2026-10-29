"""Static checks on the generated pack files."""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from emf_expr import Compiled  # noqa: E402
from lively_eyes import anim, build  # noqa: E402
from lively_eyes.config import AUTHOR, MAX_FORMAT, MIN_FORMAT, PREFIX  # noqa: E402
from sim import INPUT_NAMES  # noqa: E402

CEM = "assets/minecraft/emf/cem"


def part_ids(models):
    for m in models:
        if "id" in m:
            yield m["id"]
        yield from part_ids(m.get("submodels", []))


class StructureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = build.pack_files()
        cls.jpm = json.loads(cls.files[f"{CEM}/player_face.jpm"])
        cls.jem = json.loads(cls.files[f"{CEM}/player.jem"])
        cls.blocks = cls.jpm["animations"] + [b for m in cls.jem["models"] for b in m.get("animations", [])]
        cls.ids = list(part_ids(cls.jpm["submodels"]))

    def test_release_metadata(self):
        pack = json.loads(self.files["pack.mcmeta"])["pack"]
        self.assertEqual((pack["min_format"], pack["max_format"]), (MIN_FORMAT, MAX_FORMAT))
        self.assertTrue(MIN_FORMAT <= pack["pack_format"] <= MAX_FORMAT)
        self.assertTrue(self.files["pack.png"].startswith(b"\x89PNG"))
        self.assertIn("All rights reserved", self.files["LICENSE.txt"])
        self.assertIn(AUTHOR, self.files["CREDITS.txt"])

    def test_all_files_are_valid_json(self):
        for name, text in self.files.items():
            if name.endswith((".jem", ".jpm", ".mcmeta")):
                json.loads(text)

    def test_hosts_load_face_module(self):
        self.assertEqual(self.files[f"{CEM}/player.jem"], self.files[f"{CEM}/player_slim.jem"])
        models = [m.get("model") for m in self.jem["models"]]
        self.assertIn("player_face.jpm", models)
        # the host must never hide the vanilla player
        self.assertTrue(all(m.get("attach") for m in self.jem["models"]))

    def test_parts_use_plain_model_space(self):
        # invertAxis on the shared jpm came out un-inverted in game; parts are authored in model space
        def walk(models):
            for m in models:
                yield m
                yield from walk(m.get("submodels", []))
        self.assertFalse(any(m.get("invertAxis") for m in walk(self.jpm["submodels"])))
        self.assertNotIn("invertAxis", self.jpm)

    def test_eyes_sit_on_the_face(self):
        # slot a1 right eye: face columns 1-2, row 6 -> model x -3..-1, y -2..-1, just in front of z -4
        eye = next(m for m in self.jpm["submodels"][0]["submodels"] if m["id"] == f"{PREFIX}e_a1r")
        x, y, z = eye["translate"]
        bx, by, bz, w, h, _ = eye["boxes"][0]["coordinates"]
        self.assertEqual((x + bx, x + bx + w, y + by, y + by + h), (-3, -1, -2, -1))
        self.assertLess(z + bz, -4)

    def test_part_ids_unique_and_prefixed(self):
        self.assertEqual(len(self.ids), len(set(self.ids)))
        self.assertTrue(all(i.startswith(PREFIX) for i in self.ids))

    def test_expressions_compile_and_read_only_known_names(self):
        assigned = {t for b in self.blocks for t in b}
        ids = set(self.ids)
        for block in self.blocks:
            for target, text in block.items():
                with self.subTest(target=target):
                    expr = Compiled(text)
                    for name in expr.names:
                        if name.startswith(("var.", "varb.")):
                            self.assertTrue(name in assigned or name in anim.FA_INTERFACE, f"{name} is never assigned")
                        elif name.startswith("global_var."):
                            self.assertEqual(name, anim.BRIDGE_ZOOM)
                        elif name.split(".")[0] in ids:
                            continue
                        else:
                            self.assertIn(name, INPUT_NAMES)

    def test_each_variable_has_one_writer(self):
        # two modules sharing a name silently overwrite each other ($hp was both head pitch and health)
        rewritten = {f"var.{PREFIX}dryness", *anim.FA_INPUTS}  # deliberately updated in a later stage too
        writers = {}
        for i, block in enumerate(self.jpm["animations"]):
            for target in block:
                if target.startswith(("var.", "varb.")):
                    writers.setdefault(target, set()).add(i)
        shared = {t: b for t, b in writers.items() if len(b) > 1 and t not in rewritten}
        self.assertEqual(shared, {})

    def test_targets_are_ours_or_declared_interface(self):
        ids = set(self.ids)
        for block in self.blocks:
            for target in block:
                with self.subTest(target=target):
                    if target.startswith(("var.", "varb.")):
                        name = target.split(".", 1)[1]
                        self.assertTrue(name.startswith(PREFIX) or target in anim.FA_INTERFACE)
                    elif target.startswith("head."):
                        continue
                    else:
                        self.assertIn(target.rsplit(".", 1)[0], ids)

    def test_fa_interface_only_in_adapter_and_readback(self):
        users = {t for b in self.jpm["animations"] for t, e in b.items() if any(n in e for n in anim.FA_INTERFACE)}
        self.assertEqual(users, {f"varb.{PREFIX}fa_ok", f"var.{PREFIX}rhy", f"var.{PREFIX}rhp", *anim.FA_INPUTS})


if __name__ == "__main__":
    unittest.main()
