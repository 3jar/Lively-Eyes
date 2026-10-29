"""Checks on README.md and project.toml, the sources of the GitHub and Modrinth pages."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from lively_eyes import sync  # noqa: E402

README = (ROOT / "README.md").read_text()
IMAGES = set(sync.ART.findall(README))
CONFIG = sync.load()


class ReadmeTest(unittest.TestCase):
    def test_images_exist(self):
        self.assertTrue(IMAGES)
        for path in IMAGES:
            self.assertTrue((ROOT / path).is_file(), f"README.md shows {path}, which does not exist")

    def test_images_have_alt_text(self):
        # the alt text titles the image when it is uploaded to the gallery
        alts = sync.alt_texts(README)
        for path in IMAGES:
            self.assertTrue(alts.get(path), f"{path} has no alt text")

    def test_description_swaps_every_image(self):
        urls = {path: f"https://cdn.example/{i}" for i, path in enumerate(IMAGES)}
        body = sync.description(README, urls)
        self.assertNotIn('"art/', body)
        self.assertNotIn("(art/", body)
        self.assertEqual(body.count("https://cdn.example/"), README.count('"art/') + README.count("(art/"))


class ProjectTomlTest(unittest.TestCase):
    def test_identifies_both_sites(self):
        self.assertRegex(CONFIG["github"]["repo"], r"^[\w.-]+/[\w.-]+$")
        self.assertTrue(CONFIG["modrinth"]["id"])

    def test_topics_are_valid(self):
        topics = CONFIG["github"].get("topics", [])
        self.assertLessEqual(len(topics), 20)
        for topic in topics:
            self.assertRegex(topic, sync.TOPIC.pattern)

    def test_left_out_fields_stay_out(self):
        # a field missing from project.toml must not be sent, or it would be wiped
        wanted = sync.modrinth_wanted({"github": {"repo": "a/b"}, "modrinth": {"id": "x"}}, "body")
        self.assertEqual(set(wanted), {"source_url", "body"})
        self.assertEqual(sync.github_wanted({"github": {"repo": "a/b"}}), {})

    def test_empty_link_clears_it(self):
        wanted = sync.modrinth_wanted({"github": {"repo": "a/b"}, "modrinth": {"id": "x", "discord": ""}}, "body")
        self.assertIn("discord_url", wanted)
        self.assertIsNone(wanted["discord_url"])


if __name__ == "__main__":
    unittest.main()
