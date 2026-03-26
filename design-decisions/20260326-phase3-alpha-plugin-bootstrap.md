# ADR-001: Phase 3-Alpha — xFlow Plugin Bootstrap & Manual Check-Next

**Date**: 2026-03-26
**Status**: Accepted
**Deciders**: h (project owner)

## Context

Phase 3-alpha establishes the first working end-to-end connection between X-Plane and the Django backend. The goal is deliberately minimal: one X-Plane command, one Django endpoint, one auth mechanism — no dataref reading, no auto-checking. This validates the full integration path before phase 3-beta (dataref automation).

The product is named **simFlow**. The X-Plane plugin component is named **xFlow** (`PI_xFlow.py`).

## Decision

### Auth: API key (Bearer token), hashed with PBKDF2

A static API key stored as a PBKDF2 hash on `UserProfile` (`api_key_hash`, `api_key_prefix`). The raw key is shown once after generation and never stored. The plugin sends it as `Authorization: Bearer <raw_key>`.

Chosen over session-token auth because this is machine-to-machine: the plugin has no browser context, no CSRF token, and no interactive login flow.

### Endpoint: `POST /api/plugin/check-next/`

Finds the active `FlightSession` for the authenticated user, resolves the current `active_phase` → `Procedure`, filters `CheckItem`s via `shouldshow()`, and marks the first unchecked visible item as `FlightItemState(status=checked, source=manual)`.

Also updates `FlightSession.last_plugin_contact` on every call — this is the only proof-of-life signal from the plugin in phase 3-alpha (no dataref loop yet), and the browser connection badge reads this field.

### Endpoint location: `checklist/plugin_views.py`

Separate from `api_views.py` (browser-facing). Keeps API-key auth isolated from session-key auth. This file will also host phase 3-beta plugin endpoints (`/api/plugin/push/`).

### Plugin: `xFlow/PI_xFlow.py` (XPPython3)

- Folder `xFlow/`, file `PI_xFlow.py` (XPPython3 requires `PI_` prefix for auto-load)
- Product brand: `simFlow`; plugin display name: `xFlow`
- `plugin_sig`: `xppython3.simflow`
- `plugin_desc`: `"simFlow – X-Plane checklist integration"`
- Command: `simflow/check_next_item` — bindable via X-Plane keyboard/joystick UI
- **Command name must not change after release — breaks user bindings**
- Default `backend_url` in `config.ini`: `http://cortado:8300` (local dev; pilot changes for production)
- `PLACEHOLDER` sentinel: the literal string `"paste-your-key-here"` that ships in `config.ini`; checked on command fire to guard against unconfigured installs logging a confusing 401
- HTTP: daemon thread (`threading.Thread(daemon=True)`), never blocks X-Plane main thread
- HTTP library: `requests` preferred, `urllib.request` fallback if not available
- No sim UI (no widgets, no menus)
- Follows PI_SimBrief2Zibo.py patterns: `EasyCommand` wrapper, `xp.log()` for all output

### Poll interval: 1500ms

Tightened from 2500ms. The spec targets 1–2 seconds; 1500ms gives responsive feedback after a button press without hammering the server.

## Options Considered

**Option A — inline in `api_views.py`**: Rejected because it mixes browser-session auth and API-key auth in one file. Acceptable for a single endpoint but creates confusion as plugin API surface grows in phase 3-beta.

**Option C — `@require_api_key` decorator**: Rejected as premature abstraction. One endpoint doesn't justify a new decorator pattern. Revisit in phase 3-beta when `/api/plugin/push/` lands.

## Consequences

- `UserProfile` gains `api_key_hash` + `api_key_prefix` fields — migration required
- Plugin filename is `PI_xFlow.py`, not `xFlow.py` (XPPython3 constraint)
- `check-next` only works for authenticated users — anonymous sessions cannot use the plugin in phase 3-alpha
- `active_phase` is a forward-only frontier updated by the browser navigation flow (confirmed: `views.py:487`)
- Command name `simflow/check_next_item` must not change after release — breaks user key bindings
- Default backend URL is `http://cortado:8300` (local dev); pilots deploying against production must update `config.ini`

## Assumptions at Time of Decision

- `CheckItem.shouldshow()` takes `list[int]` of attribute IDs (medium confidence — assumed from `procedure_detail` usage)
- `requests` is available in XPPython3's bundled Python (medium confidence — `urllib.request` fallback implemented)
- `active_phase` is maintained by the browser navigation flow — **confirmed** (`views.py:481–488`: forward-only frontier, updated on each `procedure_detail` load)
