"""Behavior checks for gestures, panting, body reactions, weather, yawning and bed."""

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tests")]

from lively_eyes import build, config  # noqa: E402
from sim import Sim  # noqa: E402

FILES = build.pack_files()
NO_GLANCE = {"var.le_k_sac_prob": 0}
IDS = range(1, 9)


def peak(rows, key, t0=0.0, t1=1e9, fn=max):
    return fn(r[key] for r in rows if t0 <= r["t"] < t1)


def wave(start, amp, hz, dur):
    return lambda t: amp * math.sin(2 * math.pi * hz * (t - start)) if start <= t < start + dur else 0.0


# A water column whose top is at y 66; standing eyes are 1.62 above the feet.
WATER_TOP = 66.0
DIVE_Y = WATER_TOP - 1.62 - 1.0   # eyes a block under
FLOAT_Y = WATER_TOP - 1.62 + 0.3  # eyes just out


def in_water(y):
    """EMF counts fluid blocks from the feet block up in fluid_depth_up."""
    return {"is_in_water": True, "is_on_ground": False, "pos_y": y, "fluid_depth_up": WATER_TOP - math.floor(y)}


def bobbing(t):
    return in_water(WATER_TOP - 1.62 + 0.2 * math.sin(2 * math.pi * t / 0.8))


@unittest.skipUnless(config.GESTURES, "gestures are off in this build")
class GestureTest(unittest.TestCase):
    def test_crouch_spam_makes_happy_face(self):
        sneak = lambda t: {"is_sneaking": 1.0 <= t < 2.2 and int((t - 1.0) / 0.15) % 2 == 0}
        rows = Sim(FILES, overrides=NO_GLANCE).run(3, sneak, ["var.le_joy", "var.le_lid", "var.le_brow_ty"])
        self.assertGreater(peak(rows, "var.le_joy"), 0.8)
        self.assertGreater(peak(rows, "var.le_lid"), 0.6)
        if config.BROWS:
            self.assertLess(peak(rows, "var.le_brow_ty", fn=min), -0.3)

    def test_nodding_smiles(self):
        nod = wave(1.0, 15, 2, 1.5)
        rows = Sim(FILES, overrides=NO_GLANCE).run(3, lambda t: {"head_pitch": nod(t)}, ["var.le_yes", "var.le_no_ev"])
        self.assertGreater(peak(rows, "var.le_yes"), 0.8)
        self.assertEqual(peak(rows, "var.le_no_ev"), 0)

    def test_head_shake_reads_as_no(self):
        shake = wave(1.0, 20, 2.5, 1.6)
        rows = Sim(FILES, overrides=NO_GLANCE).run(3, lambda t: {"head_yaw": shake(t)}, ["var.le_no_ev", "var.le_yes", "var.le_furrow"])
        self.assertEqual(peak(rows, "var.le_no_ev"), 1)
        self.assertEqual(peak(rows, "var.le_yes"), 0)
        if config.BROWS:
            self.assertGreater(peak(rows, "var.le_furrow"), 0.6)  # the frown shows through the brows

    def test_ordinary_looking_is_not_a_gesture(self):
        def look(t):
            return {"head_yaw": min(45.0, max(0.0, (t - 1) * 180)), "head_pitch": min(30.0, max(0.0, (t - 2) * 120))}
        rows = Sim(FILES, overrides=NO_GLANCE).run(4, look, ["var.le_yes", "var.le_no_ev", "var.le_joy"])
        self.assertEqual(max(peak(rows, k) for k in ("var.le_yes", "var.le_no_ev", "var.le_joy")), 0)


class BreathTest(unittest.TestCase):
    def test_pants_after_sprinting(self):
        sim = Sim(FILES, overrides=NO_GLANCE)
        sim.run(20, lambda t: {"is_sprinting": True, "limb_speed": 0.9})
        rows = sim.run(3, record=["var.le_pant", "var.le_hx_p", "var.le_lid_s"])
        self.assertGreater(rows[-1]["var.le_pant"], 0.3)
        self.assertGreater(peak(rows, "var.le_hx_p", 1) - peak(rows, "var.le_hx_p", 1, fn=min), 2)  # breathing bob
        self.assertGreater(rows[-1]["var.le_lid_s"], 0.08)

    def test_walking_does_not_wind_you(self):
        rows = Sim(FILES).run(30, lambda t: {"limb_speed": 0.5}, ["var.le_pant"])
        self.assertEqual(peak(rows, "var.le_pant"), 0)


class BodyReactionTest(unittest.TestCase):
    def test_hard_landing_dips_head_and_squeezes_eyes(self):
        def fall(t):
            if t < 1.0:
                return {"pos_y": 80.0}
            if t < 2.0:
                return {"pos_y": 80.0 - 16 * (t - 1.0) ** 2, "is_on_ground": False}
            return {"pos_y": 64.0}
        rows = Sim(FILES, overrides=NO_GLANCE).run(3, fall, ["var.le_hx_p", "var.le_lid"])
        self.assertGreater(peak(rows, "var.le_hx_p", 2.0, 2.4), 6)
        self.assertGreater(peak(rows, "var.le_lid", 2.0, 2.3), 0.7)

    def test_surfacing_after_a_long_dive_shakes_head_and_blinks(self):
        sim = Sim(FILES, overrides=NO_GLANCE)
        sim.run(4, lambda t: in_water(DIVE_Y))
        rows = sim.run(1.5, lambda t: in_water(FLOAT_Y), ["var.le_hx_y", "varb.le_b_start"])
        self.assertGreater(peak(rows, "var.le_hx_y", fn=lambda v: max(abs(x) for x in v)), 6)
        self.assertGreaterEqual(sum(r["varb.le_b_start"] for r in rows), 2)

    def test_short_dip_does_not_shake(self):
        sim = Sim(FILES, overrides=NO_GLANCE)
        sim.run(3, lambda t: in_water(FLOAT_Y))
        rows = sim.run(1.5, lambda t: in_water(DIVE_Y), ["var.le_water_ev", "var.le_surface_ev"])
        rows += sim.run(2, lambda t: in_water(FLOAT_Y), ["var.le_water_ev", "var.le_surface_ev"])
        self.assertEqual(sum(r["var.le_water_ev"] for r in rows), 1)  # going under after a while out still reacts
        self.assertEqual(sum(r["var.le_surface_ev"] for r in rows), 0)

    def test_bobbing_at_the_surface_reacts_only_once(self):
        sim = Sim(FILES, overrides=NO_GLANCE)
        record = ["var.le_water_ev", "var.le_surface_ev"]
        rows = sim.run(4, lambda t: in_water(DIVE_Y), record)
        rows += sim.run(10, bobbing, record)
        self.assertEqual(sum(r["var.le_surface_ev"] for r in rows), 1)
        self.assertEqual(sum(r["var.le_water_ev"] for r in rows), 0)

    def test_a_one_frame_glitch_does_not_restart_the_dive(self):
        sim = Sim(FILES, overrides=NO_GLANCE)
        sim.run(4, lambda t: in_water(FLOAT_Y if 1.99 <= t < 2.01 else DIVE_Y))
        rows = sim.run(1, lambda t: in_water(FLOAT_Y), ["var.le_surface_ev"])
        self.assertEqual(sum(r["var.le_surface_ev"] for r in rows), 1)

    def test_attack_swing_shows_effort(self):
        swing = lambda t: {"swing_progress": min(1.0, (t - 1.0) / 0.3) if 1.0 <= t < 1.3 else 0.0}
        rows = Sim(FILES, overrides=NO_GLANCE).run(2, swing, ["var.le_hx_p", "var.le_lid_s"])
        self.assertGreater(peak(rows, "var.le_hx_p", 1.0, 1.4), 2)
        self.assertGreater(peak(rows, "var.le_lid_s", 1.0, 1.4), 0.2)


class WeatherTest(unittest.TestCase):
    def test_rain_squints_and_blinks_more(self):
        dry = wet = 0
        for i in IDS:
            dry += sum(r["varb.le_b_start"] for r in Sim(FILES, entity_id=i).run(60, record=["varb.le_b_start"]))
            sim = Sim(FILES, entity_id=i)
            wet += sum(r["varb.le_b_start"] for r in sim.run(60, lambda t: {"is_wet": True}, ["varb.le_b_start"]))
        self.assertGreater(sim.state["var.le_lid_s"], 0.1)
        self.assertGreater(wet, dry * 1.15)

    def test_nether_heat_squints(self):
        sim = Sim(FILES)
        sim.run(3, lambda t: {"dimension": -1})
        self.assertGreater(sim.state["var.le_squint"], 0.15)


class YawnTest(unittest.TestCase):
    def test_drowsy_players_yawn(self):
        doze = {**NO_GLANCE, "var.le_k_doze_start": 2, "var.le_k_doze_ramp": 2, "var.le_k_sleep_start": 100, "var.le_k_yawn_rate": 5}
        rows = Sim(FILES, overrides=doze).run(12, record=["var.le_yawn", "var.le_hx_p", "var.le_lid"])
        top = max(rows, key=lambda r: r["var.le_yawn"])
        self.assertGreater(top["var.le_yawn"], 0.8)
        self.assertLess(top["var.le_hx_p"], -8)   # head tips back
        self.assertGreater(top["var.le_lid"], 0.75)

    def test_yawning_can_be_turned_off(self):
        doze = {**NO_GLANCE, "var.le_k_doze_start": 2, "var.le_k_doze_ramp": 2, "var.le_k_sleep_start": 100, "var.le_k_yawn_rate": 0}
        rows = Sim(FILES, overrides=doze).run(12, record=["var.le_yawn"])
        self.assertEqual(peak(rows, "var.le_yawn"), 0)


class BedTest(unittest.TestCase):
    def test_eyes_shut_in_bed_and_open_after(self):
        sim = Sim(FILES, overrides=NO_GLANCE)
        sim.run(1)
        rows = sim.run(5, lambda t: {"nbt__SleepingX": True}, ["var.le_lid", "varb.le_b_start", "var.le_hx_p"])
        settled = [r for r in rows if r["t"] > 2.0]
        self.assertTrue(all(r["var.le_lid"] == 1 for r in settled))
        self.assertFalse(any(r["varb.le_b_start"] for r in settled))
        self.assertEqual(settled[-1]["var.le_hx_p"], 0)
        rows = sim.run(2, lambda t: {"limb_speed": 0.5}, ["varb.le_in_bed", "var.le_lid"])
        self.assertFalse(rows[-1]["varb.le_in_bed"])
        self.assertLess(rows[-1]["var.le_lid"], 0.3)


if __name__ == "__main__":
    unittest.main()
