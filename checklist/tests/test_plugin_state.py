"""Tests for POST /api/plugin/state/ (plugin_views.plugin_state)."""

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import json
from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from checklist.models import (
    FlightItemState,
    FlightSession,
    FlightSessionAttribute,
    Procedure,
    generate_api_key,
)
from checklist.tests.testFactories import AttributeFactory, CheckItemFactory

User = get_user_model()
URL = reverse("checklist:api_plugin_state")

RULE_PARKING_BRAKE_ON = {
    "dataref": "sim/cockpit/switches/parking_brake",
    "op": "eq",
    "value": 1,
}
RULE_PARKING_BRAKE_OFF = {
    "dataref": "sim/cockpit/switches/parking_brake",
    "op": "eq",
    "value": 0,
}


def _post(client, body, key=None):
    kwargs = {"content_type": "application/json"}
    if key is not None:
        kwargs["HTTP_AUTHORIZATION"] = f"Bearer {key}"
    return client.post(URL, data=json.dumps(body), **kwargs)


class _Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="pilot", password="pw")
        self.profile = self.user.profile
        raw, hashed, prefix = generate_api_key()
        self.raw_key = raw
        self.profile.api_key_hash = hashed
        self.profile.api_key_prefix = prefix
        self.profile.save()

        self.procedure = Procedure.objects.create(
            title="Before Start", step=1, slug="before-start"
        )
        self.session = FlightSession.objects.create(
            user_profile=self.profile, active_phase="before-start", is_active=True
        )

    def _valid_body(self, datarefs=None):
        return {"session_id": self.session.pk, "datarefs": datarefs or {}}


class TestPluginStateAuth(_Base):

    def test_missing_auth_returns_401(self):
        resp = _post(self.client, self._valid_body())
        self.assertEqual(resp.status_code, 401)

    def test_wrong_key_returns_401(self):
        resp = _post(self.client, self._valid_body(), key="fvw_wrongkey")
        self.assertEqual(resp.status_code, 401)

    def test_get_returns_405(self):
        resp = self.client.get(URL, HTTP_AUTHORIZATION=f"Bearer {self.raw_key}")
        self.assertEqual(resp.status_code, 405)


class TestPluginStateBodyValidation(_Base):

    def test_invalid_json_returns_400(self):
        resp = self.client.post(
            URL,
            data="not json",
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.raw_key}",
        )
        self.assertEqual(resp.status_code, 400)

    def test_missing_session_id_returns_400(self):
        resp = _post(self.client, {"datarefs": {}}, key=self.raw_key)
        self.assertEqual(resp.status_code, 400)

    def test_non_integer_session_id_returns_400(self):
        resp = _post(self.client, {"session_id": "abc", "datarefs": {}}, key=self.raw_key)
        self.assertEqual(resp.status_code, 400)

    def test_missing_datarefs_returns_400(self):
        resp = _post(self.client, {"session_id": self.session.pk}, key=self.raw_key)
        self.assertEqual(resp.status_code, 400)

    def test_non_dict_datarefs_returns_400(self):
        resp = _post(self.client, {"session_id": self.session.pk, "datarefs": [1, 2]}, key=self.raw_key)
        self.assertEqual(resp.status_code, 400)


class TestPluginStateSessionLookup(_Base):

    def test_unknown_session_id_returns_404(self):
        resp = _post(self.client, {"session_id": 99999, "datarefs": {}}, key=self.raw_key)
        self.assertEqual(resp.status_code, 404)

    def test_inactive_session_returns_404(self):
        self.session.is_active = False
        self.session.save()
        resp = _post(self.client, self._valid_body(), key=self.raw_key)
        self.assertEqual(resp.status_code, 404)

    def test_session_belonging_to_other_user_returns_404(self):
        other = User.objects.create_user(username="other", password="pw")
        other_session = FlightSession.objects.create(
            user_profile=other.profile, active_phase="before-start", is_active=True
        )
        resp = _post(
            self.client,
            {"session_id": other_session.pk, "datarefs": {}},
            key=self.raw_key,
        )
        self.assertEqual(resp.status_code, 404)


class TestPluginStateHappyPath(_Base):

    def test_returns_ok_with_empty_checked_and_watch_when_no_rules(self):
        CheckItemFactory(procedure=self.procedure, step=1)
        resp = _post(self.client, self._valid_body(), key=self.raw_key)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["checked"], [])
        self.assertEqual(data["watch"], [])

    def test_updates_last_plugin_contact(self):
        before = datetime.now(tz=timezone.utc)
        _post(self.client, self._valid_body(), key=self.raw_key)
        self.session.refresh_from_db()
        self.assertIsNotNone(self.session.last_plugin_contact)
        self.assertGreaterEqual(self.session.last_plugin_contact, before)

    def test_updates_last_plugin_contact_even_with_empty_active_phase(self):
        self.session.active_phase = ""
        self.session.save()
        before = datetime.now(tz=timezone.utc)
        _post(self.client, self._valid_body(), key=self.raw_key)
        self.session.refresh_from_db()
        self.assertGreaterEqual(self.session.last_plugin_contact, before)

    def test_empty_active_phase_returns_empty_watch(self):
        self.session.active_phase = ""
        self.session.save()
        resp = _post(self.client, self._valid_body(), key=self.raw_key)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["watch"], [])

    def test_unknown_active_phase_slug_returns_empty_watch(self):
        self.session.active_phase = "no-such-phase"
        self.session.save()
        resp = _post(self.client, self._valid_body(), key=self.raw_key)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["watch"], [])


class TestPluginStateRuleEvaluation(_Base):

    def test_matching_rule_creates_auto_checked_state(self):
        item = CheckItemFactory(
            procedure=self.procedure, step=1, auto_check_rule=RULE_PARKING_BRAKE_ON
        )
        datarefs = {"sim/cockpit/switches/parking_brake": 1}
        resp = _post(self.client, {"session_id": self.session.pk, "datarefs": datarefs}, key=self.raw_key)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(item.pk, resp.json()["checked"])
        state = FlightItemState.objects.get(flight_session=self.session, checklist_item=item)
        self.assertEqual(state.status, "checked")
        self.assertEqual(state.source, "auto")
        self.assertIsNotNone(state.checked_at)

    def test_non_matching_rule_does_not_check_item(self):
        item = CheckItemFactory(
            procedure=self.procedure, step=1, auto_check_rule=RULE_PARKING_BRAKE_ON
        )
        datarefs = {"sim/cockpit/switches/parking_brake": 0}
        resp = _post(self.client, {"session_id": self.session.pk, "datarefs": datarefs}, key=self.raw_key)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(item.pk, resp.json()["checked"])
        self.assertFalse(
            FlightItemState.objects.filter(flight_session=self.session, checklist_item=item).exists()
        )

    def test_already_checked_item_not_in_newly_checked(self):
        item = CheckItemFactory(
            procedure=self.procedure, step=1, auto_check_rule=RULE_PARKING_BRAKE_ON
        )
        FlightItemState.objects.create(
            flight_session=self.session,
            checklist_item=item,
            status="checked",
            source="manual",
            checked_at=datetime.now(tz=timezone.utc),
        )
        datarefs = {"sim/cockpit/switches/parking_brake": 1}
        resp = _post(self.client, {"session_id": self.session.pk, "datarefs": datarefs}, key=self.raw_key)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(item.pk, resp.json()["checked"])

    def test_already_checked_item_still_appears_in_watch(self):
        item = CheckItemFactory(
            procedure=self.procedure, step=1, auto_check_rule=RULE_PARKING_BRAKE_ON
        )
        FlightItemState.objects.create(
            flight_session=self.session,
            checklist_item=item,
            status="checked",
            source="manual",
            checked_at=datetime.now(tz=timezone.utc),
        )
        resp = _post(self.client, self._valid_body(), key=self.raw_key)
        self.assertIn("sim/cockpit/switches/parking_brake", resp.json()["watch"])

    def test_missing_dataref_in_state_does_not_check_item(self):
        item = CheckItemFactory(
            procedure=self.procedure, step=1, auto_check_rule=RULE_PARKING_BRAKE_ON
        )
        resp = _post(self.client, self._valid_body(), key=self.raw_key)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(item.pk, resp.json()["checked"])

    def test_item_without_rule_not_in_watch(self):
        CheckItemFactory(procedure=self.procedure, step=1)
        resp = _post(self.client, self._valid_body(), key=self.raw_key)
        self.assertEqual(resp.json()["watch"], [])

    def test_watch_list_deduplicates_shared_datarefs(self):
        rule = RULE_PARKING_BRAKE_ON
        CheckItemFactory(procedure=self.procedure, step=1, auto_check_rule=rule)
        CheckItemFactory(procedure=self.procedure, step=2, auto_check_rule=rule)
        resp = _post(self.client, self._valid_body(), key=self.raw_key)
        watch = resp.json()["watch"]
        self.assertEqual(watch.count("sim/cockpit/switches/parking_brake"), 1)

    def test_compound_all_rule_fires_when_all_conditions_met(self):
        rule = {
            "all": [
                {"dataref": "sim/parking_brake", "op": "eq", "value": 1},
                {"dataref": "sim/throttle", "op": "lte", "value": 0.05},
            ]
        }
        item = CheckItemFactory(procedure=self.procedure, step=1, auto_check_rule=rule)
        datarefs = {"sim/parking_brake": 1, "sim/throttle": 0.0}
        resp = _post(self.client, {"session_id": self.session.pk, "datarefs": datarefs}, key=self.raw_key)
        self.assertIn(item.pk, resp.json()["checked"])

    def test_compound_all_rule_does_not_fire_when_one_condition_fails(self):
        rule = {
            "all": [
                {"dataref": "sim/parking_brake", "op": "eq", "value": 1},
                {"dataref": "sim/throttle", "op": "lte", "value": 0.05},
            ]
        }
        item = CheckItemFactory(procedure=self.procedure, step=1, auto_check_rule=rule)
        datarefs = {"sim/parking_brake": 1, "sim/throttle": 0.5}
        resp = _post(self.client, {"session_id": self.session.pk, "datarefs": datarefs}, key=self.raw_key)
        self.assertNotIn(item.pk, resp.json()["checked"])

    def test_compound_any_rule_fires_when_one_condition_met(self):
        rule = {
            "any": [
                {"dataref": "sim/parking_brake", "op": "eq", "value": 1},
                {"dataref": "sim/throttle", "op": "lte", "value": 0.05},
            ]
        }
        item = CheckItemFactory(procedure=self.procedure, step=1, auto_check_rule=rule)
        datarefs = {"sim/parking_brake": 0, "sim/throttle": 0.0}
        resp = _post(self.client, {"session_id": self.session.pk, "datarefs": datarefs}, key=self.raw_key)
        self.assertIn(item.pk, resp.json()["checked"])


class TestPluginStateAttributeFiltering(_Base):

    def test_item_with_inactive_attribute_not_auto_checked(self):
        attr = AttributeFactory()
        item = CheckItemFactory(
            procedure=self.procedure, step=1,
            attributes=[attr], auto_check_rule=RULE_PARKING_BRAKE_ON
        )
        # No FlightSessionAttribute row → attribute not active
        datarefs = {"sim/cockpit/switches/parking_brake": 1}
        resp = _post(self.client, {"session_id": self.session.pk, "datarefs": datarefs}, key=self.raw_key)
        self.assertNotIn(item.pk, resp.json()["checked"])

    def test_item_with_active_attribute_is_auto_checked(self):
        attr = AttributeFactory()
        item = CheckItemFactory(
            procedure=self.procedure, step=1,
            attributes=[attr], auto_check_rule=RULE_PARKING_BRAKE_ON
        )
        FlightSessionAttribute.objects.create(
            flight_session=self.session, attribute=attr, is_active=True
        )
        datarefs = {"sim/cockpit/switches/parking_brake": 1}
        resp = _post(self.client, {"session_id": self.session.pk, "datarefs": datarefs}, key=self.raw_key)
        self.assertIn(item.pk, resp.json()["checked"])

    def test_item_with_inactive_attribute_not_in_watch(self):
        attr = AttributeFactory()
        CheckItemFactory(
            procedure=self.procedure, step=1,
            attributes=[attr], auto_check_rule=RULE_PARKING_BRAKE_ON
        )
        resp = _post(self.client, self._valid_body(), key=self.raw_key)
        self.assertEqual(resp.json()["watch"], [])
