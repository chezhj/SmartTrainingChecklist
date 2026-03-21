"""Tests for /api/check and /api/uncheck endpoints."""

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

import json

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
