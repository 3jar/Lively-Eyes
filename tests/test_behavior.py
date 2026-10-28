"""Behavior checks: run scripted scenarios through the simulator."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from lively_eyes import build  # noqa: E402
from sim import Sim, hurt_at  # noqa: E402

FILES = build.pack_files()
NO_GLANCE = {"var.le_k_sac_prob": 0}
IDS = range(1, 9)


def blinks(rows, t0=0.0, t1=1e9):
    return sum(1 for r in rows if t0 <= r["t"] < t1 and r["varb.le_b_start"])


def ramp(t0, dur, amount):
    return lambda t: 0.0 if t < t0 else amount * min(1.0, (t - t0) / dur)


class GazeTest(unittest.TestCase):
    def test_small_glance_moves_eyes_not_head(self):
        sim = Sim(FILES, overrides=NO_GLANCE)
        yaw = ramp(1.0, 0.3, 8)
        rows = sim.run(2.0, lambda t: {"head_yaw": yaw(t)}, ["var.le_hy", "var.le_oc"])
        end = rows[-1]
        self.assertLess(abs(end["var.le_hy"]), 2.0)
        self.assertLess(end["var.le_oc"], -0.3)  # +yaw -> toward smaller columns

    def test_big_turn_head_follows_and_eyes_recenter(self):
        sim = Sim(FILES, overrides=NO_GLANCE)
        yaw = ramp(1.0, 0.25, 45)
        rows = sim.run(2.5, lambda t: {"head_yaw": yaw(t)}, ["var.le_hy", "var.le_oc"])
        self.assertGreater(min(r["var.le_oc"] for r in rows), -1.6)
        self.assertLess(min(r["var.le_oc"] for r in rows), -0.8)  # eyes lead first
        self.assertGreater(rows[-1]["var.le_hy"], 40)
        self.assertLess(abs(rows[-1]["var.le_oc"]), 0.2)

    def test_big_pitch_head_follows(self):
        for mode in ("standalone", "fa"):
            with self.subTest(mode=mode):
                sim = Sim(FILES, mode=mode, overrides=NO_GLANCE)
                rows = sim.run(3.0, lambda t: {"head_pitch": 0 if t < 1 else 40}, ["var.le_hp"])
                self.assertGreater(rows[-1]["var.le_hp"], 38)

    def test_standalone_head_applies_lag(self):
        sim = Sim(FILES, overrides=NO_GLANCE)
        sim.run(1.0)
        s = sim.frame({"head_yaw": 30})
        self.assertLess(abs(s["head.ry"]), 0.1)  # head has not caught up in one frame

    def test_fa_mode_injects_into_fa_head_and_reads_it_back(self):
        sim = Sim(FILES, mode="fa", overrides=NO_GLANCE)
        yaw = ramp(1.0, 0.25, 45)
        rows = sim.run(1.1, lambda t: {"head_yaw": yaw(t)}, ["var.head_ry", "var.le_eye_y", "varb.le_fa_ok"])
        self.assertTrue(rows[-1]["varb.le_fa_ok"])
        self.assertLess(rows[-1]["var.head_ry"], 0.5)  # lagging well behind 45 deg (0.71 rad / 1.1)
        self.assertGreater(rows[-1]["var.le_eye_y"], 10)
        rows = sim.run(1.5, lambda t: {"head_yaw": 45}, ["var.head_ry", "var.le_eye_y"])
        self.assertAlmostEqual(rows[-1]["var.head_ry"], 0.7854 / 1.1, delta=0.03)
        self.assertLess(abs(rows[-1]["var.le_eye_y"]) - 45 * (1 - 1 / 1.1), 1.0)

    def test_works_when_frame_counter_never_advances(self):
        for mode in ("standalone", "fa"):
            with self.subTest(mode=mode):
                sim = Sim(FILES, mode=mode, counter_step=0)
                yaw = ramp(1.0, 0.3, 8)
                rows = sim.run(20, lambda t: {"head_yaw": yaw(t), "head_pitch": yaw(t)}, ["var.le_hp", "varb.le_b_start"])
                self.assertGreater(sim.state["var.le_t"], 19)
                self.assertGreater(sum(r["varb.le_b_start"] for r in rows), 3)
                self.assertGreater(rows[-1]["var.le_hp"], 1)  # drifting toward the new pitch, not frozen at 0

    def test_fa_head_ignores_fa_look_swing_on_small_glances(self):
        sim = Sim(FILES, mode="fa", overrides=NO_GLANCE)
        sim.run(1.0)
        start = sim.t
        rows = sim.run(1.5, lambda t: {"head_yaw": min(8.0, (t - start) * 40)}, ["var.head_ry"])
        self.assertLess(max(abs(r["var.head_ry"]) for r in rows), 0.05)  # < 3 deg: eyes took the glance

    def test_gui_preview_does_not_touch_state(self):
        sim = Sim(FILES, overrides=NO_GLANCE)
        sim.run(1.0, lambda t: {"head_yaw": 20})
        before = sim.state["var.le_hy"]
        for _ in range(30):
            sim.frame({"head_yaw": -60, "is_in_gui": True})
        self.assertEqual(sim.state["var.le_hy"], before)

    def test_repeat_pass_in_one_frame_updates_once(self):
        sim = Sim(FILES)
        sim.run(1.0)
        t = sim.state["var.le_t"]
        sim.frame(passes=3)
        self.assertAlmostEqual(sim.state["var.le_t"] - t, 1 / 60, places=6)


class VerticalPupilTest(unittest.TestCase):
    def pupil_ty(self, pitch):
        sim = Sim(FILES, parts=True, overrides=NO_GLANCE)
        sim.run(1.0)
        start = sim.t
        sim.run(1.0, lambda t: {"head_pitch": max(-abs(pitch), min(abs(pitch), (t - start) * 10 * (1 if pitch > 0 else -1)))})
        return sim.state["le_pm_b1r.ty"], sim.state["le_pm_cr.ty"]

    def test_small_look_down_moves_pupils_down_a_little(self):
        flat, roomy = self.pupil_ty(8)
        self.assertGreater(flat, 0.1)   # 2-row eye: overshoot only
        self.assertLess(flat, 0.36)
        self.assertGreater(roomy, flat)  # 3-row eye has a real row of travel first

    def test_look_up_moves_pupils_up(self):
        flat, _ = self.pupil_ty(-8)
        self.assertLess(flat, -0.1)


class GlanceTest(unittest.TestCase):
    def test_glances_while_still(self):
        rows = Sim(FILES).run(20, record=["var.le_sac_y"])
        self.assertTrue(any(abs(r["var.le_sac_y"]) > 5 for r in rows))

    def test_no_glance_while_panning(self):
        rows = Sim(FILES).run(10, lambda t: {"head_yaw": 20 * t}, ["varb.le_sac_start"])
        self.assertFalse(any(r["varb.le_sac_start"] for r in rows[60:]))


class BlinkTest(unittest.TestCase):
    def test_baseline_rate_is_human(self):
        total = sum(blinks(Sim(FILES, entity_id=i).run(60, record=["varb.le_b_start"])) for i in IDS)
        per_minute = total / len(IDS)
        self.assertGreater(per_minute, 8)
        self.assertLess(per_minute, 30)

    def test_hit_blinks_then_widens(self):
        sim = Sim(FILES, overrides=NO_GLANCE)
        sim.run(3.0)
        ht = hurt_at(3.0)
        rows = sim.run(4.0, lambda t: {"hurt_time": ht(t), "is_hurt": ht(t) > 0},
                       ["var.le_blink_c", "var.le_eye_sy", "var.le_surprise", "var.le_tension"])
        self.assertGreater(max(r["var.le_blink_c"] for r in rows[:12]), 0.9)  # reflex blink within 0.2 s
        self.assertGreater(max(r["var.le_eye_sy"] for r in rows[:60]), 1.2)
        self.assertLess(rows[-1]["var.le_surprise"], 0.2)
        self.assertGreater(rows[-1]["var.le_tension"], 0.1)

    def test_repeated_hits_raise_blink_rate(self):
        hits = hurt_at(*[2.0 + 3 * k for k in range(10)])
        calm = shaken = 0
        for i in IDS:
            calm += blinks(Sim(FILES, entity_id=i).run(60, record=["varb.le_b_start"]), 33, 60)
            rows = Sim(FILES, entity_id=i).run(60, lambda t: {"hurt_time": hits(t)}, ["varb.le_b_start"])
            shaken += blinks(rows, 33, 60)
        self.assertGreater(shaken, calm * 1.3)

    def test_wide_eyes_dry_faster(self):
        calm = Sim(FILES, overrides={"var.le_k_sac_prob": 0, "var.le_k_blink_base": 0, "var.le_k_blink_dry": 0})
        calm.run(3)
        wide = Sim(FILES, overrides={"var.le_k_sac_prob": 0, "var.le_k_blink_base": 0, "var.le_k_blink_dry": 0, "var.le_k_surprise_tau": 1e6})
        wide.state["var.le_surprise"] = 1.0
        wide.run(3)
        self.assertGreater(wide.state["var.le_dryness"], calm.state["var.le_dryness"] * 2)

    def test_under_water_squints_and_blinks_less(self):
        water = {"is_in_water": True, "fluid_depth_up": 3.0}  # feet at y 64, water up to 67
        dry_total = wet_total = 0
        squint = 0
        for i in IDS:
            dry_total += blinks(Sim(FILES, entity_id=i).run(40, record=["varb.le_b_start"]), 5, 40)
            sim = Sim(FILES, entity_id=i)
            rows = sim.run(40, lambda t: water, ["varb.le_b_start"])
            wet_total += blinks(rows, 5, 40)
            squint = max(squint, sim.state["var.le_lid_s"])
        self.assertLess(wet_total, dry_total * 0.6)
        self.assertGreater(squint, 0.25)

    def test_low_health_droops_and_slows_blinks(self):
        sim = Sim(FILES)
        sim.run(20, lambda t: {"health": 3.0})
        self.assertGreater(sim.state["var.le_lid_s"], 0.2)
        self.assertGreater(sim.state["var.le_b_close"], 0.07 * 1.4)

    def test_idle_lids_fully_open_day_and_night(self):
        for day_time in (6000, 18000):
            with self.subTest(day_time=day_time):
                rows = Sim(FILES).run(30, lambda t: {"day_time": day_time}, ["var.le_lid_s"])
                self.assertEqual(max(r["var.le_lid_s"] for r in rows), 0)

    def test_dead_eyes_closed(self):
        sim = Sim(FILES)
        sim.run(1, lambda t: {"is_alive": False, "death_time": 5})
        self.assertEqual(sim.state["var.le_lid"], 1)

    def test_hard_landing_startles(self):
        def fall(t):
            if t < 1.0:
                return {"pos_y": 80.0, "is_on_ground": True}
            if t < 2.0:
                return {"pos_y": 80.0 - 0.5 * 32 * (t - 1.0) ** 2, "is_on_ground": False}
            return {"pos_y": 64.0, "is_on_ground": True}
        rows = Sim(FILES, overrides=NO_GLANCE).run(2.5, fall, ["var.le_surprise"])
        self.assertGreater(max(r["var.le_surprise"] for r in rows if r["t"] > 2.0), 0.4)


class PartsTest(unittest.TestCase):
    def test_part_animations_run(self):
        sim = Sim(FILES, parts=True, overrides=NO_GLANCE)
        sim.run(1.0)
        start = sim.t
        sim.run(1.0, lambda t: {"head_yaw": min(10.0, (t - start) * 20)})  # slow look: eyes only
        s = sim.state
        right, left = s["le_pm_a1r.tx"], s["le_pm_a1l.tx"]
        self.assertLess(right, -0.5)        # right pupil travels inside its eye
        self.assertLess(left, -0.1)         # left pupil is at its edge but still follows a little
        self.assertGreater(left, -0.41)     # ...capped overshoot
        self.assertLess(right, left)
        self.assertFalse(s["le_l_a1r.visible"] and s["var.le_lid"] <= 0.01)


if __name__ == "__main__":
    unittest.main()
