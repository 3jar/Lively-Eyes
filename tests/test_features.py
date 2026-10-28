"""Behavior checks for dozing, head reactions, brows, eye contact and zoom."""

import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from lively_eyes import build, config  # noqa: E402
from sim import Sim, hurt_at  # noqa: E402

FILES = build.pack_files()
NO_GLANCE = {"var.le_k_sac_prob": 0}
FAST_DOZE = {**NO_GLANCE, "var.le_k_doze_start": 2, "var.le_k_doze_ramp": 2, "var.le_k_sleep_start": 8,
             "var.le_k_nod_gap_min": 0.5, "var.le_k_nod_gap_max": 1.0}
IDS = range(1, 9)


def peak(rows, key, t0=0.0, t1=1e9, fn=max):
    return fn(r[key] for r in rows if t0 <= r["t"] < t1)


class DozeTest(unittest.TestCase):
    def test_nods_off_sleeps_and_wakes(self):
        sim = Sim(FILES, overrides=FAST_DOZE)
        rows = sim.run(7, record=["var.le_lid", "var.le_hx_p", "var.le_nod_ev"])
        self.assertGreater(rows[-1]["var.le_lid"], 0.3)                    # drowsy lids
        self.assertGreater(peak(rows, "var.le_hx_p"), 10)                   # the head sinks...
        self.assertGreaterEqual(sum(r["var.le_nod_ev"] for r in rows), 1)  # ...and jerks back up
        rows = sim.run(4, record=["varb.le_asleep", "var.le_lid", "var.le_hx_p"])
        self.assertTrue(rows[-1]["varb.le_asleep"])
        self.assertEqual(rows[-1]["var.le_lid"], 1)
        self.assertGreater(rows[-1]["var.le_hx_p"], 5)               # head settles into a sleeping droop
        rows = sim.run(2, lambda t: {"limb_speed": 0.5}, ["var.le_wake_ev", "var.le_surprise", "var.le_lid", "var.le_hx_p"])
        self.assertEqual(sum(r["var.le_wake_ev"] for r in rows), 1)
        self.assertGreater(peak(rows, "var.le_surprise"), 0.4)
        self.assertLess(rows[-1]["var.le_lid"], 0.3)
        self.assertLess(rows[-1]["var.le_hx_p"], 1)

    def test_no_doze_while_walking(self):
        sim = Sim(FILES, overrides=FAST_DOZE)
        rows = sim.run(20, lambda t: {"limb_speed": 0.5}, ["var.le_drowsy"])
        self.assertEqual(peak(rows, "var.le_drowsy"), 0)

    def test_slow_looking_around_counts_as_input(self):
        sim = Sim(FILES, overrides=FAST_DOZE)
        rows = sim.run(20, lambda t: {"head_yaw": 30 * math.sin(t / 3)}, ["var.le_drowsy"])  # <= 10 deg/s
        self.assertEqual(peak(rows, "var.le_drowsy"), 0)


class HeadReactionTest(unittest.TestCase):
    def test_hit_flinches_head(self):
        sim = Sim(FILES, overrides=NO_GLANCE)
        ht = hurt_at(1.0)
        rows = sim.run(3, lambda t: {"hurt_time": ht(t)}, ["var.le_hx_p", "var.le_hx_r"])
        self.assertLess(peak(rows, "var.le_hx_p", 1.0, 1.3, min), -8)
        self.assertGreater(peak(rows, "var.le_hx_r", 1.0, 1.3, lambda v: max(abs(x) for x in v)), 3)
        self.assertLess(abs(rows[-1]["var.le_hx_p"]), 1)

    def test_no_glances_while_walking_or_attacking(self):
        for inputs in ({"limb_speed": 0.5}, {"swing_progress": 0.5}):
            with self.subTest(inputs=inputs):
                rows = Sim(FILES).run(30, lambda t: inputs, ["varb.le_sac_start"])
                self.assertFalse(any(r["varb.le_sac_start"] for r in rows))

    def test_idle_glances_keep_the_head_still(self):
        rows = Sim(FILES).run(40, record=["varb.le_sac_start", "var.le_hx_r", "var.le_hx_p"])  # before dozing starts
        self.assertTrue(any(r["varb.le_sac_start"] for r in rows))
        for key in ("var.le_hx_r", "var.le_hx_p"):
            self.assertLess(peak(rows, key, fn=lambda v: max(abs(x) for x in v)), 0.5, key)

    def test_curious_tilt_with_glances(self):
        rows = Sim(FILES, overrides={"var.le_k_tilt_prob": 1}).run(20, record=["var.le_tilt"])
        self.assertGreater(peak(rows, "var.le_tilt", fn=lambda v: max(abs(x) for x in v)), 5)

    def test_sun_glare_by_day_only(self):
        for day_time, expect_squint in ((6000, True), (18000, False)):
            with self.subTest(day_time=day_time):
                sim = Sim(FILES, overrides=NO_GLANCE)
                sim.run(4, lambda t: {"head_pitch": -70, "pos_y": 70.0, "day_time": day_time})
                if expect_squint:
                    self.assertGreater(sim.state["var.le_lid_s"], 0.25)
                else:
                    self.assertLess(sim.state["var.le_lid_s"], 0.05)

    def test_sneaking_glances_more(self):
        calm = sneaky = 0
        for i in IDS:
            calm += sum(r["varb.le_sac_start"] for r in Sim(FILES, entity_id=i).run(60, record=["varb.le_sac_start"]))
            rows = Sim(FILES, entity_id=i).run(60, lambda t: {"is_sneaking": True}, ["varb.le_sac_start"])
            sneaky += sum(r["varb.le_sac_start"] for r in rows)
        self.assertGreater(sneaky, calm * 1.3)

    def test_falling_widens_eyes_and_looks_down(self):
        sim = Sim(FILES, overrides=NO_GLANCE)
        sim.run(1, lambda t: {"pos_y": 200.0})
        start = sim.t
        rows = sim.run(1.5, lambda t: {"pos_y": 200 - 20 * (t - start), "is_on_ground": False},
                       ["var.le_surprise", "var.le_eye_p"])
        self.assertGreater(rows[-1]["var.le_surprise"], 0.5)
        self.assertGreater(rows[-1]["var.le_eye_p"], 3)


class ReleaseSwitchTest(unittest.TestCase):
    """Features switched off for a release leave no trace in the built pack."""

    def test_switched_features_are_built_only_when_on(self):
        jpm = FILES["assets/minecraft/emf/cem/player_face.jpm"]
        checks = {
            "brow": config.BROWS, "furrow": config.BROWS,
            "gesture": config.GESTURES, "le_joy": config.GESTURES, "le_g_": config.GESTURES,
            "contact": config.CONTACT, "le_c_": config.CONTACT, "shy": config.CONTACT,
            "le_no\"": config.BROWS and config.GESTURES,
        }
        for word, on in checks.items():
            with self.subTest(word=word):
                self.assertEqual(word in jpm, on)


@unittest.skipUnless(config.BROWS, "brows are off in this build")
class BrowTest(unittest.TestCase):
    def test_brows_raise_when_startled(self):
        def fall(t):
            if t < 1.0:
                return {"pos_y": 80.0}
            if t < 2.0:
                return {"pos_y": 80.0 - 16 * (t - 1.0) ** 2, "is_on_ground": False}
            return {"pos_y": 64.0}
        rows = Sim(FILES, overrides=NO_GLANCE).run(3, fall, ["var.le_brow_ty"])
        self.assertLess(peak(rows, "var.le_brow_ty", fn=min), -0.4)

    def test_brows_furrow_when_hurt(self):
        ht = hurt_at(1.0)
        rows = Sim(FILES, overrides=NO_GLANCE).run(2, lambda t: {"hurt_time": ht(t)}, ["var.le_brow_ty", "var.le_brow_rz"])
        self.assertGreater(peak(rows, "var.le_brow_ty", 1.0, 1.3), 0.3)
        self.assertGreater(peak(rows, "var.le_brow_rz", 1.0, 1.3), 5)


@unittest.skipUnless(config.CONTACT, "eye contact is off in this build")
class ContactTest(unittest.TestCase):
    """Another player at the origin facing +z; the viewer stands 1.5 to the side, 4 ahead."""

    VIEWER = {"player_pos_x": 1.5, "player_pos_z": 4.0, "distance": math.hypot(1.5, 4.0)}
    LOOKING_AT_THEM = math.radians(math.degrees(math.atan2(1.5, -4.0)))

    def run_scene(self, **inputs):
        scene = {**self.VIEWER, **inputs}
        return Sim(FILES, overrides=NO_GLANCE).run(20, lambda t: scene, ["varb.le_contact_on", "var.le_look_y"])

    def test_meets_the_viewers_eyes(self):
        rows = self.run_scene(player_rot_y=self.LOOKING_AT_THEM)
        during = [r["var.le_look_y"] for r in rows if r["varb.le_contact_on"]]
        self.assertTrue(during)
        self.assertAlmostEqual(during[0], -20, delta=0.5)  # viewer is ~20.6 deg to their right, clamped

    def test_ignores_a_viewer_looking_elsewhere(self):
        rows = self.run_scene(player_rot_y=0.0)
        self.assertFalse(any(r["varb.le_contact_on"] for r in rows))

    def test_never_on_own_player(self):
        rows = self.run_scene(player_rot_y=self.LOOKING_AT_THEM, distance=0.0)
        self.assertFalse(any(r["varb.le_contact_on"] for r in rows))


class ZoomTest(unittest.TestCase):
    def test_zoom_squints_own_player_only(self):
        for distance, expect in ((0.0, True), (5.0, False)):
            with self.subTest(distance=distance):
                sim = Sim(FILES, overrides=NO_GLANCE)
                sim.run(2, lambda t: {"global_var.le_zoom": 1.0, "distance": distance})
                self.assertEqual(sim.state["var.le_squint"] > 0.3, expect)


class GeometryTest(unittest.TestCase):
    def test_boxes_sit_just_in_front_of_the_face_and_brows_over_the_hair(self):
        jpm = json.loads(FILES["assets/minecraft/emf/cem/player_face.jpm"])
        over_hair = config.BROWS_OVER_HAIR

        def walk(model, z=0.0):
            z += model["translate"][2]
            for box in model.get("boxes", []):
                yield model["id"], z + box["coordinates"][2]
            for child in model.get("submodels", []):
                yield from walk(child, z)

        for part, front in (p for m in jpm["submodels"] for p in walk(m)):
            with self.subTest(part=part):
                if over_hair and part.startswith("le_bm_"):
                    self.assertTrue(-4.9 < front < -4.75, front)  # past Skin Layers 3D's bangs (-4.72)
                else:
                    self.assertTrue(-4.05 < front < -4.0, front)


if __name__ == "__main__":
    unittest.main()
