"""Project identity and every tunable constant.

Tunables are emitted as the first animation block of player_face.jpm
(`var.le_k_<name>`), so players can tweak them without rebuilding.
"""

NAME = "Lively Eyes"
VERSION = "0.1.1"
AUTHOR = "Tokid"
PREFIX = "le_"
# Tested on Minecraft 26.1.2 with EMF 3.3.11, which also ships for 1.21.11.
# Resource pack format 75 is 1.21.11, 84 is 26.1 to 26.1.2; the pack declares the range.
GAME_VERSIONS = "1.21.11, 26.1–26.1.2"
MIN_FORMAT = 75
MAX_FORMAT = 84

# Sign of a pupil mover's tx/ty per +1 face column/row. Derived from how CEM
# inverts x/y; flip here if pupils move the wrong way in game.
TX_SIGN = 1
TY_SIGN = 1
# Rotation sign that lowers the inner end of the right brow (left brow uses the opposite).
BROW_RZ_SIGN = 1

# Close the eyes in bed by reading the SleepingX NBT tag with EMF's nbt().
# If EMF ever rejects that expression it drops the whole animation set,
# so this can be switched off on its own.
BED_NBT = True

# Brows (Fresh Moves brow slots), plus what only shows through them: furrow from
# pain, tension, focus and effort, and the head-shake frown. Left out of the
# first release; the code stays and comes back with this switch.
BROWS = False
# Gesture faces: crouch spam (happy ^^), nodding (smile), head shake (frown).
# Without brows they only half-close the eyes, so they wait for brows.
GESTURES = False
# Eye contact: other players look back at you when you face each other.
# Left out of the first release until there's a better use for it.
CONTACT = False
# Draw brows in front of the hair (hat) layer, anime style, so bangs don't hide
# them. Off puts them back on the face, where hair covers them.
BROWS_OVER_HAIR = True

# (name, value, comment)
TUNABLES = [
    # gaze: eyes lead, head follows
    ("deadzone", 12, "gaze shift (deg) the eyes alone absorb"),
    ("speed_trigger", 120, "gaze speed (deg/s) that pulls the head in"),
    ("head_k", 10, "head catch-up responsiveness (1/s)"),
    ("head_maxv", 400, "head max angular speed (deg/s)"),
    ("drift_k", 0.2, "slow head re-centering while eyes are off-center (1/s)"),
    ("vel_k", 25, "gaze speed smoothing (1/s)"),
    ("gaze_event_deg", 25, "head-follow shift that counts as a startle/blink cue (deg)"),
    ("fa_keep", 0, "share of Fresh Animations' own extra head motion (look-speed swing) to keep; 0 = head follows Lively Eyes only"),
    # pupils
    ("yaw_per_col", 15, "eye yaw (deg) per one column of pupil travel"),
    ("pitch_per_row", 15, "eye pitch (deg) per one row of pupil travel"),
    ("pupil_k", 25, "pupil smoothing (1/s)"),
    ("pupil_over_k", 0.35, "share of gaze a pupil keeps following past its eye edge"),
    ("pupil_over_max", 0.4, "how far a pupil may go past its eye edge (px)"),
    ("pupil_over_k_v", 0.3, "same as pupil_over_k for up/down; most eyes have no vertical room"),
    ("pupil_over_max_v", 0.35, "same as pupil_over_max for up/down (px)"),
    # idle glances
    ("active_vel", 3, "look speed (deg/s) that counts as input; any input stops idle glances and dozing"),
    ("still_min", 1.2, "seconds fully idle before glances start"),
    ("sac_prob", 0.7, "chance to glance when a glance is due"),
    ("sac_yaw_min", 8, "glance yaw min (deg)"),
    ("sac_yaw_max", 16, "glance yaw max (deg)"),
    ("sac_pitch", 5, "glance pitch range (deg)"),
    ("sac_hold_min", 0.3, "glance hold min (s)"),
    ("sac_hold_max", 1.4, "glance hold max (s)"),
    ("sac_rest_min", 1.0, "rest between glances min (s)"),
    ("sac_rest_max", 3.5, "rest between glances max (s)"),
    ("sac_tension_gain", 1.5, "how much tension speeds up glancing"),
    ("sac_blink_deg", 12, "glances wider than this may carry a blink (deg)"),
    ("sac_blink_prob", 0.3, "chance a wide glance carries a blink"),
    # events
    ("land_speed_min", 9, "fall speed (blocks/s) that starts to startle on landing"),
    ("land_speed_span", 14, "fall speed range over which landing startle ramps to full"),
    ("submerge_depth", 0, "how far the eyes must be below the top of the water to count as under (blocks); 0 = Minecraft's own check"),
    ("sub_settle", 0.15, "head must stay under (or out) this long before it counts (s)"),
    ("surface_min_under", 3, "shake off water only after the head was under at least this long (s)"),
    ("dive_min_out", 2, "react to going under only after the head was out at least this long (s)"),
    # state
    ("surprise_tau", 1.2, "surprise decay time constant (s)"),
    ("ev_hurt_s", 0.9, "surprise from getting hit"),
    ("ev_land_s", 0.7, "surprise from a hard landing (at full intensity)"),
    ("ev_water_s", 0.4, "surprise from going under water"),
    ("ev_fire_s", 0.7, "surprise from catching fire"),
    ("ev_gaze_s", 0.2, "surprise from a big sudden gaze shift"),
    ("tension_tau", 20, "tension decay time constant (s)"),
    ("tension_gain", 0.22, "tension added per startling event"),
    ("fatigue_hp", 0.5, "health fraction below which fatigue sets in"),
    ("night_fatigue", 0.25, "fatigue while awake at night in the overworld"),
    ("fatigue_tau", 4, "fatigue follow time constant (s)"),
    ("sq_water", 0.55, "squint under water"),
    ("sq_fire", 0.6, "squint while burning"),
    ("sq_wind", 0.35, "squint at full wind (gliding)"),
    ("sq_k_up", 8, "squint onset speed (1/s)"),
    ("sq_k_down", 2, "squint release speed (1/s)"),
    ("dry_rate", 0.12, "dryness gained per second with eyes open"),
    ("dry_widen", 2.0, "extra drying from wide eyes"),
    ("dry_wind", 1.0, "extra drying from wind"),
    ("dry_fire", 1.5, "extra drying from fire"),
    ("dry_tension", 0.8, "extra drying while tense (nervous eyes)"),
    # blink
    ("blink_base", 0.12, "base blink rate (1/s)"),
    ("blink_dry", 1.0, "blink rate per dryness^2 (1/s)"),
    ("blink_tension", 1.0, "blink rate per tension (1/s)"),
    ("blink_fatigue", 0.25, "blink rate per fatigue (1/s)"),
    ("blink_water", 0.2, "blink rate multiplier under water"),
    ("blink_close", 0.07, "lid closing time (s)"),
    ("blink_hold", 0.03, "lid fully closed time (s)"),
    ("blink_open", 0.11, "lid opening time (s)"),
    ("blink_fatigue_slow", 0.8, "how much fatigue slows blinks"),
    ("blink_refractory", 0.3, "min gap after a blink before a spontaneous one (s)"),
    ("double_blink_prob", 0.12, "chance of a follow-up blink"),
    ("double_blink_dry", 0.3, "extra follow-up chance per dryness at blink start"),
    ("double_blink_gap", 0.12, "delay before the follow-up blink (s)"),
    ("blink_gaze_prob", 0.5, "chance a big head-follow shift carries a blink"),
    # dozing off when left alone
    ("doze_start", 45, "idle seconds before drowsiness starts"),
    ("doze_ramp", 45, "seconds from first drowsiness to fully drowsy"),
    ("sleep_start", 150, "idle seconds before falling asleep"),
    ("doze_lid", 0.55, "lid droop when fully drowsy"),
    ("sleep_head_deg", 12, "head droop while asleep (deg)"),
    ("nod_min", 0.4, "drowsiness before nodding off starts"),
    ("nod_deg", 22, "head drop of a full nod (deg)"),
    ("nod_drop_time", 2.5, "seconds for the head to sink in a nod"),
    ("nod_gap_min", 2, "rest between nods min (s)"),
    ("nod_gap_max", 6, "rest between nods max (s)"),
    ("nod_recover_k", 10, "jerk-up speed after a nod (1/s)"),
    ("ev_nod_s", 0.3, "surprise from jerking awake after a nod"),
    ("ev_wake_s", 0.6, "surprise when woken"),
    # head reactions
    ("flinch_deg", 12, "head snaps back on a hit (deg)"),
    ("flinch_roll", 6, "head roll on a hit (deg)"),
    ("flinch_tau", 0.2, "flinch recovery time constant (s)"),
    ("tilt_prob", 0, "chance an idle glance comes with a curious head tilt (0 = off: glances move only the eyes)"),
    ("tilt_deg", 8, "curious head tilt (deg)"),
    ("tilt_k", 4, "tilt speed (1/s)"),
    ("sun_pitch", 35, "looking up steeper than this in daylight starts sun glare (deg)"),
    ("sq_sun", 0.6, "squint from sun glare"),
    ("sneak_glance", 1.5, "extra glancing while sneaking"),
    ("sq_sneak", 0.15, "squint while sneaking"),
    ("fear_speed", 12, "fall speed (blocks/s) where fall fear starts"),
    ("fear_look", 10, "eyes look down while falling (deg)"),
    ("sq_zoom", 0.5, "squint while zooming (needs Lively Eyes Bridge)"),
    ("zoom_blink", 0.6, "blink reduction while zooming"),
    # out of breath
    ("exert_sprint", 0.08, "exertion per second of sprinting"),
    ("exert_jump", 0.04, "exertion per jump"),
    ("exert_swing", 0.03, "exertion per attack swing"),
    ("exert_tau", 8, "recovery time constant (s)"),
    ("pant_deg", 3, "head bob of heavy breathing (deg)"),
    ("pant_lid", 0.3, "lid droop when out of breath"),
    ("pant_blink", 0.5, "extra blinks per second when out of breath"),
    # body reactions
    ("impact_deg", 10, "head dip on a hard landing (deg)"),
    ("impact_tau", 0.18, "landing dip recovery (s)"),
    ("shake_deg", 12, "head shake when coming out of water (deg)"),
    ("shake_time", 0.7, "head shake duration (s)"),
    ("wet_blink", 3, "extra blinks per second right after surfacing"),
    ("effort_deg", 4, "head push on an attack swing (deg)"),
    ("effort_squint", 0.35, "squint on an attack swing"),
    ("effort_tau", 0.25, "attack effort fade (s)"),
    # weather and places
    ("sq_rain", 0.25, "squint in rain"),
    ("rain_blink", 0.4, "extra blinks per second in rain"),
    ("sq_heat", 0.2, "squint in the Nether heat"),
    ("dry_heat", 1.0, "extra drying in the Nether"),
    # yawning when drowsy
    ("yawn_rate", 0.08, "yawns per second when fully drowsy (0 = off)"),
    ("yawn_time", 2.2, "yawn duration (s)"),
    ("yawn_deg", 12, "head tips back during a yawn (deg)"),
    # bed
    ("bed_check_frames", 20, "frames between bed checks while idle (reading NBT is not free)"),
    # face
    ("lid_fatigue", 0.4, "lid droop at full low-health fatigue"),
    ("lid_squint", 0.55, "lid droop at full squint"),
    ("lid_down", 0.3, "upper lid follows eyes looking down"),
    ("lid_down_deg", 8, "downward eye angle (deg) before the lid starts to follow"),
    ("lid_widen", 0.6, "lid lift from wide eyes"),
    ("widen_scale", 0.4, "eye height gain at full widen"),
    ("pupil_shrink", 0.3, "pupil shrink at full widen"),
    ("lash_lift", 0.35, "eyelash lift at full widen (px)"),
]

# Emitted only when CONTACT is on.
CONTACT_TUNABLES = [
    ("contact_dist", 6, "max distance for eye contact (blocks)"),
    ("contact_cone", 40, "how far off their look the viewer can be and still be noticed (deg)"),
    ("contact_view", 25, "how directly the viewer must look at them (deg)"),
    ("contact_rate", 0.8, "chance per second to meet the viewer's eyes when possible"),
    ("contact_hold_min", 0.7, "eye contact hold min (s)"),
    ("contact_hold_max", 1.6, "eye contact hold max (s)"),
    ("contact_gap_min", 3, "cooldown between eye contacts min (s)"),
    ("contact_gap_max", 8, "cooldown between eye contacts max (s)"),
    ("shy_prob", 0.5, "chance to glance away after eye contact"),
    ("shy_deg", 10, "how far the shy glance goes (deg)"),
    ("shy_time", 0.5, "shy glance duration (s)"),
]

# Emitted only when GESTURES is on.
GESTURE_TUNABLES = [
    ("gesture_sneak_count", 3, "crouch toggles in quick succession that read as a greeting"),
    ("gesture_sneak_tau", 1.0, "how fast crouch toggles are forgotten (s)"),
    ("gesture_nod_speed", 40, "head pitch speed (deg/s) a nod swing must reach"),
    ("gesture_shake_speed", 60, "head yaw speed (deg/s) a head-shake swing must reach"),
    ("gesture_swing_tau", 0.8, "how fast nod/shake swings are forgotten (s)"),
    ("gesture_nod_count", 2.4, "recent nod swings (decayed count) that read as yes (about 3-4 swings)"),
    ("gesture_shake_count", 3.0, "recent head-shake swings (decayed count) that read as no (about 5 swings)"),
    ("joy_tau", 1.5, "how long the happy (^^) face lasts (s)"),
    ("joy_lid", 0.65, "lid closure of the happy face"),
    ("yes_tau", 0.8, "how long the nod smile lasts (s)"),
]

# Emitted only when BROWS is on.
BROW_TUNABLES = [
    ("brow_lift", 1.0, "brow raise at full surprise (px)"),
    ("brow_drop", 0.5, "brow drop at full furrow (px)"),
    ("brow_tilt", 10, "brow inner-end tilt at full furrow (deg)"),
    ("joy_brow", 0.6, "brow raise of the happy face (px)"),
    ("furrow_squint", 0.6, "furrow from squinting"),
    ("furrow_tension", 0.4, "furrow from tension"),
    ("furrow_pain", 0.9, "furrow right after a hit"),
    ("furrow_focus", 0.6, "furrow while aiming/using an item or zooming"),
    ("no_tau", 1.2, "how long the head-shake frown lasts (s)"),
]
