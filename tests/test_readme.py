"""Checks on README.md: the GitHub page, and the source of the Modrinth description."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from lively_eyes import modrinth  # noqa: E402

README = (ROOT / "README.md").read_text()
IMAGES = set(modrinth.ART.findall(README))


class ReadmeTest(unittest.TestCase):
    def test_images_exist(self):
        self.assertTrue(IMAGES)
        for path in IMAGES:
            self.assertTrue((ROOT / path).is_file(), f"README.md shows {path}, which does not exist")

    def test_images_have_alt_text(self):
        # the alt text titles the image when it is uploaded to the gallery
        alts = modrinth.alt_texts(README)
        for path in IMAGES:
            self.assertTrue(alts.get(path), f"{path} has no alt text")

    def test_description_swaps_every_image(self):
        urls = {path: f"https://cdn.example/{i}" for i, path in enumerate(IMAGES)}
        body = modrinth.description(README, urls)
        self.assertNotIn('"art/', body)
        self.assertNotIn("(art/", body)
        self.assertEqual(body.count("https://cdn.example/"), README.count('"art/') + README.count("(art/"))


if __name__ == "__main__":
    unittest.main()
