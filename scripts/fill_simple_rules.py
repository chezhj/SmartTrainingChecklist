"""
Fill auto_check_rule for items with simple (single-dataref) expressions that
still have null rules, plus a handful of special cases.

Run from repo root:
    python scripts/fill_simple_rules.py
"""
import json
from pathlib import Path

FIXTURE = Path("checklist/fixtures/checklist_content.json")


def leaf(dataref: str, op: str, value) -> dict:
    return {"dataref": dataref, "op": op, "value": value}


def eq(dataref: str, value) -> dict:
    return leaf(dataref, "eq", value)


def gt(dataref: str, value) -> dict:
    return leaf(dataref, "gt", value)


# Items whose dataref_expression can't be expressed by the current rule schema:
#   pk=52  : ">={laminar/B738/FMS/v2}"  — dynamic dataref comparison
#   pk=137 : "><0"                       — range syntax (between)
#   pk=221 : "{dataref}-N|{dataref}"     — dynamic CG tolerance band
UNSUPPORTED = {52, 137, 221}

RULES = {
    # ── Cockpit setup / before-start ────────────────────────────────────────
    1:   eq("laminar/b738/fmodpack/play_welcome_msg", 1),
    5:   eq("laminar/B738/door/flt_dk_door_ratio", 0),
    10:  eq("laminar/B738/FMS/trim_set", 1),
    11:  eq("sim/cockpit2/switches/yaw_damper_on", 0),
    12:  eq("laminar/B738/knobs/cross_feed", 0),
    14:  eq("laminar/B738/toggle_switch/cab_util_pos", 1),
    15:  eq("laminar/B738/toggle_switch/ife_pass_seat_pos", 1),
    16:  eq("laminar/B738/toggle_switch/eq_cool_supply", 0),
    17:  eq("laminar/B738/toggle_switch/eq_cool_exhaust", 0),
    19:  eq("sim/cockpit2/switches/wiper_speed", 0),
    25:  eq("laminar/B738/ice/wing_heat_pos", 0),

    # ── APU start sequence ───────────────────────────────────────────────────
    28:  eq("laminar/B738/spring_toggle_switch/APU_start_pos", 1),
    29:  eq("laminar/B738/spring_toggle_switch/APU_start_pos", 2),
    128: eq("laminar/B738/spring_toggle_switch/APU_start_pos", 0),

    # ── External power ───────────────────────────────────────────────────────
    33:  eq("laminar/B738/fmod/gpu_deployed", 0),

    # ── Air conditioning / pressurization ───────────────────────────────────
    35:  eq("laminar/B738/air/trim_air_pos", 1),
    42:  eq("laminar/B738/air/isolation_valve_pos", 2),
    47:  eq("laminar/B738/toggle_switch/air_valve_ctrl", 0),
    87:  gt("laminar/B738/air/l_pack_pos", 0),
    88:  eq("laminar/B738/air/isolation_valve_pos", 1),
    92:  eq("laminar/B738/toggle_switch/air_valve_ctrl", 0),
    93:  eq("laminar/B738/toggle_switch/bleed_air_apu_pos", 0),
    241: eq("laminar/B738/air/r_pack_pos", 1),
    242: eq("laminar/B738/air/isolation_valve_pos", 0),
    243: eq("laminar/B738/air/l_pack_pos", 1),
    244: eq("laminar/B738/toggle_switch/bleed_air_1_pos", 0),
    246: eq("laminar/B738/toggle_switch/bleed_air_2_pos", 0),
    248: eq("laminar/B738/toggle_switch/bleed_air_2_pos", 1),
    249: eq("laminar/B738/toggle_switch/bleed_air_apu_pos", 0),
    250: eq("laminar/B738/toggle_switch/bleed_air_1_pos", 1),
    251: gt("laminar/B738/air/l_pack_pos", 0),
    252: eq("laminar/B738/air/isolation_valve_pos", 1),
    253: gt("laminar/B738/air/r_pack_pos", 0),
    285: {"all": [
            eq("laminar/B738/air/l_pack_pos", 0),
            eq("laminar/B738/air/r_pack_pos", 0),
         ]},
    286: gt("laminar/B738/air/r_pack_pos", 0),

    # ── Autopilot / FMC ──────────────────────────────────────────────────────
    48:  eq("laminar/B738/autopilot/autothrottle_arm_pos", 1),
    49:  eq("laminar/B738/autopilot/flight_director_pos", 1),
    50:  eq("laminar/B738/autopilot/flight_director_fo_pos", 1),
    55:  eq("laminar/B738/autopilot/vnav_status1", 1),
    119: eq("laminar/B738/autopilot/pfd_spd_mode", 2),

    # ── Takeoff performance ───────────────────────────────────────────────────
    94:  eq("laminar/B738/FMS/takeoff_flaps_set", 1),
    206: gt("laminar/B738/FMS/fmc_gw_app", 0),
    220: gt("laminar/B738/FMS/takeoff_flaps", 0),
    289: eq("laminar/B738/FMS/takeoff_flaps_set", 1),

    # ── IRS ──────────────────────────────────────────────────────────────────
    157: eq("laminar/B738/toggle_switch/irs_dspl_sel", 4),

    # ── Transponder / clock ───────────────────────────────────────────────────
    75:  eq("laminar/B738/clock/captain/et_mode", 1),
    76:  eq("laminar/B738/knob/transponder_pos", 5),
    117: eq("laminar/B738/clock/captain/et_mode", 1),

    # ── Engine start ─────────────────────────────────────────────────────────
    78:  eq("laminar/B738/engine/starter2_pos", 0),
    82:  eq("laminar/B738/engine/starter2_pos", 1),
    83:  eq("laminar/B738/engine/starter1_pos", 0),
    84:  eq("laminar/B738/engine/mixture_ratio1", 1),
    247: eq("sim/cockpit/engine/APU_running", 1),
    254: eq("sim/cockpit/engine/APU_N1", 0),
    260: eq("laminar/B738/engine/starter2_pos", 0),
    261: eq("laminar/B738/engine/mixture_ratio2", 1),
    262: eq("laminar/B738/engine/starter1_pos", 0),
    263: eq("laminar/B738/engine/mixture_ratio2", 1),
    280: eq("laminar/B738/engine/starter1_pos", 1),
    281: eq("laminar/B738/engine/starter2_pos", 1),
    282: eq("laminar/B738/engine/starter1_pos", 1),
    284: eq("laminar/B738/engine/mixture_ratio2", 1),

    # ── Lights ───────────────────────────────────────────────────────────────
    95:  eq("laminar/B738/systems/lowerDU_page", 1),
    101: eq("laminar/B738/ice/wing_heat_pos", 0),
    108: eq("laminar/B738/toggle_switch/taxi_light_brightness_pos", 0),
    110: eq("sim/cockpit/switches/EFIS_shows_weather", 1),
    255: eq("laminar/B738/ice/wing_heat_pos", 1),
    275: eq("laminar/B738/ice/wing_heat_pos", 1),
    287: eq("sim/cockpit2/switches/generic_lights_switch[0]", 1),

    # ── Wing anti-ice ─────────────────────────────────────────────────────────
    256: {"all": [
            eq("laminar/B738/ice/eng1_heat_pos", 1),
            eq("laminar/B738/ice/eng2_heat_pos", 1),
         ]},  # pk 256 not in previous batch — already handled, kept as guard

    # ── Flaps ─────────────────────────────────────────────────────────────────
    257: eq("sim/cockpit2/controls/flap_ratio", 0),
    267: eq("sim/cockpit2/controls/flap_ratio", 0),
    276: eq("sim/cockpit2/controls/flap_ratio", 0),

    # ── GPWS / fire test ──────────────────────────────────────────────────────
    268: eq("laminar/B738/annunciator/gpws", 1),
    270: eq("laminar/B738/toggle_switch/extinguisher_circuit_test", -1),

    # ── Reverser / thrust ─────────────────────────────────────────────────────
    140: eq("laminar/B738/flt_ctrls/reverse_lever12", 0),

    # ── Heading bug  (value is −1 OR +1 when bug is active) ──────────────────
    278: {"any": [
            eq("laminar/B738/hud/hdg_bug_tape", -1),
            eq("laminar/B738/hud/hdg_bug_tape",  1),
         ]},

    # ── Parking brake ────────────────────────────────────────────────────────
    288: eq("sim/cockpit2/controls/parking_brake_ratio", 1),
    290: eq("sim/cockpit2/controls/parking_brake_ratio", 0),
    302: eq("sim/cockpit2/controls/parking_brake_ratio", 1),

    # ── Ground / cargo sounds ─────────────────────────────────────────────────
    132: eq("laminar/b738/fmodpack/fmod_play_cargo", 1),
    159: eq("laminar/b738/fmodpack/fmod_play_cargo", 0),
    160: eq("laminar/b738/fmodpack/fmod_start_leg", 1),
}


def main() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    updated = skipped_notnull = skipped_unsupported = not_found = 0

    for obj in data:
        if obj.get("model") != "checklist.checkitem":
            continue
        pk = obj["pk"]

        if pk in UNSUPPORTED:
            print(f"  SKIP pk={pk:4d}  (unsupported expression syntax)")
            skipped_unsupported += 1
            continue

        if pk not in RULES:
            continue

        fields = obj["fields"]
        if fields.get("auto_check_rule") is not None:
            print(f"  SKIP pk={pk:4d}  {fields['item']} — already has a rule")
            skipped_notnull += 1
            continue

        fields["auto_check_rule"] = RULES[pk]
        print(f"  SET  pk={pk:4d}  {fields['item']}")
        updated += 1

    for pk in RULES:
        if not any(
            o.get("model") == "checklist.checkitem" and o["pk"] == pk
            for o in data
        ):
            print(f"  WARN pk={pk} not found in fixture")
            not_found += 1

    FIXTURE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(
        f"\nDone: {updated} updated, {skipped_notnull} already set, "
        f"{skipped_unsupported} unsupported syntax, {not_found} PKs not found."
    )


if __name__ == "__main__":
    main()
