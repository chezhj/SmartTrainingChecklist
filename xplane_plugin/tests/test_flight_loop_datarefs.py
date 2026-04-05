"""
Unit tests for PI_xFlow flight-loop dataref reading.

Mocks the `xp` module so no X-Plane installation is required.
Focuses on the string-dataref (Type_Data / getDatas) branch.
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, call, patch


# ---------------------------------------------------------------------------
# Minimal xp stub — only the surface the flight loop touches.
# ---------------------------------------------------------------------------

def _make_xp_stub():
    xp = types.ModuleType("xp")
    xp.Type_Data   = 32          # bitmask for string datarefs
    xp.findDataRef  = MagicMock()
    xp.getDataRefTypes = MagicMock(return_value=0)   # float by default
    xp.getDataf    = MagicMock(return_value=0.0)
    xp.getDatas    = MagicMock(return_value="")
    xp.getDatavf   = MagicMock()
    xp.log         = MagicMock()
    xp.getSystemPath = MagicMock(return_value="/tmp/xplane")
    xp.registerFlightLoopCallback  = MagicMock()
    xp.unregisterFlightLoopCallback = MagicMock()
    xp.createCommand         = MagicMock(return_value=object())
    xp.registerCommandHandler = MagicMock()
    xp.unregisterCommandHandler = MagicMock()
    return xp


class TestFlightLoopStringDataref(unittest.TestCase):

    def setUp(self):
        # Inject the stub before importing the plugin module
        self.xp_stub = _make_xp_stub()
        sys.modules["xp"] = self.xp_stub
        sys.modules["XPPython3"] = types.ModuleType("XPPython3")
        sys.modules["XPPython3.xp"] = self.xp_stub

        # Make sure the plugin module is freshly imported each test
        if "xplane_plugin.xFlow.PI_xFlow" in sys.modules:
            del sys.modules["xplane_plugin.xFlow.PI_xFlow"]
        if "PI_xFlow" in sys.modules:
            del sys.modules["PI_xFlow"]

        import importlib.util, pathlib
        spec = importlib.util.spec_from_file_location(
            "PI_xFlow",
            pathlib.Path(__file__).parent.parent / "xFlow" / "PI_xFlow.py",
        )
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)

    def _make_plugin(self):
        """Return a PythonInterface with session_id pre-set so the loop runs."""
        # Patch configparser so __init__ doesn't need a real config.ini
        with patch("configparser.ConfigParser.read"):
            plugin = self.module.PythonInterface()
        plugin._session_id = 1
        plugin._api_key = "test-key"
        return plugin

    # -----------------------------------------------------------------------
    # getDatas returns a str directly — verify the loop uses it correctly
    # -----------------------------------------------------------------------

    def test_string_dataref_uses_getDatas_return_value(self):
        """getDatas return value is stored in state without bytearray decode."""
        xp = self.xp_stub
        xp.findDataRef.return_value = object()
        xp.getDataRefTypes.return_value = 32          # Type_Data → string path
        xp.getDatas.return_value = "737-800W.1\x00\x00"

        plugin = self._make_plugin()
        plugin._watch = ["laminar/B738/fmc1/Line01_L"]

        posted = {}

        def fake_post(state):
            posted.update(state)

        with patch.object(plugin, "_post_state", side_effect=fake_post):
            plugin._flight_loop(1.0, 1.0, 1, None)

        self.assertEqual(posted.get("laminar/B738/fmc1/Line01_L"), "737-800W.1")

    def test_getDatas_called_with_correct_args(self):
        """getDatas must be called as getDatas(dref, 0, 64) — not with a bytearray."""
        xp = self.xp_stub
        fake_dref = object()
        xp.findDataRef.return_value = fake_dref
        xp.getDataRefTypes.return_value = 32
        xp.getDatas.return_value = "IDENT"

        plugin = self._make_plugin()
        plugin._watch = ["laminar/B738/fmc1/Line01_L"]

        with patch.object(plugin, "_post_state"):
            plugin._flight_loop(1.0, 1.0, 1, None)

        xp.getDatas.assert_called_once_with(fake_dref, 0, 64)

    def test_getDatas_offset_is_int_not_bytearray(self):
        """Regression: second argument to getDatas must be an int, never a bytearray."""
        xp = self.xp_stub
        xp.findDataRef.return_value = object()
        xp.getDataRefTypes.return_value = 32
        xp.getDatas.return_value = ""

        plugin = self._make_plugin()
        plugin._watch = ["laminar/B738/fmc1/Line01_L"]

        with patch.object(plugin, "_post_state"):
            plugin._flight_loop(1.0, 1.0, 1, None)

        _, args, _ = xp.getDatas.mock_calls[0]
        offset_arg = args[1]
        self.assertIsInstance(
            offset_arg, int,
            f"getDatas offset arg must be int, got {type(offset_arg).__name__}"
        )

    def test_string_dataref_stripped(self):
        """Null bytes and surrounding whitespace are stripped from the value."""
        xp = self.xp_stub
        xp.findDataRef.return_value = object()
        xp.getDataRefTypes.return_value = 32
        xp.getDatas.return_value = "  IDENT  \x00\x00\x00"

        plugin = self._make_plugin()
        plugin._watch = ["some/cdu/line"]

        posted = {}
        with patch.object(plugin, "_post_state", side_effect=posted.update):
            plugin._flight_loop(1.0, 1.0, 1, None)

        self.assertEqual(posted.get("some/cdu/line"), "IDENT")

    # -----------------------------------------------------------------------
    # Float dataref — ensure getDatas is NOT called for non-string datarefs
    # -----------------------------------------------------------------------

    def test_float_dataref_uses_getDataf(self):
        xp = self.xp_stub
        xp.findDataRef.return_value = object()
        xp.getDataRefTypes.return_value = 0   # not Type_Data
        xp.getDataf.return_value = 42.0

        plugin = self._make_plugin()
        plugin._watch = ["sim/some/float"]

        posted = {}
        with patch.object(plugin, "_post_state", side_effect=posted.update):
            plugin._flight_loop(1.0, 1.0, 1, None)

        xp.getDatas.assert_not_called()
        self.assertEqual(posted.get("sim/some/float"), 42.0)


if __name__ == "__main__":
    unittest.main()
