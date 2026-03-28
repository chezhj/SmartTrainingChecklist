"""Tests for /api/check, /api/uncheck, and /api/poll endpoints."""

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import json
from datetime import datetime, timedelta, timezone

from django.test import TestCase
from django.urls import reverse

from checklist.models import CheckItem, FlightItemState, FlightSession, Procedure
from checklist.tests.testFactories import CheckItemFactory


def _post_json(client, url, data, session_key=None):
    """Helper: POST JSON to url, optionally setting flight_session_key in session first."""
    if session_key:
        session = client.session
        session["flight_session_key"] = session_key
        session.save()
    return client.post(
        url,
        data=json.dumps(data),
        content_type="application/json",
    )


def _set_session_key(client, session_key):
    """Helper: write flight_session_key into the Django test session."""
    session = client.session
    session["flight_session_key"] = session_key
    session.save()


def _get_poll(client, procedure_slug="before-start", since=0):
    return client.get(
        reverse("checklist:api_poll"),
        {"procedure": procedure_slug, "since": since},
    )


class TestPollView(TestCase):

    def setUp(self):
        self.procedure = Procedure.objects.create(title="Before Start", step=1, slug="before-start")
        self.item = CheckItemFactory(procedure=self.procedure)
        self.session = FlightSession.objects.create()

    def _seed_checked(self, item=None, source="manual", delta_seconds=0):
        item = item or self.item
        ts = datetime.now(tz=timezone.utc) + timedelta(seconds=delta_seconds)
        return FlightItemState.objects.create(
            flight_session=self.session,
            checklist_item=item,
            status="checked",
            source=source,
            checked_at=ts,
        )

    def test_no_session_returns_empty_200(self):
        response = _get_poll(self.client)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["checked_items"], [])
        self.assertFalse(data["sim_connected"])
        self.assertEqual(data["last_seen"], 0)

    def test_post_returns_405(self):
        _set_session_key(self.client, self.session.session_key)
        response = self.client.post(reverse("checklist:api_poll"))
        self.assertEqual(response.status_code, 405)

    def test_returns_checked_items_with_uppercased_source(self):
        self._seed_checked(source="manual")
        _set_session_key(self.client, self.session.session_key)
        response = _get_poll(self.client, since=0)
        self.assertEqual(response.status_code, 200)
        items = response.json()["checked_items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], self.item.id)
        self.assertEqual(items[0]["source"], "MANUAL")

    def test_auto_source_uppercased(self):
        self._seed_checked(source="auto")
        _set_session_key(self.client, self.session.session_key)
        items = _get_poll(self.client).json()["checked_items"]
        self.assertEqual(items[0]["source"], "AUTO")

    def test_since_filters_out_older_items(self):
        # Item checked 10 seconds ago
        self._seed_checked(delta_seconds=-10)
        _set_session_key(self.client, self.session.session_key)
        # Poll with since = 5 seconds ago → item is older, should be excluded
        since = int((datetime.now(tz=timezone.utc) - timedelta(seconds=5)).timestamp())
        items = _get_poll(self.client, since=since).json()["checked_items"]
        self.assertEqual(items, [])

    def test_since_includes_newer_items(self):
        # Item checked 2 seconds ago
        self._seed_checked(delta_seconds=-2)
        _set_session_key(self.client, self.session.session_key)
        # Poll with since = 10 seconds ago → item is newer, should be included
        since = int((datetime.now(tz=timezone.utc) - timedelta(seconds=10)).timestamp())
        items = _get_poll(self.client, since=since).json()["checked_items"]
        self.assertEqual(len(items), 1)

    def test_sim_connected_false_when_no_plugin_contact(self):
        _set_session_key(self.client, self.session.session_key)
        data = _get_poll(self.client).json()
        self.assertFalse(data["sim_connected"])
        self.assertEqual(data["last_seen"], 0)

    def test_sim_connected_false_when_plugin_contact_stale(self):
        self.session.last_plugin_contact = datetime.now(tz=timezone.utc) - timedelta(seconds=20)
        self.session.save()
        _set_session_key(self.client, self.session.session_key)
        data = _get_poll(self.client).json()
        self.assertFalse(data["sim_connected"])
        self.assertGreater(data["last_seen"], 0)

    def test_sim_connected_false_when_plugin_contact_just_outside_threshold(self):
        # 7s ago is outside the 5s threshold but would have been True under a 10s threshold
        self.session.last_plugin_contact = datetime.now(tz=timezone.utc) - timedelta(seconds=7)
        self.session.save()
        _set_session_key(self.client, self.session.session_key)
        data = _get_poll(self.client).json()
        self.assertFalse(data["sim_connected"])
        self.assertGreater(data["last_seen"], 0)

    def test_sim_connected_true_when_plugin_contact_recent(self):
        self.session.last_plugin_contact = datetime.now(tz=timezone.utc) - timedelta(seconds=3)
        self.session.save()
        _set_session_key(self.client, self.session.session_key)
        data = _get_poll(self.client).json()
        self.assertTrue(data["sim_connected"])

    def test_invalid_since_defaults_to_zero(self):
        self._seed_checked()
        _set_session_key(self.client, self.session.session_key)
        response = self.client.get(reverse("checklist:api_poll"), {"since": "bogus"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["checked_items"]), 1)


class TestCheckView(TestCase):

    def setUp(self):
        self.url = reverse("checklist:api_check")
        self.procedure = Procedure.objects.create(title="Before Start", step=1, slug="before-start")
        self.item = CheckItemFactory(procedure=self.procedure)
        self.session = FlightSession.objects.create()

    def test_happy_path_creates_flight_item_state(self):
        response = _post_json(
            self.client, self.url, {"check_item_id": self.item.id},
            session_key=self.session.session_key,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["id"], self.item.id)
        self.assertEqual(data["source"], "MANUAL")

        state = FlightItemState.objects.get(
            flight_session=self.session, checklist_item=self.item
        )
        self.assertEqual(state.status, "checked")
        self.assertEqual(state.source, "manual")
        self.assertIsNotNone(state.checked_at)

    def test_check_is_idempotent(self):
        _post_json(
            self.client, self.url, {"check_item_id": self.item.id},
            session_key=self.session.session_key,
        )
        _post_json(self.client, self.url, {"check_item_id": self.item.id})
        self.assertEqual(
            FlightItemState.objects.filter(
                flight_session=self.session, checklist_item=self.item
            ).count(),
            1,
        )

    def test_no_session_returns_403(self):
        response = _post_json(self.client, self.url, {"check_item_id": self.item.id})
        self.assertEqual(response.status_code, 403)

    def test_inactive_session_returns_403(self):
        self.session.is_active = False
        self.session.save()
        response = _post_json(
            self.client, self.url, {"check_item_id": self.item.id},
            session_key=self.session.session_key,
        )
        self.assertEqual(response.status_code, 403)

    def test_unknown_check_item_returns_400(self):
        response = _post_json(
            self.client, self.url, {"check_item_id": 99999},
            session_key=self.session.session_key,
        )
        self.assertEqual(response.status_code, 400)

    def test_non_integer_item_id_returns_400(self):
        response = _post_json(
            self.client, self.url, {"check_item_id": "abc"},
            session_key=self.session.session_key,
        )
        self.assertEqual(response.status_code, 400)

    def test_malformed_json_returns_400(self):
        session = self.client.session
        session["flight_session_key"] = self.session.session_key
        session.save()
        response = self.client.post(
            self.url, data="not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_get_request_returns_405(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)


class TestUncheckView(TestCase):

    def setUp(self):
        self.url = reverse("checklist:api_uncheck")
        self.procedure = Procedure.objects.create(title="Before Start", step=1, slug="before-start")
        self.item = CheckItemFactory(procedure=self.procedure)
        self.session = FlightSession.objects.create()

    def _seed_checked(self):
        from datetime import datetime, timezone
        FlightItemState.objects.create(
            flight_session=self.session,
            checklist_item=self.item,
            status="checked",
            source="manual",
            checked_at=datetime.now(tz=timezone.utc),
        )

    def test_happy_path_deletes_flight_item_state(self):
        self._seed_checked()
        response = _post_json(
            self.client, self.url, {"check_item_id": self.item.id},
            session_key=self.session.session_key,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["id"], self.item.id)
        self.assertFalse(
            FlightItemState.objects.filter(
                flight_session=self.session, checklist_item=self.item
            ).exists()
        )

    def test_uncheck_already_unchecked_is_idempotent(self):
        response = _post_json(
            self.client, self.url, {"check_item_id": self.item.id},
            session_key=self.session.session_key,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_no_session_returns_403(self):
        response = _post_json(self.client, self.url, {"check_item_id": self.item.id})
        self.assertEqual(response.status_code, 403)

    def test_inactive_session_returns_403(self):
        self.session.is_active = False
        self.session.save()
        response = _post_json(
            self.client, self.url, {"check_item_id": self.item.id},
            session_key=self.session.session_key,
        )
        self.assertEqual(response.status_code, 403)

    def test_unknown_check_item_returns_400(self):
        response = _post_json(
            self.client, self.url, {"check_item_id": 99999},
            session_key=self.session.session_key,
        )
        self.assertEqual(response.status_code, 400)

    def test_non_integer_item_id_returns_400(self):
        response = _post_json(
            self.client, self.url, {"check_item_id": "abc"},
            session_key=self.session.session_key,
        )
        self.assertEqual(response.status_code, 400)

    def test_malformed_json_returns_400(self):
        session = self.client.session
        session["flight_session_key"] = self.session.session_key
        session.save()
        response = self.client.post(
            self.url, data="not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_get_request_returns_405(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
