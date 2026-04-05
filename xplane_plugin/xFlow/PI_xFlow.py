"""
xFlow — simFlow X-Plane plugin
Phase 3: flight loop dataref monitoring + manual check-next command.

Installation:
  Copy the xFlow/ folder to:
    X-Plane 12/Resources/plugins/PythonPlugins/

  Edit config.ini:
    api_key     — paste your key from the simFlow profile page
    backend_url — leave as-is for local dev; change for production
    log_level   — DEBUG / INFO / ERROR (default: INFO)
                  DEBUG shows watch list contents, dataref values, raw responses

Commands registered:
  simflow/check_next_item
  Bind via X-Plane Settings → Keyboard or Joystick.
"""

from __future__ import annotations

import configparser
import json
import re
import threading
import urllib.error
import urllib.request
from pathlib import Path

_ARRAY_RE = re.compile(r'^(.+)\[(\d+)\]$')

try:
    from XPPython3 import xp
except ImportError:
    print("xp module not found")

try:
    import requests
    _USE_REQUESTS = True
except ImportError:
    _USE_REQUESTS = False

# ── Plugin identity ────────────────────────────────────────────────────────── #

plugin_name = "xFlow"
plugin_sig  = "xppython3.simflow"
plugin_desc = "simFlow – X-Plane checklist integration"

# ── Command ────────────────────────────────────────────────────────────────── #

_COMMAND_FULL = "simflow/check_next_item"
_COMMAND_DESC = "simFlow – Check next checklist item"

# ── Flight loop interval ───────────────────────────────────────────────────── #

_LOOP_INTERVAL = 1.0   # seconds; reschedule rate returned from flight loop

# ── Log levels ─────────────────────────────────────────────────────────────── #

_LEVELS = {"DEBUG": 0, "INFO": 1, "ERROR": 2}

# ── Config sentinel ────────────────────────────────────────────────────────── #
#
# PLACEHOLDER is the literal string that ships in config.ini.
# Guards against firing requests on an unconfigured install.

PLACEHOLDER = "paste-your-key-here"


# ── Command wrapper ────────────────────────────────────────────────────────── #

class CheckCommand:
    """
    Creates and registers a single X-Plane command.
    The callback receives the phase (0=begin, 1=continue, 2=end).
    The handler always returns 1 (pass-through) so other plugins and
    X-Plane itself can still process the same binding.
    """

    def __init__(self, name: str, description: str, callback):
        self._cmd = xp.createCommand(name, description)
        self._handler = self._on_command
        self._callback = callback
        xp.registerCommandHandler(self._cmd, self._handler, 1, 0)

    def _on_command(self, cmd, phase, ref):
        self._callback(phase)
        return 1  # always pass through

    def destroy(self):
        xp.unregisterCommandHandler(self._cmd, self._handler, 1, 0)


# ── Plugin ─────────────────────────────────────────────────────────────────── #

class PythonInterface:

    def __init__(self):
        config_path = (
            Path(xp.getSystemPath())
            / "Resources/plugins/PythonPlugins/xFlow/config.ini"
        )
        cfg = configparser.ConfigParser()
        cfg.read(config_path)
        self._api_key      = cfg.get("xflow", "api_key",     fallback=PLACEHOLDER)
        self._backend_url  = cfg.get("xflow", "backend_url", fallback="http://cortado:8300")
        raw_level          = cfg.get("xflow", "log_level",   fallback="INFO").upper()
        self._log_level    = _LEVELS.get(raw_level, _LEVELS["INFO"])
        self._check_cmd    = CheckCommand(_COMMAND_FULL, _COMMAND_DESC, self._on_check_next)

        # Session state — populated by _fetch_session()
        self._session_id: int | None = None

        # Watch list: dataref path → cached XP DataRef handle
        # Populated from server responses; starts empty.
        self._watch: list[str] = []
        self._drefs: dict[str, object] = {}   # path → xp.findDataRef() result

        # Last sent values — used to detect changes before POSTing
        self._last_values: dict[str, float | str] = {}

        # Serialise all HTTP work onto one daemon thread
        self._lock = threading.Lock()

    # ── Logging helper ─────────────────────────────────────────────────────── #

    def _log(self, level: str, msg: str) -> None:
        """Emit msg to X-Plane Log.txt only if level >= configured log_level."""
        if _LEVELS.get(level, 0) >= self._log_level:
            xp.log(f"[xFlow] {msg}")

    # ── XPPython3 lifecycle ────────────────────────────────────────────────── #

    def XPluginStart(self):
        return plugin_name, plugin_sig, plugin_desc

    def XPluginEnable(self):
        self._log("INFO", f"ready — backend: {self._backend_url}")
        # Register the flight loop callback
        xp.registerFlightLoopCallback(self._flight_loop, _LOOP_INTERVAL, 0)
        # Kick off session discovery in the background so we don't block enable
        threading.Thread(target=self._fetch_session, daemon=True).start()
        return 1

    def XPluginDisable(self):
        xp.unregisterFlightLoopCallback(self._flight_loop, 0)

    def XPluginStop(self):
        self._check_cmd.destroy()

    # ── Flight loop ────────────────────────────────────────────────────────── #

    def _flight_loop(self, since_last: float, elapsed: float, counter: int, ref) -> float:
        """
        Called by X-Plane at ~1 Hz. Reads the current watch list datarefs
        and POSTs to /api/plugin/state/. If the watch list is empty the POST
        still fires (with datarefs: {}) so the server can return the initial
        watch list and record last_plugin_contact (keeps the connection badge alive).
        """
        if self._session_id is None:
            return _LOOP_INTERVAL

        state: dict[str, float | str] = {}
        changed = False

        for path in self._watch:
            m = _ARRAY_RE.match(path)
            if m:
                base, idx = m.group(1), int(m.group(2))
                dref = self._drefs.get(path)
                if dref is None:
                    dref = xp.findDataRef(base)
                    if dref is None:
                        self._log("DEBUG", f"dataref not found: {base}")
                        continue
                    self._drefs[path] = dref
                buf = [0.0] * (idx + 1)
                xp.getDatavf(dref, buf, 0, idx + 1)
                val = buf[idx]
            else:
                dref = self._drefs.get(path)
                if dref is None:
                    dref = xp.findDataRef(path)
                    if dref is None:
                        self._log("DEBUG", f"dataref not found: {path}")
                        continue
                    self._drefs[path] = dref
                # xp.Type_Data (32) = byte-array / string dataref (CDU lines etc.)
                # getDatas(dataRef, offset, count) returns a str directly.
                if xp.getDataRefTypes(dref) & 32:
                    val = xp.getDatas(dref, 0, 64).rstrip("\x00").strip()
                else:
                    val = xp.getDataf(dref)

            state[path] = val
            if self._last_values.get(path) != val:
                changed = True

        self._last_values = state

        # Always POST — keeps last_plugin_contact fresh (heartbeat) and
        # bootstraps the watch list on first tick. Dataref data is small enough
        # that 1 POST/s to a local server is negligible.
        self._log("DEBUG", f"POSTing {len(state)} datarefs (changed={changed})")
        snapshot = dict(state)
        threading.Thread(
            target=self._post_state, args=(snapshot,), daemon=True
        ).start()

        return _LOOP_INTERVAL

    # ── Command handler ────────────────────────────────────────────────────── #

    def _on_check_next(self, phase: int):
        if phase != 0:      # 0=BEGIN (key down); ignore CONTINUE and END
            return
        threading.Thread(target=self._post_check_next, daemon=True).start()

    # ── HTTP workers (daemon threads) ──────────────────────────────────────── #

    def _fetch_session(self) -> None:
        """
        GET /api/plugin/session/ — discover active session id on startup.
        Retries silently; the flight loop simply does nothing until session_id
        is set. Called again automatically when state POST returns 404.
        """
        if not self._api_key or self._api_key == PLACEHOLDER:
            self._log("ERROR", "api_key not set — edit config.ini")
            return

        url     = self._backend_url.rstrip("/") + "/api/plugin/session/"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        self._log("DEBUG", f"GET {url}")
        try:
            status, body = self._http_get(url, headers)
        except Exception as exc:
            self._log("ERROR", _classify_error(exc))
            return

        self._log("DEBUG", f"session response status {status}")

        if status == 200:
            with self._lock:
                self._session_id = body.get("session_id")
            self._log("INFO", f"session {self._session_id} — phase: {body.get('active_phase')}")
        elif status == 404:
            self._log("INFO", "no active session — waiting for pilot to start checklist")
        elif status == 401:
            self._log("ERROR", "authentication failed — check api_key in config.ini")
        else:
            self._log("INFO", f"session lookup returned {status}")

    def _post_state(self, state: dict[str, float]) -> None:
        """
        POST /api/plugin/state/ with current dataref values.
        Updates the watch list from the server response.
        On 404, clears session_id so _fetch_session is retried next loop.
        """
        with self._lock:
            session_id = self._session_id

        if session_id is None:
            return

        url     = self._backend_url.rstrip("/") + "/api/plugin/state/"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body    = {"session_id": session_id, "datarefs": state}

        self._log("DEBUG", f"POST {url}")
        try:
            status, data = self._http_post_json(url, headers, body)
        except Exception as exc:
            self._log("ERROR", _classify_error(exc))
            return

        self._log("DEBUG", f"state response status {status}")

        if status == 200:
            newly_checked = data.get("checked", [])
            new_watch     = data.get("watch", [])
            if newly_checked:
                self._log("DEBUG", f"auto-checked items: {newly_checked}")
            if new_watch != self._watch:
                with self._lock:
                    self._watch = new_watch
                    # Clear stale dref handles for paths no longer watched
                    self._drefs = {p: v for p, v in self._drefs.items() if p in new_watch}
        elif status == 401:
            self._log("ERROR", "authentication failed — check api_key in config.ini")
        elif status == 404:
            self._log("INFO", "session expired — re-fetching session")
            with self._lock:
                self._session_id = None
            threading.Thread(target=self._fetch_session, daemon=True).start()
        else:
            self._log("INFO", f"unexpected status {status}")

    def _post_check_next(self) -> None:
        if not self._api_key or self._api_key == PLACEHOLDER:
            self._log("ERROR", "api_key not set — edit config.ini")
            return

        url     = self._backend_url.rstrip("/") + "/api/plugin/check-next/"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        self._log("DEBUG", f"POST {url}")

        try:
            status, _ = self._http_post_json(url, headers, None)
        except Exception as exc:
            self._log("ERROR", _classify_error(exc))
            return

        self._log("DEBUG", f"check-next response status {status}")

        if status == 200:
            pass  # success — visible at DEBUG via the line above
        elif status == 204:
            self._log("INFO", "phase complete — nothing left to check")
        elif status == 401:
            self._log("ERROR", "authentication failed — check api_key in config.ini")
        elif status == 404:
            self._log("INFO", "no active flight session")
        else:
            self._log("INFO", f"unexpected status {status}")

    # ── HTTP primitives ────────────────────────────────────────────────────── #

    @staticmethod
    def _http_get(url: str, headers: dict) -> tuple[int, dict]:
        """GET url. Returns (status_code, parsed_json_body)."""
        if _USE_REQUESTS:
            resp = requests.get(url, headers=headers, timeout=5)
            try:
                body = resp.json()
            except Exception:
                body = {}
            return resp.status_code, body

        req = urllib.request.Request(url, method="GET", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read()
                try:
                    body = json.loads(raw)
                except Exception:
                    body = {}
                return resp.status, body
        except urllib.error.HTTPError as exc:
            return exc.code, {}

    @staticmethod
    def _http_post_json(url: str, headers: dict, body) -> tuple[int, dict]:
        """
        POST url with optional JSON body.
        Returns (status_code, parsed_json_body).
        Raises on network/timeout errors.
        """
        if _USE_REQUESTS:
            resp = requests.post(url, headers=headers, json=body, timeout=5)
            try:
                data = resp.json()
            except Exception:
                data = {}
            return resp.status_code, data

        payload = json.dumps(body).encode() if body is not None else b""
        h = dict(headers)
        h.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(url, method="POST", headers=h, data=payload)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                raw = resp.read()
                try:
                    data = json.loads(raw)
                except Exception:
                    data = {}
                return resp.status, data
        except urllib.error.HTTPError as exc:
            return exc.code, {}


# ── Error classifier (module-level, no state needed) ──────────────────────── #

def _classify_error(exc: Exception) -> str:
    """
    Map a network exception to a human-readable log fragment.
    Works for both requests and urllib exceptions without importing
    requests-specific types when requests is unavailable.
    """
    exc_type = type(exc).__name__.lower()
    if "timeout" in exc_type or isinstance(exc, TimeoutError):
        return "request timed out"
    if isinstance(exc, OSError):
        return "could not reach backend"
    return f"request error: {exc}"
