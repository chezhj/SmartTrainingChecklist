# SimFlow v2.0 — Implementation Specification

## Purpose

This document defines the scope, data model, API contracts, and build sequence for v2.0.
It is intended as context for development. The existing codebase is a Django application
with models in checklist/models.py and views in checklist/views.py.

---

## Design Reference

UI design is defined in mockup-final.html (included in project).
Key design decisions:

- Mobile-first, responsive to tablet and laptop
- Dark connection bar (top), light checklist area
- Checkbox visual language:
  - Empty: white box, grey border
  - Manual checked: dark green fill (#0F6B54) + white tick + dark green left border on row
  - Auto checked: dark green fill (#0F6B54) + white dot (no tick), no left border on row
- Both checked states share the same row background (#F0FAF6)
- Info panel slides in from right via ⓘ button — contains legend, session info, reset, about

---

## Scope

### In v2.0

- Django user registration and login
- Anonymous manual mode remains fully functional (no login required)
- SimSession model (links user to active flight)
- CheckedItem model (server-side checked state, persists across reloads)
- User profile (attributes) saved to account, pre-loaded each new flight
- JSON rule evaluator for dataref_expression field on CheckItem
- /api/state endpoint (plugin → Django)
- /api/poll endpoint (browser → Django, 2–3s interval)
- Session reset action ("new flight")
- XPython3 plugin: reads datarefs, POSTs to backend, receives watch list
- Frontend redesign per mockup
- Yoke/button binding for manual checks from simulator
- Bulk load of dataref_expression rules for Zibo 737 (~15–20 datarefs)
  NOTE: The existing dataref_expression TextField on CheckItem is preserved as-is.
  The field currently stores xChecklist export syntax. A NEW separate field will
  store the JSON rule for v2.0 automation. Do not alter or migrate the existing field.

### Out of scope for v2.0

- Automatic procedure switching on sim state (engine failure etc.)
- Debug mode showing raw dataref values
- SSE / WebSockets (planned v3.0)
- Multiple aircraft beyond Zibo 737
- Multiplayer, C++ plugin, offline bundle, xChecklist export changes

---

## Data Model Changes

### New model: SimSession

```python
class SimSession(models.Model):
    user         = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at   = models.DateTimeField(auto_now_add=True)
    last_seen    = models.DateTimeField(null=True, blank=True)
    is_active    = models.BooleanField(default=True)
    aircraft     = models.CharField(max_length=50, blank=True)  # e.g. "ZIBO 738"

    class Meta:
        ordering = ['-created_at']
```

### New model: CheckedItem

```python
class CheckedItem(models.Model):
    SOURCE_CHOICES = [('MANUAL', 'Manual'), ('AUTO', 'Auto')]

    sim_session  = models.ForeignKey(SimSession, on_delete=models.CASCADE,
                                     null=True, blank=True)
    # null sim_session = anonymous manual session (session-key based)
    session_key  = models.CharField(max_length=40, blank=True)
    check_item   = models.ForeignKey(CheckItem, on_delete=models.CASCADE)
    checked_at   = models.DateTimeField(auto_now_add=True)
    source       = models.CharField(max_length=10, choices=SOURCE_CHOICES,
                                    default='MANUAL')

    class Meta:
        unique_together = [('sim_session', 'check_item'),
                           ('session_key', 'check_item')]
```

### New field on CheckItem

```python
# ADD — do not touch existing dataref_expression field
auto_check_rule = models.JSONField(blank=True, null=True)
```

### New model: UserProfile

```python
class UserProfile(models.Model):
    user            = models.OneToOneField(User, on_delete=models.CASCADE)
    saved_attributes = models.JSONField(default=list)
    simbrief_id     = models.CharField(max_length=50, blank=True)
    dual_mode       = models.BooleanField(default=False)
    pilot_role      = models.CharField(max_length=10, blank=True)
```

Profile is loaded into session at login and on "Start Checklist".
User can modify per-flight on the profile page; saved on "Start Checklist".

---

## auto_check_rule JSON Format

Stored in CheckItem.auto_check_rule. The existing dataref_expression field
is NOT used for auto-checking and must not be modified.

### Single condition

```json
{ "dataref": "sim/cockpit/switches/parking_brake", "op": "eq", "value": 1 }
```

### Multiple conditions (all must match)

```json
{
  "all": [
    {
      "dataref": "laminar/B738/flt_ctrls/flap_lever",
      "op": "gte",
      "value": 0.125
    },
    {
      "dataref": "sim/cockpit2/engine/actuators/throttle_ratio",
      "op": "lte",
      "value": 0.05
    }
  ]
}
```

### Supported operators

- eq, neq, gt, gte, lt, lte

### Rule evaluator (checklist/rules.py)

```python
def evaluate_rule(rule: dict, state: dict) -> bool:
    """
    rule: parsed auto_check_rule JSON
    state: dict of {dataref_path: value} from plugin POST
    Returns True if condition is satisfied.
    """
    if 'all' in rule:
        return all(evaluate_rule(r, state) for r in rule['all'])
    if 'any' in rule:
        return any(evaluate_rule(r, state) for r in rule['any'])

    dataref = rule.get('dataref')
    op      = rule.get('op')
    value   = rule.get('value')

    if dataref not in state:
        return False

    actual = state[dataref]
    ops = {
        'eq':  lambda a, v: a == v,
        'neq': lambda a, v: a != v,
        'gt':  lambda a, v: a >  v,
        'gte': lambda a, v: a >= v,
        'lt':  lambda a, v: a <  v,
        'lte': lambda a, v: a <= v,
    }
    return ops.get(op, lambda a, v: False)(actual, value)
```

---

## API Endpoints

### POST /api/state

Called by XPython3 plugin at 1 Hz (on change).
Authentication: Django session token or token auth (user must be logged in).

Request body:

```json
{
  "session_id": 42,
  "datarefs": {
    "sim/cockpit/switches/parking_brake": 1,
    "laminar/B738/flt_ctrls/flap_lever": 0.0
  }
}
```

Response:

```json
{
  "status": "ok",
  "checked": [17, 23],
  "watch": [
    "sim/cockpit/switches/parking_brake",
    "laminar/B738/flt_ctrls/flap_lever",
    "sim/cockpit2/engine/actuators/throttle_ratio"
  ]
}
```

Behaviour:

1. Validate session_id belongs to authenticated user
2. Update SimSession.last_seen
3. For each CheckItem with a non-null auto_check_rule:
   - Evaluate rule against incoming datarefs
   - If satisfied and not already in CheckedItem: create CheckedItem(source=AUTO)
4. Return list of newly checked item IDs + full watch list for current procedure
   (watch list is derived from all auto_check_rules on visible items in current procedure)

### GET /api/poll

Called by browser every 2–3 seconds via JS fetch.
No authentication required for anonymous sessions (uses session_key cookie).

Query params: ?procedure=<slug>&since=<unix_timestamp>

Response:

```json
{
  "checked_items": [
    { "id": 17, "source": "AUTO" },
    { "id": 23, "source": "MANUAL" }
  ],
  "sim_connected": true,
  "last_seen": 1718200000
}
```

Behaviour:

1. Identify session (SimSession for logged-in, session_key for anonymous)
2. Return all CheckedItems for this session newer than `since`
3. Return sim_connected: true if SimSession.last_seen within last 5 seconds

### POST /api/check

Called by browser when user manually taps a checklist item.

Request body:

```json
{ "check_item_id": 17 }
```

Response:

```json
{ "status": "ok", "id": 17, "source": "MANUAL" }
```

### POST /api/uncheck

Called if user taps a checked item to uncheck it (toggle).

Request body:

```json
{ "check_item_id": 17 }
```

Response:

```json
{ "status": "ok", "id": 17 }
```

### POST /api/session/reset

Resets current flight session (clears CheckedItems, creates new SimSession).

Response:

```json
{ "status": "ok", "new_session_id": 43 }
```

---

## Frontend Changes

### JS polling loop (add to detail.html template)

```javascript
const POLL_INTERVAL = 2500; // ms
let lastPoll = 0;

async function pollChecklist() {
  try {
    const res = await fetch(
      `/api/poll?procedure={{ procedure.slug }}&since=${lastPoll}`,
    );
    const data = await res.json();
    lastPoll = Math.floor(Date.now() / 1000);

    data.checked_items.forEach((item) => {
      markItem(item.id, item.source);
    });

    updateConnectionBadge(data.sim_connected);
  } catch (e) {
    updateConnectionBadge(false);
  }
}

function markItem(id, source) {
  const row = document.querySelector(`[data-item-id="${id}"]`);
  if (!row) return;
  row.classList.remove("ci-unchecked");
  row.classList.add(source === "AUTO" ? "ci-auto" : "ci-manual");
  const box = row.querySelector(".check-box");
  if (source === "MANUAL") {
    box.innerHTML = "<svg ...tick svg...>";
    box.classList.add("manual");
  } else {
    box.classList.add("auto"); // ::after pseudo handles the dot
  }
}

setInterval(pollChecklist, POLL_INTERVAL);
```

Each checklist item row needs: `data-item-id="{{ item.id }}"` attribute.

### Connection badge states

- No simulator: grey dot, "Manual only"
- Simulator connected (last_seen < 5s): pulsing teal dot, "X-Plane · {aircraft}"
- Simulator recently lost (5–30s): amber dot, "Reconnecting…"
- Simulator lost (>30s): grey dot, "Simulator disconnected"

---

## XPython3 Plugin Outline

File: `xplane_plugin/FlyVdwaal/PI_FlyVdwaal.py`

```python
import xp
import requests
import threading
import json

BACKEND_URL = "https://fly.vdwaal.net/api/state"
POLL_HZ = 1.0

WATCH_DATAREFS = [
    "sim/cockpit/switches/parking_brake",
    "laminar/B738/flt_ctrls/flap_lever",
    # ... populated dynamically from server response
]

class PythonInterface:
    def connect(self):
        self.token = load_stored_token()
        self.session_id = get_or_create_session(self.token)
        self.watch = WATCH_DATAREFS
        self.last_values = {}
        return xp.registerFlightLoopCallback(self.loop, 1.0 / POLL_HZ, 0)

    def loop(self, since_last, elapsed, counter, ref):
        state = {}
        changed = False
        for path in self.watch:
            val = xp.getDataf(xp.findDataRef(path))
            if self.last_values.get(path) != val:
                changed = True
            state[path] = val
        self.last_values = state

        if changed:
            threading.Thread(
                target=self.post_state, args=(state,), daemon=True
            ).start()

        return 1.0 / POLL_HZ  # reschedule

    def post_state(self, state):
        try:
            res = requests.post(
                BACKEND_URL,
                json={"session_id": self.session_id, "datarefs": state},
                headers={"Authorization": f"Token {self.token}"},
                timeout=2
            )
            data = res.json()
            if "watch" in data:
                self.watch = data["watch"]  # server can narrow/expand watch list
        except Exception:
            pass  # fail silently, never block flight loop
```

Key constraints:

- HTTP call always in a daemon thread — never blocks the flight loop callback
- timeout=2 on all requests
- If backend unreachable for >30s, plugin logs once and continues silently
- Credentials stored in a local config file next to the plugin

---

## Build Sequence

### Phase 1 — Foundation (no X-Plane yet)

0. Frontend redesign — implement mockup templates and CSS
1. Add Django auth (registration, login, logout views + templates)
2. Add UserProfile model, save/load profile attributes on login
3. Add SimSession and CheckedItem models + migrations
4. Add /api/check and /api/uncheck endpoints
5. Update procedure_detail view to annotate items with checked state from DB
6. Add `data-item-id` to checklist item rows in template
7. Add JS polling loop (poll endpoint returns empty until plugin exists)

### Phase 2 — Backend rule engine

1. Add auto_check_rule JSONField to CheckItem + migration
2. Write checklist/rules.py evaluator
3. Implement /api/state endpoint
4. Implement /api/poll endpoint with sim_connected flag
5. Populate auto_check_rule for initial Zibo 737 datarefs via Django admin or fixture

### Phase 3 — Plugin

1. Scaffold XPython3 plugin with credential storage
2. Implement flight loop + dataref reading
3. Implement threaded POST to /api/state
4. Handle watch list response
5. Add plugin UI widget for credentials + connection status

### Phase 4 — Integration & polish

1. End-to-end test: sim action → Django → browser
2. Connection badge states (connected / reconnecting / lost)
3. Session reset flow
4. Info panel wired up (session data, reset action)
5. Install documentation for plugin

---

## Key Files to Create or Modify

| File                                       | Action                                                          |
| ------------------------------------------ | --------------------------------------------------------------- |
| checklist/models.py                        | Add SimSession, CheckedItem, UserProfile, auto_check_rule field |
| checklist/rules.py                         | New — rule evaluator                                            |
| checklist/views.py                         | Update procedure_detail; add api views                          |
| checklist/urls.py                          | Add API routes                                                  |
| checklist/templates/checklist/detail.html  | Redesign + data-item-id + JS poll                               |
| checklist/templates/checklist/profile.html | Redesign + toggles + login nudge                                |
| checklist/templates/registration/          | New — login, register templates                                 |
| checklist/fixtures/zibo_datarefs.json      | New — initial auto_check_rule data                              |
| xplane_plugin/FlyVdwaal/PI_FlyVdwaal.py    | New — XPython3 plugin                                           |

---

## Constraints & Notes

- The existing dataref_expression field on CheckItem must not be modified or
  migrated. It is used by the xChecklist export feature which remains unchanged.
- The existing show_expression field on Procedure is similarly preserved.
- Django session remains the mechanism for anonymous users. SimSession is only
  created for authenticated users.
- The poll endpoint is intentionally lightweight — it returns only a diff
  (items changed since timestamp), not full checklist state.
- All API endpoints should return 400 for malformed requests and 401 for
  unauthenticated requests where auth is required.
- Plugin must be installable by non-developers: one folder drop into
  X-Plane/Resources/plugins/PythonPlugins/, no pip installs required beyond
  what XPython3 bundles.
