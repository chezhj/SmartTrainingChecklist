# SimFlow — `near` Geo-Operator
## Specification: Rule Engine Extension

**Version:** 1.0  
**Status:** Draft  
**Replaces:** `RUNWAY_PROXIMITY_SPEC.md` (superseded)  
**Scope:** `checklist/rules.py` only — no changes to plugin, views, or models  
**Related specs:** `PHASE_3_ALPHA_SPEC.md`, `MODEL_DESIGN.md`

---

## 1. Problem Statement

The Before Takeoff procedure must activate automatically when the aircraft
approaches the departure runway hold-short point. The existing rule engine
(`rules.py`) handles all procedure and item trigger logic. This spec extends
it with a single new geo-operator, `near`, that evaluates proximity between
the aircraft's current position and a pair of reference coordinates — both
sourced from datarefs already available in the sim.

---

## 2. Constraints

- `plugin_views.py` must not change — the watchlist and evaluation flow
  are already correct and call into `rules.py` at the right points
- Plugin must not change — it is a dumb dataref reporter; it has no
  knowledge of what any value means
- Aircraft position is **not** implicitly in the payload — it only appears
  if the watchlist requests it. The `near` implementation must ensure it
  is requested
- The `near` operator is a **geo-operator**, structurally distinct from
  scalar comparison operators (`lt`, `gt`, `eq`). The schema should make
  this visible
- The unset sentinel for FMC reference coordinates is **exactly `0.0`** in
  both lat and lon — confirmed by direct testing. This is the safe
  "not yet programmed" guard

---

## 3. Design Decisions

### 3.1 Why `near` does not include aircraft position in its JSON schema

Aircraft position (`sim/flightmodel/position/latitude` / `longitude`) is
a universal implicit dependency of any geo-operator. Requiring authors to
spell it out in every rule would be redundant and error-prone. Instead,
`collect_datarefs` adds these two paths to the watchlist automatically
whenever it encounters a `near` node. The schema stays minimal; the
implementation handles the plumbing.

### 3.2 Why reference coordinates come from datarefs, not static values

Static coordinates (e.g. from OurAirports or a local database) would
diverge from what X-Plane is actually rendering when users have Navigraph
or custom scenery installed. Using `laminar/B738/fms/ref_runway_start_lat`
and `ref_runway_start_lon` guarantees coordinates match the Zibo FMC
exactly — the same source X-Plane's own RAAS system uses. The plugin
reports these as raw values; Django does the geometry.

### 3.3 Why the FMC sentinel `(0.0, 0.0)` returns `False` not an error

When the FMC departure runway is not yet programmed, the reference coords
are `0.0` / `0.0`. Treating this as `False` (condition not met) is the
correct degradation — the procedure simply won't auto-trigger, and the
pilot advances manually as before. Raising an error or logging a warning
here would be noise on every poll until the FMC is programmed.

### 3.4 Why `collect_datarefs` handles the implicit position paths

`plugin_views.py` calls `collect_datarefs(proc.show_rule)` to build the
watchlist. If `collect_datarefs` yields the implicit aircraft position
paths for `near` nodes, the watchlist is correct with zero changes outside
`rules.py`. This is the right place — it's already the single source of
truth for "what does this rule need to read."

---

## 4. Schema

### 4.1 `near` operator node

```json
{
  "op": "near",
  "ref_lat": "<dataref_path>",
  "ref_lon": "<dataref_path>",
  "meters": <number>
}
```

| Field | Type | Description |
|---|---|---|
| `op` | `"near"` | Identifies this as a geo-operator |
| `ref_lat` | string | Dataref path for reference latitude |
| `ref_lon` | string | Dataref path for reference longitude |
| `meters` | number | Proximity threshold in metres |

Aircraft position is implicit — never specified in the rule JSON.

### 4.2 Before Takeoff procedure `show_rule`

```json
{
  "all": [
    {
      "op": "near",
      "ref_lat": "laminar/B738/fms/ref_runway_start_lat",
      "ref_lon": "laminar/B738/fms/ref_runway_start_lon",
      "meters": 200
    },
    {
      "dataref": "sim/flightmodel/position/y_agl",
      "op": "lt",
      "value": 5
    },
    {
      "dataref": "sim/flightmodel/misc/groundspeed",
      "op": "lt",
      "value": 5
    }
  ]
}
```

The `agl` and `groundspeed` guards prevent a false positive if the
aircraft happens to be spawned near a runway threshold without taxiing.

---

## 5. Implementation — `rules.py` changes only

Three functions need extending. All existing behaviour is unchanged.

### 5.1 `haversine_meters` — new private helper

Add once at module level. No external dependencies.

```python
import math

def _haversine_meters(lat1: float, lon1: float,
                      lat2: float, lon2: float) -> float:
    """
    Great-circle distance in metres between two lat/lon points.
    Accuracy within ~0.3% — sufficient for runway proximity detection.
    Executes in ~2 µs; safe to call at 1 Hz in the request cycle.
    """
    R = 6_371_000
    p = math.pi / 180
    dlat = (lat2 - lat1) * p
    dlon = (lon2 - lon1) * p
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1 * p) * math.cos(lat2 * p) *
         math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))
```

### 5.2 `collect_datarefs` — add `near` branch

```python
# Existing pattern (scalar operators):
#   if "dataref" in node:
#       yield node["dataref"]

# Add after existing branches:
elif node.get("op") == "near":
    yield node["ref_lat"]
    yield node["ref_lon"]
    # Aircraft position is an implicit dependency of every near operator.
    # Yielding here ensures the plugin watchlist always includes these paths
    # without any near rule having to declare them explicitly.
    yield "sim/flightmodel/position/latitude"
    yield "sim/flightmodel/position/longitude"
```

### 5.3 `evaluate_rule` — add `near` branch

```python
# Add alongside existing op handling (lt, gt, eq, ...):

elif op == "near":
    ref_lat = float(datarefs.get(node["ref_lat"], 0.0))
    ref_lon = float(datarefs.get(node["ref_lon"], 0.0))

    # FMC not yet programmed — treat as condition not met, not an error.
    if ref_lat == 0.0 and ref_lon == 0.0:
        return False

    ac_lat = float(datarefs.get("sim/flightmodel/position/latitude", 0.0))
    ac_lon = float(datarefs.get("sim/flightmodel/position/longitude", 0.0))

    return _haversine_meters(ac_lat, ac_lon, ref_lat, ref_lon) < node["meters"]
```

### 5.4 `collect_leaf_evaluations` — add `near` branch

This function is used by the session logger in `plugin_views.py` to record
condition detail when the gate item changes. Extend it so `near` nodes
produce useful log output.

```python
elif node.get("op") == "near":
    ref_lat = float(datarefs.get(node["ref_lat"], 0.0))
    ref_lon = float(datarefs.get(node["ref_lon"], 0.0))
    ac_lat  = float(datarefs.get("sim/flightmodel/position/latitude", 0.0))
    ac_lon  = float(datarefs.get("sim/flightmodel/position/longitude", 0.0))

    if ref_lat == 0.0 and ref_lon == 0.0:
        dist = None
        result = False
    else:
        dist = round(_haversine_meters(ac_lat, ac_lon, ref_lat, ref_lon), 1)
        result = dist < node["meters"]

    yield {
        "op": "near",
        "ref_lat": node["ref_lat"],
        "ref_lon": node["ref_lon"],
        "threshold_m": node["meters"],
        "dist_m": dist,           # null if FMC unprogrammed
        "result": result,
    }
```

---

## 6. Data Flow

```
FMC programmed with departure runway
  └─ laminar/B738/fms/ref_runway_start_lat/lon become non-zero

Django builds watchlist (every plugin_state response)
  └─ collect_datarefs walks Before Takeoff show_rule
  └─ near node → yields ref_lat, ref_lon, ac_lat, ac_lon paths
  └─ all four paths added to watch[] list

Plugin receives watch list
  └─ reads all four datarefs at 1 Hz
  └─ reports as flat datarefs dict in next POST

Django evaluates show_rule (plugin_state, every POST)
  └─ evaluate_rule → near branch
  └─ sentinel check: ref_lat == 0.0 and ref_lon == 0.0 → False
  └─ haversine(ac, ref) < 200 → True/False
  └─ combined with agl < 5 and groundspeed < 5
  └─ all True → Before Takeoff procedure becomes visible/active

Runway change mid-taxi (ATC assigns different runway)
  └─ crew re-enters FMC → ref_lat/lon update automatically
  └─ next plugin POST carries new values
  └─ haversine recalculates against new threshold transparently
```

---

## 7. Operational Behaviour

| State | `ref_lat/lon` | `evaluate_rule` result | Behaviour |
|---|---|---|---|
| FMC unprogrammed | `0.0, 0.0` | `False` | No auto-trigger; manual advance only |
| FMC programmed, >200m away | non-zero | `False` | Waiting |
| FMC programmed, <200m, taxiing fast | non-zero | `False` | `groundspeed` guard blocks it |
| FMC programmed, <200m, stopped, on ground | non-zero | `True` | Before Takeoff activates |
| Spawned on runway without FMC | `0.0, 0.0` | `False` | Safe — FMC guard catches it |
| Runway changed mid-taxi | updates live | recalculates | Transparent — no session reset |

---

## 8. Testing

### Unit tests for `rules.py`

| Test | Input | Expected |
|---|---|---|
| `near` — within threshold | dist 150m, threshold 200m | `True` |
| `near` — beyond threshold | dist 250m, threshold 200m | `False` |
| `near` — exactly at threshold | dist 200m, threshold 200m | `False` (`<` not `<=`) |
| `near` — FMC sentinel | ref `0.0, 0.0` | `False` |
| `near` — collect_datarefs yields 4 paths | any near node | 4 paths in output |
| `near` in `all` — one False | near True, agl 10 | `False` |
| `near` in `all` — all True | near True, agl 2, gs 3 | `True` |
| `collect_leaf_evaluations` near | dist 143m | `dist_m: 143.0, result: True` |
| `collect_leaf_evaluations` sentinel | ref `0.0, 0.0` | `dist_m: null, result: False` |

### Integration smoke test

Set `laminar/B738/fms/ref_runway_start_lat/lon` to LOWI 08 threshold
coordinates in the test datarefs dict. Set aircraft position to 150m away.
Confirm `plugin_state` POST returns the Before Takeoff procedure as newly
active.

---

## 9. Explicit Non-Goals

- This spec does not cover destination runway proximity (arrival triggers)
- This spec does not handle non-Zibo aircraft (Zibo-specific datarefs)
- This spec does not add new API endpoints or model fields
- This spec does not modify `plugin_views.py`
- The 200m threshold in the `show_rule` JSON is a starting value;
  real-world tuning is a content decision, not a code decision
- `haversine_meters` is not exposed as a public utility — it is private
  to `rules.py`

---

## 10. Open Questions

1. Should `near` support an optional `label` field for display in the
   session log UI, similar to how other conditions might be labelled?
   Currently the log shows `ref_lat`/`ref_lon` dataref paths, which are
   readable but verbose.

2. Is there a `collect_leaf_evaluations` equivalent called anywhere in
   the browser-facing views (for live condition display in the UI), or is
   it currently only used for session file logging? This affects whether
   the `near` leaf output format needs to be UI-friendly now or later.

---

*End of specification*
