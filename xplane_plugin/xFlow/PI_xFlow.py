"""
xFlow — simFlow X-Plane plugin
Phase 3-alpha: manual "check next item" command via joystick/keyboard binding.

Installation:
  Copy the xFlow/ folder to:
    X-Plane 12/Resources/plugins/PythonPlugins/

  Edit config.ini:
    api_key    — paste your key from the simFlow profile page
    backend_url — leave as-is for local dev; change for production

Command registered:
  simflow/check_next_item
  Bind via X-Plane Settings → Keyboard or Joystick.
"""

from __future__ import annotations

import configparser
import threading
import urllib.error
import urllib.request
from pathlib import Path

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

# ── Config sentinel ────────────────────────────────────────────────────────── #
#
# PLACEHOLDER is the literal string that ships in config.ini.
# _post_check_next checks for it so an unconfigured install logs a clear
# warning ("api_key not set") instead of firing a request and getting 401.

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
        self._api_key     = cfg.get("xflow", "api_key",     fallback=PLACEHOLDER)
        self._backend_url = cfg.get("xflow", "backend_url", fallback="http://cortado:8300")
        self._check_cmd   = CheckCommand(_COMMAND_FULL, _COMMAND_DESC, self._on_check_next)

    def XPluginStart(self):
        return plugin_name, plugin_sig, plugin_desc

    def XPluginEnable(self):
        xp.log(f"[xFlow] ready — backend: {self._backend_url}")
        return 1

    def XPluginDisable(self):
        pass

    def XPluginStop(self):
        self._check_cmd.destroy()

    # ── Command handler ────────────────────────────────────────────────────── #

    def _on_check_next(self, phase: int):
        if phase != 0:      # 0=BEGIN (key down); ignore CONTINUE and END
            return
        threading.Thread(target=self._post_check_next, daemon=True).start()

    # ── HTTP worker (daemon thread) ────────────────────────────────────────── #

    def _post_check_next(self):
        if not self._api_key or self._api_key == PLACEHOLDER:
            xp.log("[xFlow] api_key not set — edit config.ini")
            return

        url     = self._backend_url.rstrip("/") + "/api/plugin/check-next/"
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            status = self._http_post(url, headers)
        except Exception as exc:
            xp.log(f"[xFlow] {_classify_error(exc)}")
            return

        if status == 200:
            pass  # success is silent
        elif status == 204:
            xp.log("[xFlow] phase complete — nothing left to check")
        elif status == 401:
            xp.log("[xFlow] authentication failed — check api_key in config.ini")
        elif status == 404:
            xp.log("[xFlow] no active flight session")
        else:
            xp.log(f"[xFlow] unexpected status {status}")

    @staticmethod
    def _http_post(url: str, headers: dict) -> int:
        """
        POST to url. Returns the HTTP status code.
        Raises on network/timeout errors; caller handles logging.
        urllib.error.HTTPError (4xx/5xx) is caught here and converted to a
        status code so the caller's status-switch runs for all responses.
        """
        if _USE_REQUESTS:
            return requests.post(url, headers=headers, timeout=5).status_code

        req = urllib.request.Request(url, method="POST", headers=headers, data=b"")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            return exc.code     # 4xx / 5xx — not a network failure


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
