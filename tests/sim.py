"""Frame-by-frame simulator for the built pack.

Runs the animation blocks the way EMF does (in order, state persisting
between frames) against scripted inputs. Two hosts:
  standalone  our player.jem: host flag -> player_face.jpm -> host head
  fa          a stand-in for Fresh Animations' head interface around the jpm
"""

import json
import math

from emf_expr import Compiled, make_scope

FPS = 60

DEFAULT_INPUTS = {
    "head_yaw": 0.0, "head_pitch": 0.0,
    "is_in_gui": False, "is_first_person_hand": False,
    "hurt_time": 0, "is_hurt": False,
    "pos_y": 64.0, "is_on_ground": True,
    "is_in_water": False, "fluid_depth_up": 0.0, "is_burning": False,
    "health": 20.0, "max_health": 20.0, "is_alive": True, "death_time": 0,
    "is_sprinting": False, "is_gliding": False, "is_swimming": False, "is_crawling": False, "is_climbing": False,
    "day_time": 6000, "dimension": 0, "id": 42,
    "limb_speed": 0.0, "swing_progress": 0.0, "is_using_item": False, "is_blocking": False, "is_sneaking": False, "is_wet": False,
    "pos_x": 0.0, "pos_z": 0.0, "rot_y": 0.0,
    "player_pos_x": 0.0, "player_pos_y": 64.0, "player_pos_z": 0.0, "player_rot_y": 0.0, "distance": 0.0,
    "nbt__SleepingX": False,
}

INPUT_NAMES = set(DEFAULT_INPUTS) | {"frame_time", "frame_counter", "age", "head.rx", "head.ry", "head.rz"}


class State(dict):
    """Unset var/varb and part properties read as EMF defaults."""

    def __missing__(self, key):
        if key.startswith("global_var."):
            return 0.0
        if key.startswith("varb."):
            return False
        if key.startswith("var."):
            return 0.0
        prop = key.rsplit(".", 1)[-1]
        if "." in key and prop in ("sx", "sy", "sz"):
            return 1.0
        if "." in key and prop == "visible":
            return True
        if "." in key:
            return 0.0
        raise KeyError(f"unknown input variable {key!r}")


def compile_blocks(blocks, keep=lambda target: True):
    return [[(t, Compiled(e)) for t, e in block.items() if keep(t)] for block in blocks]


def load(files):
    jpm = json.loads(files["assets/minecraft/emf/cem/player_face.jpm"])
    jem = json.loads(files["assets/minecraft/emf/cem/player.jem"])
    return jpm, jem


class Sim:
    def __init__(self, files, mode="standalone", overrides=None, parts=False, entity_id=42, counter_step=1):
        jpm, jem = load(files)
        keep = (lambda t: True) if parts else (lambda t: t.startswith(("var.", "varb.", "head.")))
        self.mode = mode
        self.face = compile_blocks(jpm["animations"], keep)
        self.host_before = compile_blocks(jem["models"][0].get("animations", []))
        self.host_after = compile_blocks(jem["models"][2].get("animations", []))
        self.overrides = {k: v for k, v in (overrides or {}).items()}
        self.state = State()
        self.scope = make_scope(self.state)
        self.frame_counter = 1000
        self.t = 0.0
        self.entity_id = entity_id
        self.counter_step = counter_step  # 0 simulates a frame_counter that never advances
        self.fa_prev_yaw = 0.0

    def _run(self, blocks, after_first=None):
        for i, block in enumerate(blocks):
            for target, fn in block:
                self.state[target] = fn(self.scope)
            if i == 0 and after_first:
                self.state.update(after_first)

    def frame(self, inputs=None, passes=1):
        values = dict(DEFAULT_INPUTS, id=self.entity_id)
        values.update(inputs or {})
        values.update(frame_time=1 / FPS, frame_counter=self.frame_counter, age=self.t * 20)
        for _ in range(passes):
            self.state.update(values)
            self.state["head.ry"] = math.radians(values["head_yaw"])
            self.state["head.rx"] = math.radians(values["head_pitch"])
            self.state["head.rz"] = 0.0
            if self.mode == "standalone":
                self._run(self.host_before)
                self._run(self.face, self.overrides)
                self._run(self.host_after)
            else:
                # stand-in for FA: rebuilds its head inputs each frame (base mapping plus a
                # look-speed swing like FA's), applies them after
                swing = max(-1.0, min(1.0, (values["head_yaw"] - self.fa_prev_yaw) * FPS / 45))
                self.state["var.idl_headry"] = math.radians(max(-90, min(90, values["head_yaw"])) / 1.1 + 10 * swing)
                self.state["var.idl_headrx"] = math.radians(60 * math.sin(math.radians(values["head_pitch"])))
                self._run(self.face, self.overrides)
                self.state["var.head_ry"] = self.state["var.idl_headry"]
                self.state["var.head_rx"] = self.state["var.idl_headrx"]
        self.frame_counter += self.counter_step
        self.fa_prev_yaw = values["head_yaw"]
        self.t += 1 / FPS
        return self.state

    def run(self, seconds, inputs_at=lambda t: {}, record=()):
        rows = []
        for _ in range(int(round(seconds * FPS))):
            s = self.frame(inputs_at(self.t))
            rows.append({"t": self.t, **{k: s[k] for k in record}})
        return rows


def hurt_at(*times):
    """hurt_time counts down 10 -> 0 in ticks after each hit."""
    def hurt_time(t):
        active = [10 - int((t - h) * 20) for h in times if 0 <= t - h < 0.5]
        return max(active) if active else 0
    return hurt_time
