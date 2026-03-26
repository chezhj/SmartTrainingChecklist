"""Tests for POST /api/plugin/check-next/ (plugin_views.py)."""

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

from datetime import datetime, timezone

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from checklist.models import (
    Attribute,
    FlightItemState,
    FlightSession,
    FlightSessionAttribute,
    Procedure,
    generate_api_key,
)
from checklist.tests.testFactories import AttributeFactory, CheckItemFactory

User = get_user_model()
URL = reverse("checklist:api_plugin_check_next")


def _post(client, key=None):
    """POST to check-next, optionally with a Bearer token."""
    kwargs = {}
    if key is not None:
        kwargs["HTTP_AUTHORIZATION"] = f"Bearer {key}"
    return client.post(URL, **kwargs)


class TestPluginCheckNextAuth(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="pilot", password="pw")
        self.profile = self.user.profile
        raw, hashed, prefix = generate_api_key()
        self.raw_key = raw
        self.profile.api_key_hash = hashed
        self.profile.api_key_prefix = prefix
        self.profile.save()

        procedure = Procedure.objects.create(title="Before Start", step=1, slug="before-start")
        CheckItemFactory(procedure=procedure, step=1)
        FlightSession.objects.create(
            user_profile=self.profile, active_phase="before-start", is_active=True
        )

    def test_missing_auth_header_returns_401(self):
        self.assertEqual(_post(self.client).status_code, 401)

    def test_wrong_key_returns_401(self):
        self.assertEqual(_post(self.client, key="fvw_wrongkey").status_code, 401)

    def test_get_returns_405(self):
        response = self.client.get(URL, HTTP_AUTHORIZATION=f"Bearer {self.raw_key}")
        self.assertEqual(response.status_code, 405)


class TestPluginCheckNextSession(TestCase):

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
        CheckItemFactory(procedure=self.procedure, step=1)

    def test_no_active_session_returns_404(self):
        # No FlightSession at all
        self.assertEqual(_post(self.client, self.raw_key).status_code, 404)

    def test_inactive_session_returns_404(self):
        FlightSession.objects.create(
            user_profile=self.profile, active_phase="before-start", is_active=False
        )
        self.assertEqual(_post(self.client, self.raw_key).status_code, 404)

    def test_empty_active_phase_returns_404(self):
        FlightSession.objects.create(
            user_profile=self.profile, active_phase="", is_active=True
        )
        self.assertEqual(_post(self.client, self.raw_key).status_code, 404)

    def test_unknown_active_phase_slug_returns_404(self):
        FlightSession.objects.create(
            user_profile=self.profile, active_phase="no-such-phase", is_active=True
        )
        self.assertEqual(_post(self.client, self.raw_key).status_code, 404)


class TestPluginCheckNextHappyPath(TestCase):

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
        self.item1 = CheckItemFactory(procedure=self.procedure, step=1)
        self.item2 = CheckItemFactory(procedure=self.procedure, step=2)
        self.session = FlightSession.objects.create(
            user_profile=self.profile, active_phase="before-start", is_active=True
        )

    def test_checks_first_unchecked_item(self):
        response = _post(self.client, self.raw_key)
        self.assertEqual(response.status_code, 200)
        state = FlightItemState.objects.get(
            flight_session=self.session, checklist_item=self.item1
        )
        self.assertEqual(state.status, "checked")
        self.assertEqual(state.source, "manual")
        self.assertIsNotNone(state.checked_at)

    def test_response_body_contains_action_label(self):
        response = _post(self.client, self.raw_key)
        self.assertEqual(response.status_code, 200)
        self.assertIn("checked", response.json())

    def test_updates_last_plugin_contact(self):
        before = datetime.now(tz=timezone.utc)
        _post(self.client, self.raw_key)
        self.session.refresh_from_db()
        self.assertIsNotNone(self.session.last_plugin_contact)
        self.assertGreaterEqual(self.session.last_plugin_contact, before)

    def test_last_plugin_contact_updated_even_on_phase_complete(self):
        # Pre-check all items so the response is 204 — contact still updated
        for item in [self.item1, self.item2]:
            FlightItemState.objects.create(
                flight_session=self.session,
                checklist_item=item,
                status="checked",
                source="manual",
                checked_at=datetime.now(tz=timezone.utc),
            )
        before = datetime.now(tz=timezone.utc)
        response = _post(self.client, self.raw_key)
        self.assertEqual(response.status_code, 204)
        self.session.refresh_from_db()
        self.assertGreaterEqual(self.session.last_plugin_contact, before)

    def test_skips_already_checked_item_and_checks_next(self):
        FlightItemState.objects.create(
            flight_session=self.session,
            checklist_item=self.item1,
            status="checked",
            source="manual",
            checked_at=datetime.now(tz=timezone.utc),
        )
        response = _post(self.client, self.raw_key)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            FlightItemState.objects.filter(
                flight_session=self.session,
                checklist_item=self.item2,
                status="checked",
            ).exists()
        )

    def test_phase_complete_returns_204(self):
        for item in [self.item1, self.item2]:
            FlightItemState.objects.create(
                flight_session=self.session,
                checklist_item=item,
                status="checked",
                source="manual",
                checked_at=datetime.now(tz=timezone.utc),
            )
        self.assertEqual(_post(self.client, self.raw_key).status_code, 204)

    def test_pressing_twice_does_not_duplicate_row(self):
        _post(self.client, self.raw_key)
        _post(self.client, self.raw_key)
        # item1 should be checked exactly once, item2 checked once
        self.assertEqual(
            FlightItemState.objects.filter(flight_session=self.session).count(), 2
        )

    def test_existing_skipped_state_overwritten_by_manual_check(self):
        # A skipped row exists for item1 — manual press should promote it to checked
        FlightItemState.objects.create(
            flight_session=self.session,
            checklist_item=self.item1,
            status="skipped",
            source=None,
            checked_at=None,
        )
        response = _post(self.client, self.raw_key)
        self.assertEqual(response.status_code, 200)
        state = FlightItemState.objects.get(
            flight_session=self.session, checklist_item=self.item1
        )
        self.assertEqual(state.status, "checked")
        self.assertEqual(state.source, "manual")


class TestPluginCheckNextAttributeFiltering(TestCase):

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

    def test_item_requiring_inactive_attribute_is_not_checked(self):
        attr = AttributeFactory()
        # step=1 so it comes first in order
        gated_item = CheckItemFactory(procedure=self.procedure, step=1, attributes=[attr])
        mandatory_item = CheckItemFactory(procedure=self.procedure, step=2)
        # Attribute is NOT active in this session (no FlightSessionAttribute row)
        response = _post(self.client, self.raw_key)
        self.assertEqual(response.status_code, 200)
        # Gated item must NOT be checked
        self.assertFalse(
            FlightItemState.objects.filter(
                flight_session=self.session, checklist_item=gated_item
            ).exists()
        )
        # Mandatory item (no attributes) IS checked
        self.assertTrue(
            FlightItemState.objects.filter(
                flight_session=self.session, checklist_item=mandatory_item,
                status="checked",
            ).exists()
        )

    def test_item_requiring_active_attribute_is_checked(self):
        attr = AttributeFactory()
        gated_item = CheckItemFactory(procedure=self.procedure, step=1, attributes=[attr])
        # Attribute IS active in session
        FlightSessionAttribute.objects.create(
            flight_session=self.session, attribute=attr, is_active=True
        )
        response = _post(self.client, self.raw_key)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            FlightItemState.objects.filter(
                flight_session=self.session, checklist_item=gated_item,
                status="checked",
            ).exists()
        )
