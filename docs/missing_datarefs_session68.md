# Missing datarefs in auto_check_rule (session_68)

Datarefs referenced in `auto_check_rule` that were **never seen in `logs/session_68.jsonl`** — the plugin never sent them, so those rules can never fire.

30 datarefs affect 40 check items.

---

## Probably wrong / non-existent datarefs

These look most likely to be typos or datarefs that don't exist in the zibo/laminar plugin.

### `laminar/B738/knobs/cross_feed`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 12 | Preflight Procedure | Fuel CROSSFEED Selector | Closed | `eq 0` |

### `laminar/B738/toggle_switch/cab_util_pos`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 14 | Preflight Procedure | CAB / UTIL Power Switch | On | `eq 1` |

### `laminar/B738/toggle_switch/ife_pass_seat_pos`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 15 | Preflight Procedure | IFE / PASS Seat Power Switch | On | `eq 1` |

### `laminar/B738/toggle_switch/eq_cool_supply`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 16 | Preflight Procedure | EQUIP COOLING - SUPPLY Switch | Normal | `eq 0` |

### `laminar/B738/toggle_switch/eq_cool_exhaust`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 17 | Preflight Procedure | EQUIP COOLING EXHAUST - Switch | Normal | `eq 0` |

### `sim/cockpit2/switches/wiper_speed`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 19 | Preflight Procedure | Left & Right Wiper Switches | Off | `eq 0` |

### `laminar/B738/push_button/tat_test_pos`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 24 | Preflight Procedure | TAT Test | Press and hold 5 seconds, check no alarm | `gt 1` |

### `laminar/B738/ice/wing_heat_pos`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 25 | Preflight Procedure | Wing ANTI ICE | Off | `eq 0` |
| 101 | Before Taxi Procedure | Wing Anti-Ice | OFF | `eq 0` |
| 255 | Before Taxi Procedure | Wing Anti-Ice | ON | `eq 1` |
| 275 | Before Taxi Procedure | Wing Anti Ice | ON | `eq 1` |

### `laminar/B738/push_button/duct_ovht_test_pos`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 40 | Preflight Procedure | OVHT TEST | Press and hold 5 Seconds, Wing-Body OVERHEAD Light Illuminates | `eq 1` |

### `laminar/B738/toggle_switch/air_valve_ctrl`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 47 | Preflight Procedure | Pressurization Sellector | Auto | `eq 0` |
| 92 | Before Taxi Procedure | Pressurization Selector | Verify AUTO | `eq 0` |

### `sim/cockpit/electrical/landing_lights_on`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 106 | Before Takeoff Procedure | Landing Lights | ON (When Cleared) | `eq 1` |

Note: the legacy `dataref_expression` uses `laminar/B738/led_lights` + retractable light positions — the rule dataref is a different (likely obsolete) path.

### `sim/cockpit/switches/EFIS_shows_weather`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 110 | Before Takeoff Procedure | Weather Radar | On | `eq 1` |

### `laminar/B738/toggle_switch/wheel_light`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 154 | Flight Deck Preparation | Wheel Well light switch | As Required | `eq 1` |

### `laminar/B738/annunciator/gpws`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 268 | Flight Deck Preparation | GPWS / Windshear Configuration | Press "SYS TEST" (hold for long test) | `eq 1` |

### `laminar/B738/toggle_switch/extinguisher_circuit_test`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 270 | Flight Deck Preparation | APU & Engine Extinguisher test 1 & 2 | Completed | `eq -1` |

Note: value `-1` is also suspicious — toggle switches typically use 0/1/2.

### `sim/cockpit2/controls/parking_brake_ratio`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 288 | Before Takeoff Procedure | Parking break | ON (RWY Hold) | `eq 1` |
| 290 | Before Takeoff Procedure | Parking Brake | OFF | `eq 0` |
| 302 | Before Takeoff Procedure | Parking Break | ON | `eq 1` |

### `sim/cockpit2/switches/generic_lights_switch[0]`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 287 | Before Takeoff Procedure | Wing lights | ON (Signal departure) | `eq 1` |

---

## Probably missing from plugin subscription list

These look like plausible/correct dataref names — they are likely just not subscribed by the plugin yet.

### `laminar/B738/airstairs_hide`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 131 | Aircraft Preparation (EFB) | Airstairs | As Required | `eq 0` |

### `laminar/B738/flt_ctrls/reverse_lever12`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 140 | Flight Deck Preparation | Reverse thrust levers | Down | `eq 0` |

### `laminar/B738/flt_ctrls/speedbrake_lever_pos`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 141 | Flight Deck Preparation | Speed Brake | Down | `eq 0` |

Note: legacy `dataref_expression` uses `sim/cockpit2/controls/speedbrake_ratio` — may be the correct path.

### `laminar/B738/flt_ctrls/flap_lever`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 143 | Flight Deck Preparation | Flaps | Up | `eq 0.0` |

Note: legacy `dataref_expression` uses `sim/cockpit2/controls/flap_ratio` — may be the correct path.

### `laminar/B738/FMS/fmc_trans_alt`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 212 | CDU Preflight Procedure | Trans Alt | Verify with departure airport | `gt 0` |

### `laminar/B738/FMS/to_n1`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 217 | CDU Preflight Procedure | Take Off thrust (TO) | set based on calculations | `gt 0` |

### `laminar/B738/FMS/clb_n1`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 218 | CDU Preflight Procedure | CLB Thrust | is selected based on TO thrust | `gt 0` |

### `sim/flightmodel/position/theta`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 232 | Go Around | Fly manually | 15 degrees up | `gte 12` |

### `laminar/B738/autopilot/cmd_a_pos`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 235 | Go Around | When stable | engage autopilot | `eq 1` |

### `laminar/B738/toggle_switch/bleed_air_1_pos`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 244 | Takeoff Procedure | Left Engine Bleed | OFF | `eq 0` |
| 250 | Takeoff Procedure | Left Engine Bleed | ON (Wait for the pack to stabilize) | `eq 1` |

### `laminar/B738/toggle_switch/bleed_air_2_pos`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 246 | Takeoff Procedure | Right Engine Bleed | OFF | `eq 0` |
| 248 | Takeoff Procedure | Right Engine Bleed | ON (Wait for the pack to stabilize) | `eq 1` |

### `sim/cockpit/engine/APU_running`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 247 | Before Taxi Procedure | APU | ON | `eq 1` |
| 295 | Icing Spray Procedure | APU | OFF (unless required) | `eq 0` |

### `sim/cockpit/engine/APU_N1`

| pk | Procedure | Item | Setting | Rule |
|----|-----------|------|---------|------|
| 254 | Takeoff Procedure | APU | OFF | `eq 0` |
