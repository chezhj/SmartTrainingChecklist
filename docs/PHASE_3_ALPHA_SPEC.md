# Phase 3-Alpha Specification — Plugin Bootstrap & Manual Next Item

**Project**: fly.vdwaal.net  
**Version**: v2.0 — Phase 3-alpha  
**Date**: 2026-03-24  
**Status**: Ready for implementation  
**Scope**: Minimal XPython3 plugin + Django API key auth + single "check next item" command

---

## Goal

Establish the first working end-to-end connection between X-Plane and the Django backend.  
Scope is deliberately minimal: one X-Plane command, one Django endpoint, one auth mechanism.  
No dataref reading. No auto-checking. Just: pilot presses button → next checklist item advances.

This validates the full integration path before phase 2 (data model) and phase 3-beta (dataref automation).

---

## Decisions Made (from design session)

| Topic | Decision | Rationale |
|---|---|---|
| Auth mechanism | API key (Bearer token) | Machine-to-machine; no password in plugin config; revocable without account change |
| Key lifecycle | Static, manual revocation | Sufficient for single-user, single-sim setup |
| Key storage (Django) | Hashed (like password) | Raw key never stored; regeneration invalidates old key |
| Multiple sim instances | Not supported — one active session per user | Out of scope for v2.0 |
| Backend URL | Configurable via `config.ini` | Required for local dev/testing; production is one-line change |
| No-session error handling | Log to X-Plane developer console only | No sim UI interruption; silent failure is acceptable |
| Command trigger | X-Plane native command (bindable) | Pilot binds to joystick or keyboard via X-Plane's own interface; no custom plugin UI needed |
| Command name | `fly.vdwaal.net/check_next_item` | Follows X-Plane convention; **do not change after release — breaks user bindings** |
| HTTP threading | Fire-and-forget thread per press | Avoids blocking X-Plane's main thread; response not needed in sim |

---

## Scope

### In scope

- `api_key` field on `UserProfile` model (hashed)
- "Generate / Regenerate" UI on the profile page
- Key displayed once after generation (then only masked)
- Django endpoint: `POST /api/plugin/check-next/`
- XPython3 plugin: `PI_fly_vdwaal.py` + `config.ini`
- X-Plane command registration: `fly.vdwaal.net/check_next_item`
- Non-blocking HTTP POST on command fire
- Console logging for all error/no-session cases

### Out of scope (explicitly)

- Dataref reading or any auto-checking logic (phase 3-beta)
- Plugin UI widget (no on-screen display in X-Plane)
- Multiple simultaneous sessions or devices
- Key expiry or scoping
- Session pairing via session key (phase 3-beta concern)
- Any changes to `dataref_expression`, `show_expression`, or `Attribute` model

---

## Part 1 — Django: API Key Auth

### 1a. Model change — `UserProfile`

Add two fields:

```python
# On UserProfile model
api_key_hash = models.CharField(max_length=128, blank=True, null=True)
api_key_prefix = models.CharField(max_length=8, blank=True, null=True)  # for display: "fvw_a3f9..."
```

> **Why store a prefix?** The raw key is shown once and then gone. The prefix (first 8 chars) lets you display something recognisable on the profile page so the pilot knows which key is active, without storing anything sensitive.

Use Django's `make_password` / `check_password` (PBKDF2) for hashing — same mechanism as user passwords, no new dependency.

**Migration required.** Generate with `python manage.py makemigrations`.

### 1b. Key generation logic

```python
import secrets
from django.contrib.auth.hashers import make_password, check_password

def generate_api_key():
    raw = "fvw_" + secrets.token_urlsafe(32)  # e.g. fvw_aB3x...  (approx 46 chars)
    hashed = make_password(raw)
    prefix = raw[:8]
    return raw, hashed, prefix
```

The `raw` key is returned to the view **once** to be shown to the user. Only `hashed` and `prefix` are persisted.

### 1c. Profile page UI additions

On the existing profile page (desktop and mobile), add an **API Key** section:

- If no key exists: show "No key generated" + "Generate key" button
- After generation: show the full raw key in a copyable field with a warning ("This is shown once — copy it now") + "Regenerate" button
- If a key exists (returning to the page): show `fvw_a3f9…` (prefix + ellipsis) + "Regenerate" button only

No separate page — inline within the existing profile view.

### 1d. Endpoint — `POST /api/plugin/check-next/`

**URL**: `/api/plugin/check-next/`  
**Method**: POST  
**Auth**: `Authorization: Bearer <raw_api_key>` header  
**Body**: empty (or `{}`)

**Auth middleware / decorator:**

```python
def get_user_from_api_key(request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    raw_key = auth[7:]
    for profile in UserProfile.objects.exclude(api_key_hash=None):
        if check_password(raw_key, profile.api_key_hash):
            return profile.user
    return None
```

> **Performance note**: Iterating all profiles to check the hash is fine at single-user scale. If this ever becomes multi-tenant at scale, add a lookup by prefix first. For now, keep it simple.

**Logic:**

```
1. Extract and validate Bearer key → find user
2. If no user → return 401, log nothing (not our console)
3. Find active FlightSession for that user
4. If no session → return 404, Django logs: "check_next_item: no active session for user <username>"
5. Find next unchecked, non-blocked item in current phase
6. If found → mark as checked (manual), return 200
7. If all done → return 204 (no content, phase complete)
```

**Response shapes:**

The plugin does not parse the response body — HTTP status code is sufficient for all branching. A minimal body is included only as a debugging aid (e.g. when testing with `curl`). Claude Code should not write plugin-side body parsing.

```
200 OK          → item was checked (body optional: {"checked": "FUEL PUMPS"} for curl debugging)
204 No Content  → phase complete, nothing left to check
401 Unauthorized → bad or missing API key
404 Not Found   → no active FlightSession for this user
```

---

## Part 2 — XPython3 Plugin

### 2a. File structure

```
X-Plane 12/
└── Resources/
    └── plugins/
        └── PythonPlugins/
            └── fly_vdwaal/
                ├── PI_fly_vdwaal.py   ← main plugin file
                └── config.ini          ← pilot-edited config
```

### 2b. `config.ini`

```ini
[fly.vdwaal]
api_key = paste-your-key-here
backend_url = https://fly.vdwaal.net
```

For local dev/testing, change `backend_url` to `http://localhost:8000`. No other change needed.

### 2c. `PI_fly_vdwaal.py` — intent and pseudocode

> **Note for Claude Code**: Do not treat this as copy-paste source. Write the actual implementation against the real XPPython3 environment. Reference the biuti SimBrief2Zibo plugin (https://github.com/biuti) for idiomatic patterns, particularly command registration. The XPPython3 utils wrapper (`from XPPython3.utils.commands import create_command`) is preferred over raw `xp.createCommand` if it's available in the target environment — check existing plugins for which style is used.

**Plugin has no UI whatsoever.** No on-screen widgets, no menu items, no windows. X-Plane's native keyboard/joystick binding screen is the only interface.

**Pseudocode — startup:**
```
on XPluginStart:
    read config.ini (configparser)
    extract api_key and backend_url
    log backend_url to X-Plane console
    register command "fly.vdwaal.net/check_next_item" 
        → description: "Fly.vdwaal – Check next checklist item"
        → callback: on_check_next
    return plugin name, signature, description

on XPluginStop:
    unregister command handler
```

**Pseudocode — command handler:**
```
on_check_next(phase):
    if phase != BEGIN (key-down only, ignore key-up and held):
        return pass-through
    spawn fire-and-forget daemon thread → post_check_next()
    return pass-through  ← always let X-Plane continue processing

post_check_next() [runs in thread]:
    if api_key missing or is placeholder:
        log warning to console
        return
    POST {backend_url}/api/plugin/check-next/
        header: Authorization: Bearer {api_key}
        timeout: 5 seconds
    on 200: log nothing (success is silent)
    on 204: log "[fly.vdwaal] phase complete"
    on 401: log "[fly.vdwaal] authentication failed — check api_key in config.ini"
    on 404: log "[fly.vdwaal] no active flight session"
    on timeout: log "[fly.vdwaal] request timed out"
    on connection error: log "[fly.vdwaal] could not reach backend"
    on other: log "[fly.vdwaal] unexpected status {code}"
```

**Key implementation notes for Claude Code:**
- HTTP must be non-blocking — use `threading.Thread(daemon=True)`. Do NOT use `requests` synchronously on X-Plane's main thread.
- Verify `requests` is available in XPython3's bundled Python before using it. If not, fall back to `urllib.request`.
- Command phase values: `0` = begin (key down), `1` = continue (held), `2` = end (key up). Only act on phase `0`.
- Return `1` from the command handler to allow other plugins and X-Plane to also process the command.
- `xp.log()` writes to `XPPython3Log.txt` — this is the only output mechanism needed.

---

## Installation Instructions (for pilot / README)

1. Copy the `fly_vdwaal/` folder to `X-Plane/Resources/plugins/PythonPlugins/`
2. Open `config.ini` in any text editor
3. Paste your API key from your fly.vdwaal.net profile page
4. Leave `backend_url` as `https://fly.vdwaal.net` (or set to `http://localhost:8000` for local dev)
5. Start X-Plane
6. Go to **Settings → Keyboard** (or Joystick) and search for `fly.vdwaal`
7. Bind `Check next checklist item` to your preferred button

---

## Testing Checklist

### Django side
- [ ] `UserProfile` migration applies cleanly
- [ ] Generate key → displays full key once, stores only hash + prefix
- [ ] Regenerate key → old key immediately invalid (hash replaced)
- [ ] `curl -X POST http://localhost:8000/api/plugin/check-next/ -H "Authorization: Bearer <key>"` → 200
- [ ] Wrong key → 401
- [ ] Valid key, no active session → 404 + Django log entry
- [ ] Valid key, active session → correct item marked checked, browser reflects it on next poll

### Plugin side
- [ ] Plugin loads without error in X-Plane developer console
- [ ] Command visible in X-Plane keyboard/joystick binding UI
- [ ] Button press with valid config → item advances in browser
- [ ] Button press with no session → console log only, no sim stutter
- [ ] Button press with wrong key → console log only
- [ ] Button press with `backend_url = http://localhost:8000` → works against local Django

---

## Dependencies

**Django:** no new packages — `secrets` and `hashers` are stdlib/Django built-ins.  
**Plugin:** `requests` must be available to XPython3. Verify with:
```python
import requests; print(requests.__version__)
```
in X-Plane's Python console. XPython3 typically ships with it; if not, install into XPython3's bundled Python.

---

## Resolved Questions

1. **Password confirmation before showing key?** — No, not for now. Generate button shows key immediately.
2. **Poll interval responsiveness?** — Target 1–2 seconds (tighten from the current 2–3s default). Implement this in phase 3-alpha alongside the endpoint so the button press feels immediate.
3. **One active session per user?** — Confirmed. The session model guarantees one active `FlightSession` per user at a time. A second browser login gets the same session. Two simultaneous X-Plane instances for one user is not a supported use case.

---

## What Comes Next (phase 3-beta, not in scope here)

- Session pairing flow (session key entered into plugin)
- Dataref polling loop (1–2 Hz)
- Watch list delivery from Django to plugin
- Auto-check resolution on backend
- WebSocket upgrade (v3.0)
