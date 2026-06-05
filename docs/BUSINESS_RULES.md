# Business Rules Reference

Extracted from the live codebase (`models.py`, `views.py`, `api_views.py`, `plugin_views.py`, `rules.py`, `detail.html`, `idle.html`). Intended as a reference for both humans and AI. Source locations noted where they matter.

* * *

## 1\. CheckItem Visibility

**Rule:** A `CheckItem` is visible if every one of its `attributes` is present in the session's active attribute ID list.

**Mandatory items** have no attributes at all and are always visible.

```python
# models.py — CheckItem.shouldshow()
def shouldshow(self, profile_list):
    attributes = self.attributes.values_list("id", flat=True)
    if attributes:
        return set(attributes) <= set(profile_list)  # all must match
    return True  # no attributes → mandatory, always show
```

**DualPilot injection:** Attribute pk=16 ("DualPilot") is dynamically added to `active_attr_ids` at render time when `pilot_role != "SOLO"`, and stripped when SOLO. It is never stored this way in the DB — it is injected in `procedure_detail` and `plugin_check_next` only.

* * *

## 2\. Attribute Activation — Priority Order

When computing which attributes are active for a session:  
Change:  
First load pilot defaults, then suggest based on OFP, show to the pilot then pilot determines/overrides

| Priority | Source | Condition |
| --- | --- | --- |
| 2   | `ofp_derived` | OFP-derived from SimBrief temperature / bleed |
| 1(highest) | `pilot_override` | Pilot selected on form AND not in their saved defaults |
| 3   | `user_default` | Saved user preference, or selected item that matches a saved default |
| auto | invisible default | `show=False` attribute auto-activated unless over-ruled or plugin-driven |

CHANGE: Priority
**Invisible defaults (show=False):** Automatically added unless:

- The attribute has `live_rule_mode` set — these start OFF and are activated by the plugin.
- The attribute's `over_ruled_by` is already active in the session.

Example: `AboveZero` (show=False, over_ruled_by=Anti-Ice Normal) is auto-activated whenever Anti-Ice Normal is NOT active.

Source: `views.py — _resolve_active_ids()`

* * *

## 3\. OFP Attribute Derivation (SimBrief)

Temperature bands (only the first matching rule applies):

| Condition | Attribute title activated |
| --- | --- |
| `temp < 0°C` | `Anti-Ice Normal` |
| `0 < temp < 11°C` | `ZeroToTen` |

Bleed:

| Condition | Attribute title activated |
| --- | --- |
| `bleed_setting == "OFF"` | `Short Runway` |

**Never auto-derived:** `{"VA", "Online"}` — these are always pilot-chosen.

Source: `views.py — _derive_ofp_attrib_ids()`, `_OFP_TEMP_RULES`, `_OFP_BLEED_OFF_TITLE`

## 3B. loading OFP

CHANGE: OFP load and attribute derivation should be triggered when  
`User is logged in AND`  
`user has simbrief_id AND`  
`starts new flight`

Or when

`User logs in AND`  
`user has simbrief_id AND``there is NO active session for that user`

If in above case there is an active session for the user and origin or destination do not match the OFP, the user should be asked if a he wants to start a new flight.

&nbsp;

* * *

## 4\. Flight Session Lifecycle

1.  Pilot clicks **Start Checklist** → `FlightSession` created with `is_active=True`.
2.  `session_key` format: `ABCD-1234` (stored in Django session as `flight_session_key`).
3.  `FlightSessionAttribute` — one row per `Attribute`, created eagerly at session start.
4.  `active_phase` — slug of the current procedure frontier, forward-only (never moves backward).
5.  Initial `active_phase`: first `Procedure` ordered by `step`.

**Continue vs. create:** If an existing active session is found on "Start Checklist", its attributes and role are updated in-place rather than creating a new session.

**Stale session cleanup:** On new session creation, any other `is_active=True` sessions for the same `user_profile` are deactivated. This ensures the plugin's `session_id` goes stale and it re-fetches.

**Deactivation triggers:** "Clear" action, "New Flight" action, or starting a replacement session.

CHANGE:  
**Removal triggers:** Question: what should remove sessions or clean them up?

Source: `views.py — _create_flight_session()`, `profile_view()`

* * *

## 5\. Procedure Page Visit — State Reset

**Every visit** to a procedure page deletes all `FlightItemState` rows for that procedure. This gives a fresh visual slate. The `active_phase` frontier is not affected by this reset — it only advances forward.

Source: `views.py — procedure_detail()` lines 603–606

CHANGE:

I think i need to challenge this. when do I want a fresh page (clean all checks)

1.  when i use a procedure again
2.  NOT when I reload because of a connection drop

Number 1 normally happens when  
a.        A procedure is triggered by its show rule  
b.        The flight follows a non regular pattern, like after a go-around

So the question is, what should happen when a user manually selects a "done" procedure from the list . I think it is easier to give the oppertunity to clear the procedure by the user and not automate, unless triggered by some rule, because that are the ones you actually re-use. The most procedures (like the ones to get the plane ready for flight, will almost never be reused

* * *

## 6\. active_phase Frontier

The `FlightSession.active_phase` slug tracks how far the pilot has progressed:

- Advances when visiting a procedure with a higher `step` than the current frontier.
- Never moves backward when navigating to a previous procedure.
- The plugin uses `active_phase` to know which procedure's items to auto-check.

CHANGE:  
Not sure this is needed to check for items because  
\- when the pilot chooses to clear a previous procedure, then that procedure should also be watched, not the last "active_phase"  
\- procedures have information to decide if the next procedure should be loaded, auto_continue field. So I think the session does not need to know the phase

The only thing I can think of, why phase could be needed, is if the phase is needed to determine which procedure to show or give as option. Next to that it's nice to see the flight phase in the header of the page, but not needed now

Source: `views.py — procedure_detail()` lines 591–598

* * *

## 7\. Lowlight (Dual Mode)

An item gets the `lowlight` CSS class (visually dimmed, NOT hidden) when all three are true:

1.  Session is in `dual_mode`
2.  `item.role != "BOTH"`
3.  `item.role` is not in `[pilot_role, captain_role]`

Source: `views.py — procedure_detail()` lines 629–635

* * *

## 8\. Procedure Navigation — Linear vs. Conditional

- **Linear nav** (Prev/Next): only procedures where `show_rule` is `null`.
- **Conditional procedures** (`show_rule` set): hidden in nav by default (`js-hidden` CSS class). They appear/disappear dynamically based on plugin dataref state.
- Conditional procedures are not counted in the step total for linear nav.

CHANGE: the whole counter is not needed

* * *

## 9\. Auto-Advance

When all items of a procedure are checked and at least one item was checked **this visit** (`hasCheckedThisVisit`), navigate after 600 ms:

- `auto_continue == True` → next linear procedure (lowest `step > current.step` where `show_rule=null` and has visible items), or `/idle` if none.
- `auto_continue == False` → `/idle`.

`auto_continue` controls **destination only** — it no longer gates whether auto-advance fires.

The `hasCheckedThisVisit` guard prevents auto-advancing when a pilot revisits an already-complete procedure (e.g., after a connection drop and reload).

Note: scroll-to-next-unchecked within a procedure is a separate mechanism — see Rule 13.

Source: `detail.html` — `updateProgress()` JS

* * *

## 10\. Conditional Procedure Reveal — Two-Set Pattern

The JS maintains two sets to track conditional procedure state. Behaviour differs by page:

**`idle.html`** — auto-navigates on first firing slug (lowest `step`):

| Set | Purpose | Manual fallback populates? |
| --- | --- | --- |
| `revealedSlugs` | Which nav buttons are currently visible | YES |
| `navigatedSlugs` | Which slugs we’ve already auto-navigated to | NO  |

**`detail.html`** — reveals buttons only, never auto-navigates. `navigatedSlugs` is unused on procedure pages (pilot is never interrupted mid-checklist).

**Why two sets (idle.html):** The manual fallback (sim disconnected) adds to `revealedSlugs` so buttons stay visible. It does NOT add to `navigatedSlugs`. This means when the sim reconnects and a rule fires, `navigatedSlugs.has(slug)` is still false → auto-navigation always runs even if the button was already visible.

**Race fix (idle.html):** When multiple rules fire simultaneously, only the first (lowest `step`) slug triggers navigation — the loop breaks after the first navigation assignment.

**Hide logic (both pages):** When a slug is no longer in `show_procedures`, it is removed from both sets and hidden. This fires when a rule *stops firing* before the pilot acts (dataref condition reverts). It does NOT fire for completion — completed procedures self-hide via `updateProgress()` and remove themselves from `revealedSlugs` directly.

**Conditional procedure completion:** When all items in a conditional procedure are done, it hides itself from nav. `revealedSlugs` is updated. It reappears when `show_rule` fires again.

Source: `detail.html` and `idle.html` — `applyShowProcedures()` JS; `CLAUDE.md` architecture notes

* * *

## 11\. Sim Connection States (Browser)

Derived from `last_seen` unix timestamp and `sim_connected`/`sim_initializing` fields in `/api/poll/` response:

| State | Condition | Display |
| --- | --- | --- |
| Connected | `sim_connected == true` | Green dot, "X-Plane Live · 1 Hz" |
| Reconnecting | `!sim_connected && last_seen > 0 && age < 30s` | Amber dot, "Reconnecting…" |
| Initializing | `sim_initializing == true` | Pulsing dot, "X-Plane initializing…" |
| Disconnected | `!sim_connected && last_seen > 0 && age >= 30s` | "Simulator disconnected" |
| Manual only | `last_seen == 0` | "Manual only" |

Server-side thresholds (`api_views.py — poll_view()`):

- `sim_connected = age < 5s`
- `sim_initializing = not connected && age < 15s`

* * *

## 12\. Manual Fallback (No Sim)

When `sim_connected == false`, the browser reveals **all** conditional procedures in the nav (making them manually tappable). Auto-navigation does NOT fire. `navigatedSlugs` is not populated so reconnection will still trigger navigation.

Auto-navigation (from `show_procedures`) applies from idle only. On a procedure page, the manual fallback still reveals all conditional buttons for manual access but does not auto-navigate.

Source: `detail.html` / `idle.html` — poll handler

```js
var activeConditionals = data.sim_connected
    ? (data.show_procedures || [])
    : conditionalSlugs;   // all conditional slugs when offline
applyShowProcedures(activeConditionals, data.sim_connected);  // autoNav=false when offline
```

* * *

## 13\. Item Check/Uncheck State Machine

| Current state | User action | Result |
| --- | --- | --- |
| unchecked | tap/click | → `ci-manual`, POST `/api/check/` |
| `ci-manual` | tap/click | → unchecked, POST `/api/uncheck/` |
| `ci-auto` | tap/click | no action (auto state is read-only) |
| `ci-skipped` | tap/click | no action |

Auto-advance: after marking an item, scroll to first unchecked item after it.

CHANGE: name this auto-scroll

Source: `detail.html` — `toggleItem()` JS

* * *

## 14\. Plugin Gate / Active Zone Logic

This determines which items the plugin evaluates auto-check rules for:

1.  **Optional attribute:** `Attribute pk=4` — items with this attribute are "optional" (non-blocking).
2.  **Gate:** The first visible, not-done, **required** (non-optional) item in the procedure.
3.  **Active zone:** All not-done visible items with `step <= gate_step` (includes optional items before the gate).
4.  Auto-check rules are only evaluated for items **in the active zone**.
5.  Watch datarefs are collected from **all visible items** with rules (not just active zone) so the plugin keeps streaming them.

CHANGE: Make sure to evaluate from top to bottom, optional items that are executed upon, and have all criteria met, should not be skipped because the gate item was evaluated first

Source: `plugin_views.py — plugin_state()` lines 293–307

* * *

## 15\. Auto-Skip Logic

When a required item's auto-check rule fires:

1.  Any preceding optional items that are not-done are auto-skipped first.
2.  The triggering item itself is auto-checked.

Auto-skipped items get `status="skipped"`, `source="auto"` in `FlightItemState`. The browser renders them as `ci-skipped` (em-dash).  
CHANGE: Make sure to evaluate from top to bottom, optional items that are executed upon, and have all criteria met, should not be skipped because the gate item was evaluated first

Source: `plugin_views.py — plugin_state()` lines 350–377

* * *

## 16\. Conditional Procedure Edge Detection (poll)

`poll_view` tracks the last-known `show_rule` result per procedure in `FlightSession.show_rule_state` (a JSON dict `{str(proc.pk): bool}`). On every poll, for each conditional procedure:

| Rule result | Previous result | Items done? | Action |
| --- | --- | --- | --- |
| False | any | — | Hidden — not in `show_procedures`. `False` recorded in `show_rule_state`. |
| True | False (rising edge) | any | `FlightItemState` rows for procedure deleted. Slug added to `show_procedures`. Browser auto-navigates. |
| True | True (continuously true) | No | Slug added to `show_procedures`. Pilot is mid-checklist. |
| True | True (continuously true) | Yes | Silently skipped. States preserved. No loop. |

`show_rule_state` is written for **every** poll evaluation — including when the rule is `False`. This is essential: if `False` were not recorded, the next `True` evaluation would not be recognized as a rising edge, and the procedure would never re-trigger.

`show_rule_state` is persisted to the DB (saved only when changed). Preserved through server restarts.

**Re-trigger semantics**: a procedure re-triggers only when its `show_rule` transitions from `False` to `True`. Descent re-triggers after a go-around (rule went false during climb). Waypoint procedures re-trigger at each new waypoint (aircraft moved away then approached a new one). Emergency procedures re-trigger each time the condition starts fresh.

Source: `api_views.py — poll_view()`, `models.py — FlightSession.show_rule_state`

* * *

## 17\. Attribute Transition (live_rule)

Triggered before every navigation (all `.js-nav-btn` clicks are intercepted). Calls `GET /api/attribute-transition/`.

Two attribute modes:

| Mode | Behaviour |
| --- | --- |
| `activate_only` | If rule fires AND attribute is currently inactive → activate silently. No prompt. |
| `prompt_on_change` | If rule result ≠ current active state → present prompt to pilot. |

**Pilot overrides:** Stored in `FlightSession.pilot_overrides` as `{str(attr_id): bool}`. An attribute with an entry here is never prompted again in the same session.

**Accepting a prompt:** Re-evaluates `live_rule` and applies the result to `FlightSessionAttribute` with `source="live_rule"`.

**Rejecting a prompt:** Records rejection in `pilot_overrides`, attribute state unchanged.  
<br/>

Source: `api_views.py — attribute_transition_view()`, `views.py — _apply_attribute_overrides()`

* * *

## 18\. Rule Engine (rules.py)

### Composite operators

- `{"all": [rule, ...]}` — all sub-rules must be true (AND)
- `{"any": [rule, ...]}` — at least one sub-rule must be true (OR)

### Leaf shapes

```json
{"dataref": "path/to/ref", "op": "eq", "value": 1}
{"dataref": "path/to/ref", "op": "gt", "ref": "another/ref"}
{"dataref": "path/to/ref", "op": "lte", "ref": "array/ref", "ref_index": 0}
{"dataref": "path/to/ref", "op": "eq", "ref": "other/ref", "ref_index": 0, "delta": 10}
{"dataref": "path/to/ref", "op": "abs_diff_lte", "ref": "other/ref", "tolerance": 5}
{"fmc_line": "path/to/ref", "contains": "substring"}
{"fmc_line": "path/to/ref", "not_contains": "substring"}
{"fmc_line": "path/to/ref", "contains": "X", "tail": 8}
{"fmc_line": "path/to/ref", "contains": "X", "head": 4}
{"fmc_line": "path/to/ref", "contains": "X", "count_gte": 2}
```

### Comparison operators

`eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `abs_diff_lte`

### Missing dataref

Any rule referencing a dataref not present in the plugin's snapshot evaluates to `False`.

* * *

## 19\. Watch List (plugin response)

The plugin's `POST /api/plugin/state/` response includes a `watch` list of dataref paths the plugin must keep streaming. Built from:

1.  All visible items with `auto_check_rule` (not just active zone)
2.  All `Attribute.live_rule` datarefs
3.  All `IdleDataref.dataref_path` values (for the idle page display)
4.  All `Procedure.show_rule` datarefs (for conditional procedure unlocking)

Deduplicated, order-preserving.

Source: `plugin_views.py — plugin_state()` lines 339–414

* * *

## 20\. CheckItem Action Label

`CheckItem.get_action_label()` returns the display string used on the item badge:

1.  If `action_label` is set → return it verbatim.
2.  Else if item has attribute `NoActionNeed` → return `"CHECKED"`.
3.  Otherwise → return `"SET"`.

* * *

## 21\. Attribute Form — Conditions vs. General

Attributes displayed on the profile/setup form are split into two groups by `is_user_preference`:

| Group | Filter | Purpose |
| --- | --- | --- |
| Conditions | `show=True, is_user_preference=False` | Flight-specific (temp, bleed, runway) |
| General | `show=True, is_user_preference=True` | Persistent user preferences (VA, Online, etc.) |

Only `is_user_preference=True` attributes can be saved as user defaults in `UserAttributeDefault`.

* * *

## 22\. Session Keys Cleared on Reset

The following Django session keys are removed on "Clear" or "New Flight" (flight state only — auth state preserved):

```
flight_session_key, dual_mode, pilot_role, captain_role,
sb_origin, sb_destination, sb_runway, sb_temp, sb_flaps, sb_bleed,
sb_callsign, sb_block_fuel, sb_finres_altn, sb_derived_attribs,
sb_simbrief_id, sb_error
```

Source: `views.py — _FLIGHT_SESSION_KEYS`

* * *

## 23\. API Authentication

- **Browser endpoints** (`/api/check/`, `/api/uncheck/`, `/api/poll/`, `/api/attribute-transition/`): Django session auth + CSRF.
- **Plugin endpoints** (`/api/plugin/state/`, `/api/plugin/session/`, `/api/plugin/check-next/`): `Authorization: Bearer <raw_api_key>` header. CSRF exempt. Key is bcrypt-hashed in `UserProfile.api_key_hash`; only prefix stored for display.

* * *

## 24\. Logging (session JSONL)

Each flight session logs to `logs/session_<id>.jsonl`. Events logged:

| Event | When |
| --- | --- |
| `gate_changed` | The blocking gate item changes |
| `gate_cleared` | All required items done (gate = None) |
| `auto_checked` | Plugin auto-checks an item |
| `auto_skipped` | Optional item skipped because a later required item fired |
| `manual_checked` | Plugin `check-next` endpoint marks an item manually |

Each entry includes `ts` (ISO timestamp), `item_id`, `item` name, and the relevant rule + dataref values at the time.

&nbsp;

Other  
in the idle page this could show:  current speed, distance to destination, altitude, for future