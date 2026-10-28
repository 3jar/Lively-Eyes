"""Animation logic, in evaluation order:

  inputs -> gaze -> gestures (only with config.GESTURES) -> doze -> bed -> state -> glances -> contact (only with config.CONTACT) -> eye angles -> blink -> face
  -> brows (only with config.BROWS)

Every function returns a list of blocks (see expr.py). Part-level
animations live in geometry.py and only read the face outputs set here:
  $eye_sy    eye height scale (wide eyes)
  $pupil_s   pupil scale
  $oc, $or   pupil offset in face columns/rows (+ = toward larger column/row)
  $lid       lid closure 0..1
  $lash_ty   top eyelash lift
  $brow_ty   brow offset in rows (- = up), $brow_rz brow inner-end tilt (deg); with brows only
and the host adapters read the head outputs:
  $hy, $hp   lagged head yaw/pitch (deg); $hx_y, $hx_p, $hx_r extra head yaw/pitch/roll (deg)
"""

from .config import BED_NBT, BROW_TUNABLES, BROWS, CONTACT, CONTACT_TUNABLES, GESTURE_TUNABLES, GESTURES, TUNABLES
from .expr import num

# Names Fresh Animations' player model exposes and recomputes every frame.
# The only coupling to FA; if they disappear the eyes still work, only the
# head behaviour is lost.
FA_HEAD_YAW_IN = "var.idl_headry"
FA_HEAD_PITCH_IN = "var.idl_headrx"
FA_HEAD_ROLL_IN = "var.idl_headrz"
FA_HEAD_YAW_OUT = "var.head_ry"
FA_HEAD_PITCH_OUT = "var.head_rx"
FA_INPUTS = (FA_HEAD_YAW_IN, FA_HEAD_PITCH_IN, FA_HEAD_ROLL_IN)
FA_INTERFACE = FA_INPUTS + (FA_HEAD_YAW_OUT, FA_HEAD_PITCH_OUT)

# Written by the optional Lively Eyes Bridge mod; reads as 0 without it.
BRIDGE_ZOOM = "global_var.le_zoom"

RANDOMS = 16


def tunables():
    tunables = (TUNABLES + (CONTACT_TUNABLES if CONTACT else []) + (GESTURE_TUNABLES if GESTURES else [])
                + (BROW_TUNABLES if BROWS else []))
    return [[(f"#{name}", str(num(value))) for name, value, _ in tunables]]


def inputs():
    frame = [
        # skip GUI previews, the first-person hand pass, and repeat passes in one frame.
        # age (ticks + partial tick) changes every frame and stops while paused;
        # frame_counter is not relied on, it may not advance.
        ("?live", "!is_in_gui && !is_first_person_hand"),
        ("?stale", "?live && abs(age - $last_age) > 10"),
        ("$dt", "if(?live && age != $last_age, clamp((age - $last_age) / 20, 0.0001, 0.1), 0)"),
        ("$last_age", "if(?live, age, $last_age)"),
        ("?tick", "$dt > 0"),
        ("?ev_ok", "?tick && !?stale"),
        ("$t", "$t + $dt"),
        ("$n", "if(?tick, fmod($n + 1, 8192), $n)"),
        # small seed keeps float32 precision; changes every frame, differs per entity
        ("$seed", "$n * 3 + fmod(id, 997) * 2311"),
        *((f"$r{i}", f"random($seed + {i})") for i in range(1, RANDOMS + 1)),
        ("?dead", "!is_alive || death_time > 0"),
        ("$health", "clamp(health / max(max_health, 1), 0, 1)"),
        ("$wind", "if(is_gliding, 1, is_sprinting, 0.4, 0)"),
        # head under water: eyes below the top of the water. fluid_depth_up counts fluid
        # blocks from the feet block up, so that top is floor(pos_y) + fluid_depth_up.
        ("$eye_h", "if(is_swimming || is_gliding || is_crawling, 0.4, is_sneaking, 1.27, 1.62)"),
        ("$head_depth", "if(is_in_water && fluid_depth_up > 0, floor(pos_y) + fluid_depth_up - pos_y - $eye_h, -1)"),
        ("?sub_raw", "$head_depth > #submerge_depth"),
        # flips only once the new side has held for a moment, so a one-frame glitch can't
        ("$sub_hold", "if(!?tick, $sub_hold, (?sub_raw && !?sub) || (!?sub_raw && ?sub), $sub_hold + $dt, 0)"),
        ("?sub_flip", "?tick && $sub_hold >= #sub_settle"),
        ("?sub", "(?sub && !?sub_flip) || (!?sub && ?sub_flip)"),
        ("$vy", "if(?ev_ok, (pos_y - $prev_y) / max($dt, 0.001), 0)"),
        # the client player's own model is at distance 0; zoom only concerns it
        ("?other", "distance > 0.5"),
        ("$zoom", f"if(?other, 0, clamp({BRIDGE_ZOOM}, 0, 1))"),
    ]
    events = [
        ("$hurt_ev", "if(?ev_ok && hurt_time > $prev_hurt + 0.5, 1, 0)"),
        ("$land_ev", "if(?ev_ok && is_on_ground && !?prev_ground, clamp((-$fall - #land_speed_min) / #land_speed_span, 0, 1), 0)"),
        # bobbing at the surface dips the head in and out; only a real dive or surfacing counts
        ("$water_ev", "if(?ev_ok && ?sub_flip && ?sub && $out_t >= #dive_min_out, 1, 0)"),
        ("$fire_ev", "if(?ev_ok && is_burning && !?prev_burn, 1, 0)"),
        ("$surface_ev", "if(?ev_ok && ?sub_flip && !?sub && $under_t >= #surface_min_under, 1, 0)"),
        ("$jump_ev", "if(?ev_ok && !is_on_ground && ?prev_ground && $vy > 2, 1, 0)"),
        ("$swing_ev", "if(?ev_ok && swing_progress > 0 && (swing_progress < $prev_swing - 0.2 || $prev_swing == 0), 1, 0)"),
    ]
    remember = [
        ("$prev_hurt", "if(?tick, hurt_time, $prev_hurt)"),
        ("$prev_swing", "if(?tick, swing_progress, $prev_swing)"),
        ("$prev_y", "if(?tick, pos_y, $prev_y)"),
        ("$fall", "if(!?tick, $fall, is_on_ground, 0, min($fall, $vy))"),
        ("?prev_ground", "(?tick && is_on_ground) || (!?tick && ?prev_ground)"),
        ("$under_t", "if(!?tick, $under_t, ?sub, $under_t + $dt, 0)"),
        ("$out_t", "if(!?tick, $out_t, ?sub, 0, $out_t + $dt)"),
        ("?prev_burn", "(?tick && is_burning) || (!?tick && ?prev_burn)"),
    ]
    return [frame, events, remember]


def gaze():
    """Rendered head lags the look direction; eyes cover the difference."""
    measure = [
        ("?gate", "?live && !is_gliding && !is_swimming && !is_crawling && !?dead"),
        ("$vel", "if(?stale, 0, ?tick, lerp(1 - exp(-$dt * #vel_k), $vel, sqrt(pow(head_yaw - $py, 2) + pow(head_pitch - $pp, 2)) / max($dt, 0.001)), $vel)"),
        ("$py", "if(?tick, head_yaw, $py)"),
        ("$pp", "if(?tick, head_pitch, $pp)"),
        ("$ey0", "head_yaw - $hy"),
        ("$ep0", "head_pitch - $hp"),
        ("$err", "sqrt(pow($ey0, 2) + pow($ep0 * 1.3, 2))"),
        ("?follow_was", "?follow"),
    ]
    step = "clamp({e} * (1 - exp(-$dt * $gk)), -#head_maxv * $dt, #head_maxv * $dt)"
    head = [
        # engage on a big or fast shift, stay engaged until the eyes are centered again
        ("?follow", "(!?tick && ?follow) || (?tick && ((?follow && ($err > 1 || $vel > 30)) || (!?follow && ($err > #deadzone || $vel > #speed_trigger))))"),
        ("$gk", "if(?follow, #head_k, #drift_k)"),
        ("$hy", f"if(!?live, $hy, ?stale || !?gate, head_yaw, $hy + {step.format(e='$ey0')})"),
        ("$hp", f"if(!?live, $hp, ?stale || !?gate, head_pitch, $hp + {step.format(e='$ep0')})"),
        ("$gz_ev", "if(?ev_ok && ?follow && !?follow_was && $err > #gaze_event_deg, 1, 0)"),
    ]
    return [measure, head]


def gestures():
    """Body language players use instead of words: crouch spam, nodding, head shaking."""
    speed = "if(?stale, 0, ?tick, lerp(1 - exp(-$dt * 20), {v}, ({a} - {p}) / max($dt, 0.001)), {v})"
    velocity = [
        ("$g_yv", speed.format(v="$g_yv", a="head_yaw", p="$g_py")),
        ("$g_pv", speed.format(v="$g_pv", a="head_pitch", p="$g_pp")),
        ("$g_py", "if(?tick, head_yaw, $g_py)"),
        ("$g_pp", "if(?tick, head_pitch, $g_pp)"),
    ]
    # a swing counts when the head moves fast the other way from the last counted swing
    swings = [
        ("?g_pd", "?tick && $g_pv > #gesture_nod_speed && $g_pside != 1"),
        ("?g_pu", "?tick && $g_pv < -#gesture_nod_speed && $g_pside != -1"),
        ("?g_yr", "?tick && $g_yv > #gesture_shake_speed && $g_yside != 1"),
        ("?g_yl", "?tick && $g_yv < -#gesture_shake_speed && $g_yside != -1"),
        ("?g_crouch", "?tick && is_sneaking && !?g_was_sneak && limb_speed < 0.2"),
    ]
    decay = "if({ev} > 0, 0, {n} * exp(-$dt / {tau}))"
    count = [
        ("$g_pside", "if(?g_pd, 1, ?g_pu, -1, $g_pside)"),
        ("$g_yside", "if(?g_yr, 1, ?g_yl, -1, $g_yside)"),
        # counters reset the frame after their gesture fired
        ("$g_nods", decay.format(ev="$yes_ev", n="$g_nods", tau="#gesture_swing_tau") + " + if(?g_pd || ?g_pu, 1, 0)"),
        ("$g_shakes", decay.format(ev="$no_ev", n="$g_shakes", tau="#gesture_swing_tau") + " + if(?g_yr || ?g_yl, 1, 0)"),
        ("$g_crouches", decay.format(ev="$joy_ev", n="$g_crouches", tau="#gesture_sneak_tau") + " + if(?g_crouch, 1, 0)"),
        ("?g_was_sneak", "(?tick && is_sneaking) || (!?tick && ?g_was_sneak)"),
    ]
    fire = [
        ("$yes_ev", "if($g_nods > #gesture_nod_count && $g_shakes < 1, 1, 0)"),
        ("$no_ev", "if($g_shakes > #gesture_shake_count && $g_nods < 1.5, 1, 0)"),
        ("$joy_ev", "if($g_crouches > #gesture_sneak_count - 0.5, 1, 0)"),
        ("$joy", "if(?tick, max($joy * exp(-$dt / #joy_tau), $joy_ev), $joy)"),
        ("$yes", "if(?tick, max($yes * exp(-$dt / #yes_tau), $yes_ev), $yes)"),
    ]
    return [velocity, swings, count, fire]


def doze():
    """Left alone (no input, no other animation), the player gets drowsy, nods off, then falls asleep."""
    return [[
        ("?active", "$vel > #active_vel || limb_speed > 0.05 || !is_on_ground || swing_progress > 0 || is_using_item || is_blocking"
                    " || is_gliding || is_swimming || is_climbing || $hurt_ev > 0 || ?sub || ?dead"),
        ("$idle_was", "$idle_t"),
        ("$idle_t", "if(?stale, 0, ?tick, if(?active, 0, $idle_t + $dt), $idle_t)"),
        ("$wake_ev", "if(?ev_ok && $idle_t == 0 && $idle_was > #doze_start, 1, 0)"),
        ("$drowsy_t", "clamp(($idle_t - #doze_start) / #doze_ramp, 0, 1)"),
        ("?asleep", "$idle_t > #sleep_start"),
        # drowsiness creeps in, but is gone quickly once woken
        ("$drowsy", "$drowsy + ($drowsy_t - $drowsy) * (1 - exp(-$dt * if($drowsy_t > $drowsy, 0.5, 4)))"),
        # sleeping posture: the head settles down slowly and comes up fast on waking
        ("$sleep_head", "if(?tick, $sleep_head + (if(?asleep, 1, 0) - $sleep_head) * (1 - exp(-$dt * if(?asleep, 0.5, 6))), $sleep_head)"),
    ], [
        # drowsy players yawn now and then: head tips back, eyes squeeze
        ("?yawn_start", "?tick && !?yawning && !?nodding && !?asleep && $drowsy > 0.3 && $r11 < 1 - exp(-#yawn_rate * $drowsy * $dt)"),
        ("$yawn_t0", "if(?yawn_start, $t, $yawn_t0)"),
        ("?yawning", "?yawn_start || (?yawning && !?active && $t - $yawn_t0 < #yawn_time)"),
        ("$yawn", "if(?yawning, sin(3.1416 * clamp(($t - $yawn_t0) / #yawn_time, 0, 1)), 0)"),
    ], [
        # nodding off: the head sinks slowly as the eyes close, then jerks back up
        ("?can_nod", "$drowsy > #nod_min && !?asleep && !?active && !?yawning"),
        ("?nod_start", "?tick && ?can_nod && !?nodding && $nod < 0.05 && $t > $nod_next"),
        ("$nod_dur", "if(?nod_start, #nod_drop_time * (0.8 + 0.4 * $r12), $nod_dur)"),
        ("?nod_jerk", "?tick && ?nodding && ($nod >= 1 || !?can_nod || ($nod > 0.6 && $r10 < 1 - exp(-0.8 * $dt)))"),
    ], [
        ("?nodding", "?nod_start || (?nodding && !?nod_jerk)"),
        ("$nod_ev", "if(?ev_ok && ?nod_jerk && ?can_nod, 1, 0)"),
        ("$nod_next", "if(?nod_jerk, $t + #nod_gap_min + $r12 * (#nod_gap_max - #nod_gap_min), $nod_next)"),
        # falling asleep mid-nod hands over to the sleeping posture slowly
        ("$nod", "if(!?tick, $nod, ?nodding, min(1, $nod + $dt / $nod_dur), ?asleep, $nod * exp(-$dt * 0.6), $nod * exp(-$dt * #nod_recover_k))"),
        ("$doze_lid", "if(?asleep, 1, clamp(#doze_lid * $drowsy + 0.9 * $nod, 0, 1))"),
    ]]


def bed():
    """Eyes shut in bed. EMF has no sleeping variable, so read the SleepingX tag via nbt(),
    only while idle and only every few frames: reading NBT is not free."""
    if not BED_NBT:
        return [[("?in_bed", "false")]]
    return [[
        ("?bed_check", "?tick && !?active && fmod($n, #bed_check_frames) == 0"),
        ("?in_bed", "(?bed_check && nbt(SleepingX,exists:true)) || (!?bed_check && ?in_bed && !?active)"),
    ]]


def state():
    """Reactive state: surprise, tension, fatigue, squint, dryness, and what they lead to."""
    events = ("#ev_hurt_s * $hurt_ev + #ev_land_s * $land_ev + #ev_water_s * $water_ev + #ev_fire_s * $fire_ev"
              " + #ev_gaze_s * $gz_ev + #ev_wake_s * $wake_ev + #ev_nod_s * $nod_ev")
    sun = "if(dimension == 0 && between(day_time, 0, 12000) && !is_wet && pos_y > 55, clamp((-head_pitch - #sun_pitch) / 25, 0, 1), 0)"
    squint = ("max(if(?sub, #sq_water, 0), if(is_burning, #sq_fire, 0), $wind * #sq_wind, #sq_sun * $sun,"
              " if(is_sneaking, #sq_sneak, 0), #sq_zoom * $zoom, #sq_rain * $rain, #sq_heat * $heat)")
    return [[
        ("$fear_t", "if(!is_on_ground && !is_gliding && !?sub, clamp((-$vy - #fear_speed) / 10, 0, 1), 0)"),
        ("$fear", "if(?tick, $fear + ($fear_t - $fear) * (1 - exp(-$dt * 6)), $fear)"),
        ("$surprise", f"clamp(max($surprise * exp(-$dt / #surprise_tau) + {events}, 0.7 * $fear), 0, 1)"),
        ("$tension", "clamp($tension * exp(-$dt / #tension_tau) + #tension_gain * ($hurt_ev + $land_ev + $fire_ev + 0.5 * $water_ev + 0.3 * $gz_ev + $wake_ev), 0, 1)"),
        ("$fat_hp", "clamp((#fatigue_hp - $health) / #fatigue_hp, 0, 1)"),
        ("$fat_t", "max($fat_hp, if(dimension == 0 && between(day_time, 13000, 23000), #night_fatigue, 0))"),
        ("$fatigue", "$fatigue + ($fat_t - $fatigue) * (1 - exp(-$dt / #fatigue_tau))"),
        # only real exhaustion (low health) droops the lids; night fatigue just slows blinks
        ("$droop", "$droop + ($fat_hp - $droop) * (1 - exp(-$dt / #fatigue_tau))"),
        ("$sun", sun),
        ("$rain", "if(is_wet && !is_in_water, 1, 0)"),
        ("$heat", "if(dimension == -1, 1, 0)"),
        ("$sq_t", squint),
        ("$squint", "$squint + ($sq_t - $squint) * (1 - exp(-$dt * if($sq_t > $squint, #sq_k_up, #sq_k_down)))"),
        ("$widen", "$surprise * (1 - $squint)"),
        # dries while open, faster when wide/windy/tense/burning; wet under water
        ("$dryness", "if(?sub, 0, clamp($dryness + #dry_rate * (1 + #dry_widen * $widen + #dry_wind * $wind + #dry_tension * $tension + #dry_heat * $heat + if(is_burning, #dry_fire, 0)) * $dt * (1 - $blink_c), 0, 1.5))"),
        ("$flinch", "if(?tick, max($flinch * exp(-$dt / #flinch_tau), $hurt_ev), $flinch)"),
        ("$flinch_dir", "if($hurt_ev > 0, if($r10 < 0.5, -1, 1), $flinch_dir)"),
        # out of breath after sprinting, jumping and fighting; panting shows once they slow down
        ("$exert", "clamp($exert * exp(-$dt / #exert_tau) + #exert_sprint * $dt * if(is_sprinting, 1, 0) + #exert_jump * $jump_ev + #exert_swing * $swing_ev, 0, 1)"),
        ("$pant", "clamp(($exert - 0.2) / 0.6, 0, 1) * (1 - clamp(limb_speed * 2, 0, 1)) * if(?sub || ?asleep, 0, 1)"),
        ("$breath", "if(?tick, fmod($breath + $dt * (1.2 + 1.3 * $pant), 1), $breath)"),
        # body reactions: landing dip, shaking off water, effort on a swing
        ("$impact", "if(?tick, max($impact * exp(-$dt / #impact_tau), $land_ev), $impact)"),
        ("$shake_t", "if($surface_ev > 0, $t, $shake_t)"),
        ("$shake", "if($shake_t > 0 && $t - $shake_t < #shake_time, 1 - ($t - $shake_t) / #shake_time, 0)"),
        ("$wet", "if(?tick, max($wet * exp(-$dt), $surface_ev), $wet)"),
        ("$effort", "if(?tick, max($effort * exp(-$dt / #effort_tau), $swing_ev), $effort)"),
    ]]


def glances():
    """Idle glances once the player is fully idle; some come with a curious head tilt."""
    in_contact = " && !?contact_on" if CONTACT else ""
    mul = ("(1 + #sac_tension_gain * $tension) * if(is_sneaking, 1 + #sneak_glance, 1)"
           " * (1 - $drowsy) * (1 - $zoom) / (1 + $fatigue)")
    due = [
        # any input or other animation cancels a glance and keeps new ones from starting
        ("?sac_due", "?tick && ($t > $sac_end || (?active && ?sac_on))"),
        ("$sac_mul", mul),
        ("?sac_start", f"?sac_due && !?sac_on && !?active && !?follow{in_contact} && !?in_bed && $idle_t > #still_min && $r1 < #sac_prob * $sac_mul"),
    ]
    hold = "(#sac_hold_min + $r5 * (#sac_hold_max - #sac_hold_min)) / (1 + $tension)"
    rest = ("(#sac_rest_min + $r5 * (#sac_rest_max - #sac_rest_min)) * (1 + $fatigue)"
            " / ((1 + #sac_tension_gain * $tension) * if(is_sneaking, 1 + #sneak_glance, 1))")
    act = [
        ("$sac_end", f"if(?sac_start, $t + {hold}, ?sac_due && ?sac_on, $t + {rest}, ?sac_due, $t + 0.25, $sac_end)"),
        ("?sac_on", "?sac_start || (?sac_on && !?sac_due)"),
        ("$sac_y", "if(?sac_start, (#sac_yaw_min + $r2 * (#sac_yaw_max - #sac_yaw_min)) * if($r3 < 0.5, -1, 1), ?sac_on, $sac_y, 0)"),
        ("$sac_p", "if(?sac_start, #sac_pitch * (2 * $r4 - 1), ?sac_on, $sac_p, 0)"),
        ("$sac_blink_ev", "if(?sac_start && abs($sac_y) > #sac_blink_deg && $r6 < #sac_blink_prob, 1, 0)"),
        ("$tilt_t", "if(?sac_start, if($r13 < #tilt_prob, #tilt_deg * if($sac_y > 0, 1, -1), 0), ?sac_on, $tilt_t, 0)"),
        ("$tilt", "if(?tick, $tilt + ($tilt_t - $tilt) * (1 - exp(-$dt * #tilt_k)), $tilt)"),
    ]
    return [due, act]


def contact():
    """Other players' eyes meet yours when you face each other, then glance away."""
    aim = [
        ("$c_dx", "player_pos_x - pos_x"),
        ("$c_dz", "player_pos_z - pos_z"),
        ("$c_dy", "player_pos_y - pos_y"),
        # where the viewer is, relative to this player's look (deg)
        ("$c_rel_y", "wrapdeg(todeg(atan2(-$c_dx, $c_dz)) - todeg(rot_y) - head_yaw)"),
        ("$c_rel_p", "-todeg(atan2($c_dy, sqrt($c_dx * $c_dx + $c_dz * $c_dz))) - head_pitch"),
        # how directly the viewer is looking at this player (deg)
        ("$c_view", "wrapdeg(todeg(atan2($c_dx, -$c_dz)) - todeg(player_rot_y))"),
        ("?c_can", "?other && ?live && distance < #contact_dist && abs($c_rel_y) < #contact_cone && abs($c_rel_p) < 35 && abs($c_view) < #contact_view && !?asleep && !?in_bed && $drowsy < 0.5"),
    ]
    decide = [
        ("?c_start", "?tick && ?c_can && !?contact_on && $t > $c_next && $r14 < 1 - exp(-#contact_rate * $dt)"),
        ("?c_stop", "?contact_on && (!?c_can || $t > $c_end)"),
    ]
    run = [
        ("?contact_on", "?c_start || (?contact_on && !?c_stop)"),
        ("$c_end", "if(?c_start, $t + #contact_hold_min + $r15 * (#contact_hold_max - #contact_hold_min), $c_end)"),
        ("$c_next", "if(?c_stop, $t + #contact_gap_min + $r16 * (#contact_gap_max - #contact_gap_min), $c_next)"),
        # after holding your gaze, often a shy glance the other way
        ("$shy_end", "if(?c_stop && ?c_can && $r13 < #shy_prob, $t + #shy_time, $shy_end)"),
        ("$shy_dir", "if(?c_stop, if($c_rel_y > 0, -1, 1), $shy_dir)"),
        ("$c_ev", "if(?c_stop, 1, 0)"),
    ]
    return [aim, decide, run]


def eyes():
    """Eye-in-head angle: look direction minus the head actually rendered, plus attention offsets."""
    smooth = "if(?stale, {t}, ?tick, {v} + ({t} - {v}) * (1 - exp(-$dt * #pupil_k)), {v})"
    return [[
        ("$look_y", "if(?contact_on, clamp($c_rel_y, -20, 20), $t < $shy_end, #shy_deg * $shy_dir, $sac_y)" if CONTACT else "$sac_y"),
        ("$look_p", ("if(?contact_on, clamp($c_rel_p, -15, 15), $t < $shy_end, 3, $sac_p)" if CONTACT else "$sac_p") + " + #fear_look * $fear"),
        # under FA, read back the head it actually rendered last frame
        ("?fa_ok", f"!?standalone && ({FA_HEAD_YAW_OUT} != 0 || {FA_HEAD_PITCH_OUT} != 0)"),
        ("$rhy", f"if(?fa_ok, todeg({FA_HEAD_YAW_OUT}), $hy + $hx_y)"),
        ("$rhp", f"if(?fa_ok, todeg({FA_HEAD_PITCH_OUT}), $hp + $hx_p)"),
        ("$eye_y", "if(?live, head_yaw - $rhy + $look_y, 0)"),
        ("$eye_p", "if(?live, head_pitch - $rhp + $look_p, 0)"),
        # +yaw moves pupils toward smaller columns
        ("$oc", smooth.format(t="clamp(-$eye_y / #yaw_per_col, -1.5, 1.5)", v="$oc")),
        ("$or", smooth.format(t="clamp($eye_p / #pitch_per_row, -1.5, 1.5)", v="$or")),
    ]]


def blink():
    """Blinks are a hazard driven by dryness, tension and fatigue, plus reflexes."""
    slow = "(1 + {k} * #blink_fatigue_slow * max($fatigue, $drowsy))"
    rate = ("(#blink_base + #blink_dry * pow($dryness, 2) + #blink_tension * $tension + #blink_fatigue * $fatigue + 0.3 * $drowsy"
            " + #pant_blink * $pant + #wet_blink * $wet + #rain_blink * $rain)"
            " * if(?sub, #blink_water, 1) * (1 - #zoom_blink * $zoom)")
    reflex = ("$hurt_ev > 0 || $water_ev > 0 || $fire_ev > 0 || $land_ev > 0.2 || $wake_ev > 0 || $nod_ev > 0 || $surface_ev > 0"
              " || ($gz_ev > 0 && $r7 < #blink_gaze_prob) || $sac_blink_ev > 0"
              + (" || ($c_ev > 0 && $r9 < 0.4)" if CONTACT else ""))
    decide = [
        ("?b_was", "?blinking"),
        ("$b_close", f"#blink_close * {slow.format(k=1)}"),
        ("$b_open", f"#blink_open * {slow.format(k=1.3)}"),
        ("$b_rate", rate),
        ("?b_reflex", reflex),
        ("?b_follow_up", "$b_forced > 0 && $t >= $b_forced"),
        ("?b_start", "?tick && !?blinking && !?dead && !?asleep && !?in_bed && (?b_reflex || ?b_follow_up || ($t - $b_last_end > #blink_refractory && $r8 < 1 - exp(-$b_rate * $dt)))"),
    ]
    run = [
        ("$b_t0", "if(?b_start, $t, $b_t0)"),
        ("$b_dry0", "if(?b_start, $dryness, $b_dry0)"),
        ("?blinking", "?b_start || (?blinking && $t - $b_t0 < $b_close + #blink_hold + $b_open)"),
        ("$b_ph", "$t - $b_t0"),
        ("$blink_c", "if(?blinking, clamp(if($b_ph < $b_close, $b_ph / $b_close, $b_ph < $b_close + #blink_hold, 1, 1 - ($b_ph - $b_close - #blink_hold) / $b_open), 0, 1), 0)"),
    ]
    finish = [
        ("?b_end", "?b_was && !?blinking"),
        ("$b_last_end", "if(?b_end, $t, $b_last_end)"),
        # follow-up blink: sometimes, more often when dry, and in a burst while shaking off water
        ("$b_forced", "if(?b_start, -1, ?b_end && ($r9 < #double_blink_prob + #double_blink_dry * $b_dry0 || $wet > 0.5), $t + #double_blink_gap, $b_forced)"),
        ("$dryness", "if($blink_c > 0.9, 0, $dryness)"),
    ]
    return [decide, run, finish]


def face():
    smiles = ", #joy_lid * $joy, 0.5 * $yes" if GESTURES else ""
    return [[
        ("$lid_s", "clamp(#lid_fatigue * $droop + #lid_squint * $squint + #lid_down * clamp(($eye_p - #lid_down_deg) / 30, 0, 1)"
                   " + #pant_lid * $pant + #effort_squint * $effort - #lid_widen * $widen, 0, 0.9)"),
        ("$lid", f"if(?dead || ?in_bed, 1, max($blink_c, $lid_s, $doze_lid{smiles}, 0.8 * $impact, 0.85 * $yawn))"),
        ("$eye_sy", "1 + #widen_scale * $widen * (1 - $lid)"),
        ("$pupil_s", "1 - #pupil_shrink * $widen"),
        ("$lash_ty", "-#lash_lift * $widen * (1 - $lid)"),
        # head extras on top of the lagged look; FA lays the head itself in bed
        ("$hx_p", "if(?in_bed, 0, #sleep_head_deg * $sleep_head + #nod_deg * $nod - #flinch_deg * $flinch + #impact_deg * $impact + #effort_deg * $effort"
                  " + #pant_deg * $pant * sin($breath * 6.2832) - #yawn_deg * $yawn)"),
        ("$hx_r", "if(?in_bed, 0, $tilt + #flinch_roll * $flinch * $flinch_dir)"),
        ("$hx_y", "if(?in_bed, 0, #shake_deg * $shake * sin(($t - $shake_t) * 31.4))"),
    ]]


def brows():
    """Brows rise when startled or happy and furrow in pain, tension, focus, effort and on a head shake."""
    frown = ", 0.8 * $no" if GESTURES else ""
    smile = " - #joy_brow * max($joy, 0.5 * $yes)" if GESTURES else ""
    shake = [("$no", "if(?tick, max($no * exp(-$dt / #no_tau), $no_ev), $no)")] if GESTURES else []
    return [shake + [
        ("$pain", "clamp(hurt_time / 10, 0, 1)"),
        ("$focus", "max(if(is_using_item, 0.5, 0), $zoom)"),
        ("$furrow", f"clamp(max(#furrow_squint * $squint, #furrow_tension * $tension, #furrow_pain * $pain, #furrow_focus * $focus{frown}, 0.5 * $effort), 0, 1)"),
        ("$brow_ty", f"-#brow_lift * $widen * (1 - $furrow){smile} + #brow_drop * $furrow"),
        ("$brow_rz", "#brow_tilt * $furrow"),
    ]]


def logic():
    return (tunables() + inputs() + gaze() + (gestures() if GESTURES else []) + doze() + bed() + state() + glances() + (contact() if CONTACT else [])
            + eyes() + blink() + face() + (brows() if BROWS else []))


def fa_adapter():
    """Make FA's head follow our head instead of the raw look.

    FA builds its head inputs from the raw look: yaw/1.1 and 60*sin(pitch),
    plus extra motion such as look-speed swing and roll. We swap the raw look
    for our lagged head in that base mapping, add our head extras, and keep
    #fa_keep of FA's extra motion. FA recomputes these vars every frame, so
    nothing accumulates.
    """
    gate = "!?standalone && ?gate && !is_climbing"  # FA turns the head itself on ladders
    yaw = "torad(clamp({}, -90, 90) / 1.1)"
    pitch = "torad(60 * sin(torad({})))"
    return [[
        (FA_HEAD_YAW_IN, f"if({gate}, {yaw.format('$hy')} + torad($hx_y) + #fa_keep * ({FA_HEAD_YAW_IN} - {yaw.format('head_yaw')}), {FA_HEAD_YAW_IN})"),
        (FA_HEAD_PITCH_IN, f"if({gate}, {pitch.format('$hp')} + torad($hx_p) + #fa_keep * ({FA_HEAD_PITCH_IN} - {pitch.format('head_pitch')}), {FA_HEAD_PITCH_IN})"),
        (FA_HEAD_ROLL_IN, f"if({gate}, torad($hx_r) + #fa_keep * {FA_HEAD_ROLL_IN}, {FA_HEAD_ROLL_IN})"),
    ]]


def debug():
    """Log key values every 30 frames (EMF print/printb) for in-game diagnosis."""
    values = ["frame_counter", "age", "$dt", "head_yaw", "$hy", "head_pitch", "$hp", "$eye_y", "$oc", "$blink_c", FA_HEAD_YAW_IN, FA_HEAD_YAW_OUT]
    flags = ["?live", "?stale", "?tick", "?gate", "?follow", "?standalone", "?fa_ok"]
    return [[
        *((f"$dbg_v{i}", f"print({i}, 30, {v})") for i, v in enumerate(values, 1)),
        *((f"?dbg_b{i}", f"printb({100 + i}, 30, {b})") for i, b in enumerate(flags, 1)),
    ]]


def host_flag():
    return [[("?standalone", "true")]]


def host_head():
    """Standalone host: apply the head lag and head extras to the vanilla head."""
    gate = "?standalone && ?gate"
    return [[
        ("head.ry", f"head.ry + if({gate}, torad($hy + $hx_y - head_yaw), 0)"),
        ("head.rx", f"head.rx + if({gate}, torad($hp + $hx_p - head_pitch), 0)"),
        ("head.rz", f"head.rz + if({gate}, torad($hx_r), 0)"),
    ]]
