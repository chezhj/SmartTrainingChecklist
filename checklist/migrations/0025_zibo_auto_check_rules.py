"""
Data migration: populate auto_check_rule on the initial set of Zibo 737/738
checklist items where a dataref can confirm the required state.

Rules only applied when auto_check_rule is currently NULL — safe to re-run
and will not overwrite rules set manually via the admin.

Datarefs used:
  laminar/B738/parking_brake_pos          0=released, 1=set
  laminar/B738/flt_ctrls/flap_lever       0.0=UP, 0.125=1, 0.25=2, …
  laminar/B738/flt_ctrls/speedbrake_lever_pos  0=down/stowed
  laminar/B738/electric/battery_pos       1=on
  laminar/B738/autobrake/autobrake_pos    0=off
  sim/cockpit/switches/gear_handle_status 0=up, 1=down
  sim/cockpit/switches/fasten_seat_belts  0=off, ≥1=on/auto
  sim/cockpit/electrical/beacon_lights_on 0/1
  sim/cockpit/electrical/landing_lights_on 0/1
  sim/cockpit/electrical/strobe_lights_on  0/1
  sim/cockpit/electrical/taxi_light_on     0/1
"""

from django.db import migrations

# {CheckItem.pk: auto_check_rule dict}
# PKs match checklist/fixtures/checklist_content.json
_RULES = {
    # ── Flight Deck Preparation ──────────────────────────────────────────────
    138: {"dataref": "laminar/B738/parking_brake_pos", "op": "eq", "value": 1},
    # Parking Brake → Set

    141: {"dataref": "laminar/B738/flt_ctrls/speedbrake_lever_pos", "op": "eq", "value": 0},
    # Speed Brake → Down

    143: {"dataref": "laminar/B738/flt_ctrls/flap_lever", "op": "eq", "value": 0.0},
    # Flaps → Up

    144: {"dataref": "sim/cockpit/switches/gear_handle_status", "op": "eq", "value": 1},
    # Landing Gear → Down

    145: {"dataref": "laminar/B738/electric/battery_pos", "op": "eq", "value": 1},
    # Battery → On & Guard Down

    # ── Preflight Procedure ──────────────────────────────────────────────────
    18: {"dataref": "sim/cockpit/switches/fasten_seat_belts", "op": "gte", "value": 1},
    # Seatbelt Signs → On

    # ── Before Start Procedure ───────────────────────────────────────────────
    9: {"dataref": "sim/cockpit/electrical/beacon_lights_on", "op": "eq", "value": 1},
    # Anti Collision Light → ON

    # ── Engine Start Procedure ───────────────────────────────────────────────
    77: {"dataref": "laminar/B738/parking_brake_pos", "op": "eq", "value": 0},
    # Parking Brake → Release

    89: {"dataref": "laminar/B738/parking_brake_pos", "op": "eq", "value": 1},
    # Parking Brake → Set (when pushback complete)

    # ── Before Taxi Procedure ────────────────────────────────────────────────
    99: {"dataref": "sim/cockpit/electrical/taxi_light_on", "op": "eq", "value": 1},
    # Taxi Lights → On

    # ── Before Takeoff Procedure ─────────────────────────────────────────────
    106: {"dataref": "sim/cockpit/electrical/landing_lights_on", "op": "eq", "value": 1},
    # Landing Lights → ON

    109: {"dataref": "sim/cockpit/electrical/strobe_lights_on", "op": "eq", "value": 1},
    # Position Lights → Strobe & Steady

    # ── Takeoff Procedure ────────────────────────────────────────────────────
    123: {"dataref": "sim/cockpit/switches/gear_handle_status", "op": "eq", "value": 0},
    # AT Positive Rate → Gear Up

    126: {"dataref": "laminar/B738/autobrake/autobrake_pos", "op": "eq", "value": 0},
    # Autobrake → OFF

    # ── Descent Preparation ──────────────────────────────────────────────────
    194: {"dataref": "sim/cockpit/switches/fasten_seat_belts", "op": "gte", "value": 1},
    # Seatbelt signs → On
}


def _apply_rules(apps, schema_editor):
    CheckItem = apps.get_model("checklist", "CheckItem")
    for pk, rule in _RULES.items():
        CheckItem.objects.filter(pk=pk, auto_check_rule__isnull=True).update(
            auto_check_rule=rule
        )


def _remove_rules(apps, schema_editor):
    CheckItem = apps.get_model("checklist", "CheckItem")
    CheckItem.objects.filter(pk__in=_RULES.keys()).update(auto_check_rule=None)


class Migration(migrations.Migration):

    dependencies = [
        ("checklist", "0024_api_key_on_userprofile"),
    ]

    operations = [
        migrations.RunPython(_apply_rules, reverse_code=_remove_rules),
    ]
