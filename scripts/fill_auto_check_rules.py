"""
One-shot script: fill auto_check_rule for all items that have a complex
dataref_expression (&&/||) but null auto_check_rule.

Run from repo root:
    python scripts/fill_auto_check_rules.py
"""
import json
from pathlib import Path

FIXTURE = Path("checklist/fixtures/checklist_content.json")

# pk → rule dict, translated faithfully from dataref_expression
RULES = {
    # ── pk 4  Doors (Closed — both entry annunciators off) ──────────────────
    4: {"all": [
        {"dataref": "laminar/B738/annunciator/aft_entry", "op": "eq", "value": 0},
        {"dataref": "laminar/B738/annunciator/fwd_entry", "op": "eq", "value": 0},
    ]},

    # ── pk 6  Center Fuel Pumps (ON) ────────────────────────────────────────
    6: {"all": [
        {"dataref": "laminar/B738/fuel/fuel_tank_pos_ctr1", "op": "eq", "value": 1},
        {"dataref": "laminar/B738/fuel/fuel_tank_pos_ctr2", "op": "eq", "value": 1},
    ]},

    # ── pk 7  Left & Right Fuel Pumps (ON) ──────────────────────────────────
    7: {"all": [
        {"dataref": "laminar/B738/fuel/fuel_tank_pos_lft1", "op": "eq", "value": 1},
        {"dataref": "laminar/B738/fuel/fuel_tank_pos_lft2", "op": "eq", "value": 1},
        {"dataref": "laminar/B738/fuel/fuel_tank_pos_rgt1", "op": "eq", "value": 1},
        {"dataref": "laminar/B738/fuel/fuel_tank_pos_rgt2", "op": "eq", "value": 1},
    ]},

    # ── pk 8  Electric Hydraulic Pumps (ON) ─────────────────────────────────
    8: {"all": [
        {"dataref": "laminar/B738/toggle_switch/electric_hydro_pumps1_pos", "op": "eq", "value": 1},
        {"dataref": "laminar/B738/toggle_switch/electric_hydro_pumps2_pos", "op": "eq", "value": 1},
    ]},

    # ── pk 13  Fuelpumps (all Off) ───────────────────────────────────────────
    13: {"all": [
        {"dataref": "laminar/B738/fuel/fuel_tank_pos_lft1", "op": "eq", "value": 0},
        {"dataref": "laminar/B738/fuel/fuel_tank_pos_lft2", "op": "eq", "value": 0},
        {"dataref": "laminar/B738/fuel/fuel_tank_pos_rgt1", "op": "eq", "value": 0},
        {"dataref": "laminar/B738/fuel/fuel_tank_pos_rgt2", "op": "eq", "value": 0},
        {"dataref": "laminar/B738/fuel/fuel_tank_pos_ctr1", "op": "eq", "value": 0},
        {"dataref": "laminar/B738/fuel/fuel_tank_pos_ctr2", "op": "eq", "value": 0},
    ]},

    # ── pk 22  Window heat switches (all ON) ─────────────────────────────────
    22: {"all": [
        {"dataref": "laminar/B738/ice/window_heat_l_side_pos", "op": "eq", "value": 1},
        {"dataref": "laminar/B738/ice/window_heat_l_fwd_pos",  "op": "eq", "value": 1},
        {"dataref": "laminar/B738/ice/window_heat_r_fwd_pos",  "op": "eq", "value": 1},
        {"dataref": "laminar/B738/ice/window_heat_r_side_pos", "op": "eq", "value": 1},
    ]},

    # ── pk 23  PROBE HEAT Switches (both OFF — security/power-down check) ───
    23: {"all": [
        {"dataref": "laminar/B738/toggle_switch/capt_probes_pos", "op": "eq", "value": 0},
        {"dataref": "laminar/B738/toggle_switch/fo_probes_pos",   "op": "eq", "value": 0},
    ]},

    # ── pk 26  Engine ANTI ICE (both OFF) ────────────────────────────────────
    26: {"all": [
        {"dataref": "laminar/B738/ice/eng1_heat_pos", "op": "eq", "value": 0},
        {"dataref": "laminar/B738/ice/eng2_heat_pos", "op": "eq", "value": 0},
    ]},

    # ── pk 27  Electric Hydraulic Pumps (both OFF, no failure)
    #          Original has rel_hydpmp_ele duplicated — deduplicated here ─────
    27: {"all": [
        {"dataref": "laminar/B738/toggle_switch/electric_hydro_pumps1_pos", "op": "eq", "value": 0},
        {"dataref": "laminar/B738/toggle_switch/electric_hydro_pumps2_pos", "op": "eq", "value": 0},
        {"dataref": "sim/operation/failures/rel_hydpmp_ele",                "op": "eq", "value": 0},
    ]},

    # ── pk 32  APU Generators (ON, both SOURCE OFF lights out)
    #          Original has source_off1x duplicated — deduplicated here ───────
    32: {"all": [
        {"dataref": "sim/cockpit2/electrical/APU_generator_on",     "op": "eq", "value": 1},
        {"dataref": "laminar/B738/annunciator/source_off1x",        "op": "eq", "value": 0},
        {"dataref": "laminar/B738/annunciator/source_off2x",        "op": "eq", "value": 0},
    ]},

    # ── pk 39  RECIRCULATION FAN (both ON) ───────────────────────────────────
    39: {"all": [
        {"dataref": "laminar/B738/air/l_recirc_fan_pos", "op": "eq", "value": 1},
        {"dataref": "laminar/B738/air/r_recirc_fan_pos", "op": "eq", "value": 1},
    ]},

    # ── pk 41  Pack Switches (both AUTO — value > 0) ─────────────────────────
    41: {"all": [
        {"dataref": "laminar/B738/air/l_pack_pos", "op": "gt", "value": 0},
        {"dataref": "laminar/B738/air/r_pack_pos", "op": "gt", "value": 0},
    ]},

    # ── pk 43  ENGINE BLEED Air (both ON, no failures) ───────────────────────
    43: {"all": [
        {"dataref": "laminar/B738/toggle_switch/bleed_air_1_pos",   "op": "eq", "value": 1},
        {"dataref": "laminar/B738/toggle_switch/bleed_air_2_pos",   "op": "eq", "value": 1},
        {"dataref": "sim/operation/failures/rel_bleed_air_lft",     "op": "eq", "value": 0},
        {"dataref": "sim/operation/failures/rel_bleed_air_rgt",     "op": "eq", "value": 0},
    ]},

    # ── pk 44  APU Bleed (ON, no failure) ────────────────────────────────────
    44: {"all": [
        {"dataref": "laminar/B738/toggle_switch/bleed_air_apu_pos", "op": "eq", "value": 1},
        {"dataref": "sim/operation/failures/rel_APU_press",         "op": "eq", "value": 0},
    ]},

    # ── pk 51  Autobrake (RTO armed, no brake failures) ──────────────────────
    51: {"all": [
        {"dataref": "laminar/B738/autobrake/autobrake_RTO_arm", "op": "eq", "value": 1},
        {"dataref": "sim/operation/failures/rel_lbrakes",       "op": "eq", "value": 0},
        {"dataref": "sim/operation/failures/rel_rbrakes",       "op": "eq", "value": 0},
    ]},

    # ── pk 56  LNAV (LNAV active OR HDG SEL active) ──────────────────────────
    56: {"any": [
        {"dataref": "laminar/B738/autopilot/lnav_status",    "op": "eq", "value": 1},
        {"dataref": "laminar/B738/autopilot/hdg_sel_status", "op": "eq", "value": 1},
    ]},

    # ── pk 85  Engine Generator 1 & 2 (both ON, no failures) ─────────────────
    85: {"all": [
        {"dataref": "sim/cockpit2/electrical/generator_on[0]",  "op": "eq", "value": 1},
        {"dataref": "sim/operation/failures/rel_genera0",        "op": "eq", "value": 0},
        {"dataref": "sim/cockpit2/electrical/generator_on[1]",  "op": "eq", "value": 1},
        {"dataref": "sim/operation/failures/rel_genera1",        "op": "eq", "value": 0},
    ]},

    # ── pk 86  Engine Start Switches (both CONT = 2) ──────────────────────────
    86: {"all": [
        {"dataref": "laminar/B738/engine/starter1_pos", "op": "eq", "value": 2},
        {"dataref": "laminar/B738/engine/starter2_pos", "op": "eq", "value": 2},
    ]},

    # ── pk 90  Probe Heat (both ON, no failures) ─────────────────────────────
    90: {"all": [
        {"dataref": "laminar/B738/toggle_switch/capt_probes_pos",       "op": "eq", "value": 1},
        {"dataref": "laminar/B738/toggle_switch/fo_probes_pos",         "op": "eq", "value": 1},
        {"dataref": "sim/operation/failures/rel_ice_pitot_heat1",       "op": "eq", "value": 0},
        {"dataref": "sim/operation/failures/rel_ice_pitot_heat2",       "op": "eq", "value": 0},
    ]},

    # ── pk 91  Air Conditioning Packs (both AUTO — value > 0) ────────────────
    91: {"all": [
        {"dataref": "laminar/B738/air/l_pack_pos", "op": "gt", "value": 0},
        {"dataref": "laminar/B738/air/r_pack_pos", "op": "gt", "value": 0},
    ]},

    # ── pk 102  Engine Anti-Ice (both OFF) ───────────────────────────────────
    102: {"all": [
        {"dataref": "laminar/B738/ice/eng1_heat_pos", "op": "eq", "value": 0},
        {"dataref": "laminar/B738/ice/eng2_heat_pos", "op": "eq", "value": 0},
    ]},

    # ── pk 107  Runway Turnoff Lights (both ON) ──────────────────────────────
    107: {"all": [
        {"dataref": "sim/cockpit2/switches/generic_lights_switch[2]", "op": "eq", "value": 1},
        {"dataref": "sim/cockpit2/switches/generic_lights_switch[3]", "op": "eq", "value": 1},
    ]},

    # ── pk 111  Terrain Radar FO (push-button OR toggle) ─────────────────────
    111: {"any": [
        {"dataref": "laminar/B738/EFIS_control/fo/push_button/terr", "op": "eq", "value": 1},
        {"dataref": "laminar/B738/EFIS_control/fo/terr_on",          "op": "eq", "value": 1},
    ]},

    # ── pk 112  Transponder (TA/RA = pos 5, no failure) ─────────────────────
    112: {"all": [
        {"dataref": "laminar/B738/knob/transponder_pos",    "op": "eq", "value": 5},
        {"dataref": "sim/operation/failures/rel_xpndr",     "op": "eq", "value": 0},
    ]},

    # ── pk 116  Landing Lights (ON — OR of LED-aircraft vs retractable-light variant)
    # Expression: (no_fail AND led=1 AND L=1 AND R=1) || (no_fail AND led=0 AND L=1 AND R=1 AND retL=2 AND retR=2)
    116: {"any": [
        {"all": [
            {"dataref": "sim/operation/failures/rel_lites_land",        "op": "eq", "value": 0},
            {"dataref": "laminar/B738/led_lights",                      "op": "eq", "value": 1},
            {"dataref": "laminar/B738/switch/land_lights_left_pos",     "op": "eq", "value": 1},
            {"dataref": "laminar/B738/switch/land_lights_right_pos",    "op": "eq", "value": 1},
        ]},
        {"all": [
            {"dataref": "sim/operation/failures/rel_lites_land",        "op": "eq", "value": 0},
            {"dataref": "laminar/B738/led_lights",                      "op": "eq", "value": 0},
            {"dataref": "laminar/B738/switch/land_lights_left_pos",     "op": "eq", "value": 1},
            {"dataref": "laminar/B738/switch/land_lights_right_pos",    "op": "eq", "value": 1},
            {"dataref": "laminar/B738/switch/land_lights_ret_left_pos", "op": "eq", "value": 2},
            {"dataref": "laminar/B738/switch/land_lights_ret_right_pos","op": "eq", "value": 2},
        ]},
    ]},

    # ── pk 118  Thrust Levers (both engines N1 > 40 %) ───────────────────────
    118: {"all": [
        {"dataref": "sim/flightmodel/engine/ENGN_N1_[0]", "op": "gt", "value": 40},
        {"dataref": "sim/flightmodel/engine/ENGN_N1_[1]", "op": "gt", "value": 40},
    ]},

    # ── pk 125  Flaps retracted (ratio 0, no failure) ────────────────────────
    125: {"all": [
        {"dataref": "sim/cockpit2/controls/flap_ratio",         "op": "eq", "value": 0},
        {"dataref": "sim/operation/failures/rel_flap_act",      "op": "eq", "value": 0},
    ]},

    # ── pk 129  Recall (all six-pack annunciator panels illuminated > 0 during test)
    # Note: six_pack_doors appears twice in the original — deduplicated here ──
    129: {"all": [
        {"dataref": "laminar/B738/annunciator/six_pack_fuel",     "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/six_pack_fire",     "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/six_pack_apu",      "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/six_pack_flt_cont", "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/six_pack_elec",     "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/six_pack_irs",      "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/six_pack_ice",      "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/six_pack_doors",    "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/six_pack_eng",      "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/six_pack_hyd",      "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/six_pack_air_cond", "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/six_pack_overhead", "op": "gt", "value": 0},
    ]},

    # ── pk 130  Doors (at least one door open — OR) ───────────────────────────
    130: {"any": [
        {"dataref": "737u/doors/aft_Cargo", "op": "eq", "value": 1},
        {"dataref": "737u/doors/Fwd_Cargo", "op": "eq", "value": 1},
        {"dataref": "737u/doors/L1",        "op": "eq", "value": 1},
    ]},

    # ── pk 134  Ground Power (GPU deployed OR gpu_amps > 0 with no failure)
    # Standard precedence: && binds tighter than || ───────────────────────────
    134: {"any": [
        {"dataref": "laminar/B738/fmod/gpu_deployed",           "op": "eq", "value": 1},
        {"all": [
            {"dataref": "sim/cockpit/electrical/gpu_amps",      "op": "gt", "value": 0},
            {"dataref": "sim/operation/failures/rel_ex_power_on","op": "eq", "value": 0},
        ]},
    ]},

    # ── pk 139  Fuel CUT OFF switches (either engine cut off) ────────────────
    139: {"any": [
        {"dataref": "laminar/B738/engine/mixture_ratio1", "op": "eq", "value": 0},
        {"dataref": "laminar/B738/engine/mixture_ratio2", "op": "eq", "value": 0},
    ]},

    # ── pk 142  Thrust Levers (both at idle) ─────────────────────────────────
    142: {"all": [
        {"dataref": "laminar/B738/engine/thrust1_leveler", "op": "eq", "value": 0},
        {"dataref": "laminar/B738/engine/thrust2_leveler", "op": "eq", "value": 0},
    ]},

    # ── pk 146  Standby Power (battery on, cover closed, no failure) ─────────
    146: {"all": [
        {"dataref": "sim/cockpit2/electrical/battery_on[0]",        "op": "eq", "value": 1},
        {"dataref": "laminar/B738/button_switch/cover_position[3]", "op": "eq", "value": 0},
        {"dataref": "sim/operation/failures/rel_batter1",           "op": "eq", "value": 0},
    ]},

    # ── pk 147  Generators Drive Disconnect (both guards closed, both switches normal) ──
    147: {"all": [
        {"dataref": "laminar/B738/one_way_switch/drive_disconnect1_pos",    "op": "eq", "value": 0},
        {"dataref": "laminar/B738/one_way_switch/drive_disconnect2_pos",    "op": "eq", "value": 0},
        {"dataref": "laminar/B738/button_switch/cover_position[4]",         "op": "eq", "value": 0},
        {"dataref": "laminar/B738/button_switch/cover_position[5]",         "op": "eq", "value": 0},
    ]},

    # ── pk 148  Bus Transfer Switch (AUTO, guard closed) ─────────────────────
    148: {"all": [
        {"dataref": "sim/cockpit2/electrical/cross_tie",                "op": "eq", "value": 1},
        {"dataref": "laminar/B738/button_switch/cover_position[6]",    "op": "eq", "value": 0},
    ]},

    # ── pk 149  Ground Power Switch (gpu_amps > 0, no failure) ───────────────
    149: {"all": [
        {"dataref": "sim/cockpit/electrical/gpu_amps",          "op": "gt", "value": 0},
        {"dataref": "sim/operation/failures/rel_ex_power_on",   "op": "eq", "value": 0},
    ]},

    # ── pk 150  Emergency Light Switch (ARM, guard closed) ───────────────────
    150: {"all": [
        {"dataref": "laminar/B738/toggle_switch/emer_exit_lights",      "op": "eq", "value": 1},
        {"dataref": "laminar/B738/button_switch/cover_position[9]",     "op": "eq", "value": 0},
    ]},

    # ── pk 151  Position Lights (NAV on, strobe off — parking / before eng start) ──
    151: {"all": [
        {"dataref": "sim/cockpit2/switches/navigation_lights_on",   "op": "eq", "value": 1},
        {"dataref": "sim/cockpit2/switches/strobe_lights_on",       "op": "eq", "value": 0},
        {"dataref": "sim/operation/failures/rel_lites_nav",         "op": "eq", "value": 0},
    ]},

    # ── pk 152  Logo Lights (logo light switch on)
    # Original has malformed double-colon tokens for hyd pumps — only the
    # meaningful generic_lights_switch[1] datarefs are used here ─────────────
    152: {"dataref": "sim/cockpit2/switches/generic_lights_switch[1]", "op": "eq", "value": 1},

    # ── pk 154  Wheel Well light (any of the three relevant light switches on)
    # Malformed double-colon hyd-pump tokens stripped from original ───────────
    154: {"any": [
        {"dataref": "sim/cockpit2/switches/generic_lights_switch[5]", "op": "eq", "value": 1},
        {"dataref": "sim/cockpit2/switches/generic_lights_switch[0]", "op": "eq", "value": 1},
        {"dataref": "sim/cockpit2/switches/generic_lights_switch[1]", "op": "eq", "value": 1},
    ]},

    # ── pk 155  Thrust Levers (both N1 > 40 % AND takeoff config annunciator) ──
    155: {"all": [
        {"dataref": "sim/flightmodel/engine/ENGN_N1_[0]",          "op": "gt", "value": 40},
        {"dataref": "laminar/B738/annunciator/takeoff_config",      "op": "eq", "value": 1},
        {"dataref": "sim/flightmodel/engine/ENGN_N1_[1]",          "op": "gt", "value": 40},
    ]},

    # ── pk 156  IRS Mode Selector (both NAV = 2) ─────────────────────────────
    156: {"all": [
        {"dataref": "laminar/B738/toggle_switch/irs_left",  "op": "eq", "value": 2},
        {"dataref": "laminar/B738/toggle_switch/irs_right", "op": "eq", "value": 2},
    ]},

    # ── pk 225  Enter V1/Vr/V2 (all speeds set > 0) ──────────────────────────
    225: {"all": [
        {"dataref": "laminar/B738/FMS/v1_set", "op": "gt", "value": 0},
        {"dataref": "laminar/B738/FMS/vr_set", "op": "gt", "value": 0},
        {"dataref": "laminar/B738/FMS/v2_set", "op": "gt", "value": 0},
    ]},

    # ── pk 245  APU Bleed Switch (APU running AND bleed on) ──────────────────
    245: {"all": [
        {"dataref": "sim/cockpit/engine/APU_running",               "op": "eq", "value": 1},
        {"dataref": "laminar/B738/toggle_switch/bleed_air_apu_pos", "op": "eq", "value": 1},
    ]},

    # ── pk 256  Engine Anti-Ice (both ON) ────────────────────────────────────
    256: {"all": [
        {"dataref": "laminar/B738/ice/eng1_heat_pos", "op": "eq", "value": 1},
        {"dataref": "laminar/B738/ice/eng2_heat_pos", "op": "eq", "value": 1},
    ]},

    # ── pk 264  Engine generators (both ON, no failures) ─────────────────────
    264: {"all": [
        {"dataref": "sim/cockpit2/electrical/generator_on[0]",  "op": "eq", "value": 1},
        {"dataref": "sim/operation/failures/rel_genera0",        "op": "eq", "value": 0},
        {"dataref": "sim/cockpit2/electrical/generator_on[1]",  "op": "eq", "value": 1},
        {"dataref": "sim/operation/failures/rel_genera1",        "op": "eq", "value": 0},
    ]},

    # ── pk 269  APU & Engine Fire test (test button pressed AND annunciators lit) ──
    269: {"all": [
        {"dataref": "laminar/B738/push_botton/cargo_fire_test",     "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/cargo_fire",          "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/fire_bell_annun",     "op": "eq", "value": 1},
    ]},

    # ── pk 271  Cargo Fire test (same as 269) ────────────────────────────────
    271: {"all": [
        {"dataref": "laminar/B738/push_botton/cargo_fire_test",     "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/cargo_fire",          "op": "gt", "value": 0},
        {"dataref": "laminar/B738/annunciator/fire_bell_annun",     "op": "eq", "value": 1},
    ]},

    # ── pk 274  Engine Anti Ice (both ON) ────────────────────────────────────
    274: {"all": [
        {"dataref": "laminar/B738/ice/eng1_heat_pos", "op": "eq", "value": 1},
        {"dataref": "laminar/B738/ice/eng2_heat_pos", "op": "eq", "value": 1},
    ]},

    # ── pk 285  Left & Right Pack (both OFF) ─────────────────────────────────
    285: {"all": [
        {"dataref": "laminar/B738/air/l_pack_pos", "op": "eq", "value": 0},
        {"dataref": "laminar/B738/air/r_pack_pos", "op": "eq", "value": 0},
    ]},
}


def main() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))

    updated = 0
    skipped_notnull = 0
    skipped_notfound = 0

    for obj in data:
        if obj.get("model") != "checklist.checkitem":
            continue
        pk = obj["pk"]
        if pk not in RULES:
            continue
        fields = obj["fields"]
        if fields.get("auto_check_rule") is not None:
            print(f"  SKIP pk={pk} — already has a rule")
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
            skipped_notfound += 1

    FIXTURE.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nDone: {updated} updated, {skipped_notnull} skipped (already set), "
          f"{skipped_notfound} PKs not found.")


if __name__ == "__main__":
    main()
