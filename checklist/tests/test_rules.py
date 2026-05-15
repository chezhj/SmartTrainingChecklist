"""Unit tests for checklist/rules.py — pure Python, no Django required."""
import unittest

from checklist.rules import (
    _AC_LAT_DATAREF,
    _AC_LON_DATAREF,
    _haversine_meters,
    collect_datarefs,
    collect_leaf_evaluations,
    evaluate_rule,
)

# LOWI 08 threshold used as FMC reference point throughout.
_REF_LAT = 47.2604
_REF_LON = 11.3436

_NEAR_RULE = {
    "op": "near",
    "ref_lat": "laminar/B738/fms/ref_runway_start_lat",
    "ref_lon": "laminar/B738/fms/ref_runway_start_lon",
    "meters": 200,
}

_COMPOUND_RULE = {
    "all": [
        _NEAR_RULE,
        {"dataref": "sim/flightmodel/position/y_agl", "op": "lt", "value": 5},
    ]
}


def _state(ac_lat, ac_lon, **extra):
    """Build a minimal dataref state dict with aircraft position set."""
    return {
        "laminar/B738/fms/ref_runway_start_lat": _REF_LAT,
        "laminar/B738/fms/ref_runway_start_lon": _REF_LON,
        _AC_LAT_DATAREF: ac_lat,
        _AC_LON_DATAREF: ac_lon,
        **extra,
    }


def _offset_lat(meters):
    """Return a latitude offset that puts the aircraft ~meters north of reference."""
    return _REF_LAT + meters / 111_320


class TestHaversineMeters(unittest.TestCase):

    def test_zero_distance(self):
        self.assertAlmostEqual(_haversine_meters(_REF_LAT, _REF_LON, _REF_LAT, _REF_LON), 0.0, places=3)

    def test_known_distance(self):
        # Moving ~150m north along latitude.
        result = _haversine_meters(_offset_lat(150), _REF_LON, _REF_LAT, _REF_LON)
        self.assertAlmostEqual(result, 150.0, delta=1.0)


class TestNearEvaluate(unittest.TestCase):

    def test_within_threshold_returns_true(self):
        state = _state(_offset_lat(150), _REF_LON)
        self.assertTrue(evaluate_rule(_NEAR_RULE, state))

    def test_beyond_threshold_returns_false(self):
        state = _state(_offset_lat(250), _REF_LON)
        self.assertFalse(evaluate_rule(_NEAR_RULE, state))

    def test_exactly_at_threshold_returns_false(self):
        # Compute the exact haversine distance for our chosen point, then set
        # threshold to that value — confirms strict < (not <=) semantics.
        ac_lat = _offset_lat(200)
        dist = _haversine_meters(ac_lat, _REF_LON, _REF_LAT, _REF_LON)
        rule = {**_NEAR_RULE, "meters": dist}
        state = _state(ac_lat, _REF_LON)
        self.assertFalse(evaluate_rule(rule, state))

    def test_fmc_sentinel_returns_false(self):
        state = {
            "laminar/B738/fms/ref_runway_start_lat": 0.0,
            "laminar/B738/fms/ref_runway_start_lon": 0.0,
            _AC_LAT_DATAREF: _offset_lat(50),
            _AC_LON_DATAREF: _REF_LON,
        }
        self.assertFalse(evaluate_rule(_NEAR_RULE, state))

    def test_missing_ref_datarefs_treats_as_sentinel(self):
        state = {_AC_LAT_DATAREF: _offset_lat(50), _AC_LON_DATAREF: _REF_LON}
        self.assertFalse(evaluate_rule(_NEAR_RULE, state))


class TestNearCollectDatarefs(unittest.TestCase):

    def test_yields_four_paths(self):
        paths = collect_datarefs(_NEAR_RULE)
        self.assertEqual(
            set(paths),
            {
                "laminar/B738/fms/ref_runway_start_lat",
                "laminar/B738/fms/ref_runway_start_lon",
                _AC_LAT_DATAREF,
                _AC_LON_DATAREF,
            },
        )

    def test_nested_in_all_yields_four_paths(self):
        paths = collect_datarefs(_COMPOUND_RULE)
        self.assertIn(_AC_LAT_DATAREF, paths)
        self.assertIn(_AC_LON_DATAREF, paths)
        self.assertIn("laminar/B738/fms/ref_runway_start_lat", paths)
        self.assertIn("laminar/B738/fms/ref_runway_start_lon", paths)


class TestNearInCompoundRule(unittest.TestCase):

    def test_all_fails_when_agl_too_high(self):
        state = _state(_offset_lat(150), _REF_LON, **{"sim/flightmodel/position/y_agl": 10})
        self.assertFalse(evaluate_rule(_COMPOUND_RULE, state))

    def test_all_passes_when_near_and_on_ground(self):
        state = _state(_offset_lat(150), _REF_LON, **{"sim/flightmodel/position/y_agl": 2})
        self.assertTrue(evaluate_rule(_COMPOUND_RULE, state))


class TestNearCollectLeafEvaluations(unittest.TestCase):

    def test_within_threshold_leaf(self):
        ac_lat = _offset_lat(143)
        state = _state(ac_lat, _REF_LON)
        leaves = collect_leaf_evaluations(_NEAR_RULE, state)
        self.assertEqual(len(leaves), 1)
        leaf = leaves[0]
        self.assertEqual(leaf["op"], "near")
        self.assertAlmostEqual(leaf["dist_m"], 143.0, delta=1.0)
        self.assertTrue(leaf["result"])

    def test_sentinel_leaf(self):
        state = {
            "laminar/B738/fms/ref_runway_start_lat": 0.0,
            "laminar/B738/fms/ref_runway_start_lon": 0.0,
            _AC_LAT_DATAREF: _offset_lat(50),
            _AC_LON_DATAREF: _REF_LON,
        }
        leaves = collect_leaf_evaluations(_NEAR_RULE, state)
        self.assertEqual(len(leaves), 1)
        leaf = leaves[0]
        self.assertIsNone(leaf["dist_m"])
        self.assertFalse(leaf["result"])


if __name__ == "__main__":
    unittest.main()
