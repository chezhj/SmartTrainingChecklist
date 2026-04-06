"""Test views"""

# pylint: disable=no-member
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
import random
from unittest.mock import MagicMock, Mock, patch

from django.db.models.query import QuerySet
from django.test import RequestFactory, TestCase

from checklist.models import Attribute, FlightItemState, FlightSession, FlightSessionAttribute, UserAttributeDefault
from checklist.tests.testFactories import (
    AttributeFactory,
    CheckItemFactory,
    ProcedureFactory,
)
from checklist.tests.ViewTestCase import ViewTestCase
from checklist.views import (
    IndexView,
    procedure_detail,
    profile_view,
    update_session_role,
)


def _create_session_with_flight(request, attr_ids, extra_session=None):
    """
    Create a FlightSession with the given active attribute IDs, store its key
    in the request session, and return the FlightSession.
    """
    session = FlightSession.objects.create()
    all_attrs = Attribute.objects.all()
    for attr in all_attrs:
        FlightSessionAttribute.objects.create(
            flight_session=session,
            attribute=attr,
            is_active=(attr.id in attr_ids),
        )
    request.session["flight_session_key"] = session.session_key
    if extra_session:
        for k, v in extra_session.items():
            request.session[k] = v
    request.session.save()
    return session


class TestProfileView(ViewTestCase):

    def test_get_renders_template(self):
        request = self.create_request_with_session("/")
        request.user = Mock(is_authenticated=False)
        response = profile_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, "checklist/profile.html")

    def test_get_prefills_simbrief_id_for_logged_in_user(self):
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="pilot", password="pass!")
        user.profile.simbrief_id = "98765"
        user.profile.save()

        request = self.create_request_with_session("/")
        request.user = user
        response = profile_view(request)
        self.assertEqual(response.context_data["simbrief_id"], "98765")

    @patch("checklist.views.SimBrief")
    def test_get_plan_action_calls_simbrief(self, mock_sb_cls):
        mock_sb = MagicMock()
        mock_sb.origin = "EHAM"
        mock_sb.destination = "LFPG"
        mock_sb.runway = "18R"
        mock_sb.temperature = "+4°C"
        mock_sb.flap_setting = "Flap 5"
        mock_sb.bleed_setting = "ON"
        mock_sb.callsign = "KLM123"
        mock_sb.block_fuel = 6500
        mock_sb.finres_altn = 2400
        mock_sb.error_message = None
        mock_sb_cls.return_value = mock_sb

        request = self.create_request_with_session(
            "/", request_data={"action": "get_plan", "simbrief_id": "12345"}
        )
        request.user = Mock(is_authenticated=False)
        response = profile_view(request)

        mock_sb_cls.assert_called_once_with("12345")
        mock_sb.fetch_data.assert_called_once()
        self.assertEqual(response.status_code, 302)

    @patch("checklist.views.SimBrief")
    def test_get_plan_caches_data_in_session(self, mock_sb_cls):
        mock_sb = MagicMock()
        mock_sb.origin = "EHAM"
        mock_sb.destination = "LFPG"
        mock_sb.runway = "18R"
        mock_sb.temperature = "+4°C"
        mock_sb.flap_setting = "Flap 5"
        mock_sb.bleed_setting = "ON"
        mock_sb.callsign = "KLM123"
        mock_sb.block_fuel = 6500
        mock_sb.finres_altn = 2400
        mock_sb.error_message = None
        mock_sb_cls.return_value = mock_sb

        request = self.create_request_with_session(
            "/", request_data={"action": "get_plan", "simbrief_id": "12345"}
        )
        request.user = Mock(is_authenticated=False)
        # Create the attribute that should be derived for +4°C (ZeroToTen range)
        zero_to_ten = Attribute.objects.create(title="ZeroToTen", order=1)
        profile_view(request)

        self.assertEqual(request.session["sb_origin"], "EHAM")
        self.assertEqual(request.session["sb_destination"], "LFPG")
        self.assertEqual(request.session["sb_callsign"], "KLM123")
        self.assertEqual(request.session["sb_block_fuel"], 6500)
        self.assertEqual(request.session["sb_finres_altn"], 2400)
        # +4°C is in the ZeroToTen range (0 < t < 11) → ZeroToTen attribute should be derived
        self.assertIn(zero_to_ten.pk, request.session["sb_derived_attribs"])

    def test_clear_action_removes_flight_keys(self):
        flight_data = {
            "flight_session_key": "ABCD-1234",
            "dual_mode": True,
            "pilot_role": "PF",
            "captain_role": "C",
            "sb_origin": "EHAM",
            "sb_destination": "LFPG",
            "sb_runway": "18R",
            "sb_temp": "+4°C",
            "sb_flaps": "Flap 5",
            "sb_bleed": "ON",
            "sb_derived_attribs": [1, 2],
            "sb_simbrief_id": "12345",
            "sb_error": "",
        }
        request = self.create_request_with_session(
            "/", session_data=flight_data, request_data={"action": "clear"}
        )
        request.user = Mock(is_authenticated=False)
        profile_view(request)

        for key in flight_data:
            self.assertNotIn(key, request.session)

    def test_clear_action_preserves_auth_session(self):
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="clearpilot", password="pass!")
        self.client.force_login(user)
        self.assertIn("_auth_user_id", self.client.session)

        self.client.post("/", {"action": "clear"})

        self.assertIn("_auth_user_id", self.client.session)

    def test_start_checklist_creates_flight_session(self):
        attr = Attribute.objects.create(title="Optional", order=1)
        request = self.create_request_with_session(
            "/",
            request_data={"action": "start_checklist", "attributes": str(attr.id)},
        )
        request.user = Mock(is_authenticated=False)
        response = profile_view(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("flight_session_key", request.session)
        key = request.session["flight_session_key"]
        session = FlightSession.objects.get(session_key=key)
        self.assertTrue(session.is_active)

    def test_start_checklist_sets_attributes(self):
        attr = Attribute.objects.create(title="Online", order=2)
        request = self.create_request_with_session(
            "/",
            request_data={"action": "start_checklist", "attributes": str(attr.id)},
        )
        request.user = Mock(is_authenticated=False)
        profile_view(request)

        key = request.session["flight_session_key"]
        session = FlightSession.objects.get(session_key=key)
        active_ids = list(
            FlightSessionAttribute.objects.filter(
                flight_session=session, is_active=True
            ).values_list("attribute_id", flat=True)
        )
        self.assertIn(attr.id, active_ids)

    def test_user_default_ids_prechecked_on_get(self):
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="pilot2", password="pass!")
        pref_attr = Attribute.objects.create(title="Optional", order=5, is_user_preference=True)
        UserAttributeDefault.objects.create(user_profile=user.profile, attribute=pref_attr)

        request = self.create_request_with_session("/")
        request.user = user
        response = profile_view(request)
        self.assertIn(pref_attr.id, response.context_data["user_default_ids"])

    def test_start_checklist_seeds_user_defaults_as_active(self):
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="pilot3", password="pass!")
        pref_attr = Attribute.objects.create(title="Safety Test", order=6, is_user_preference=True)
        UserAttributeDefault.objects.create(user_profile=user.profile, attribute=pref_attr)

        request = self.create_request_with_session(
            "/", request_data={"action": "start_checklist"}
        )
        request.user = user
        profile_view(request)

        key = request.session["flight_session_key"]
        session = FlightSession.objects.get(session_key=key)
        self.assertTrue(
            FlightSessionAttribute.objects.filter(
                flight_session=session, attribute=pref_attr, is_active=True
            ).exists()
        )

    def test_start_checklist_user_default_source_is_user_default(self):
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="pilot4", password="pass!")
        pref_attr = Attribute.objects.create(title="Optional B", order=7, is_user_preference=True)
        UserAttributeDefault.objects.create(user_profile=user.profile, attribute=pref_attr)

        request = self.create_request_with_session(
            "/",
            request_data={"action": "start_checklist", "attributes": str(pref_attr.id)},
        )
        request.user = user
        profile_view(request)

        key = request.session["flight_session_key"]
        session = FlightSession.objects.get(session_key=key)
        fsa = FlightSessionAttribute.objects.get(flight_session=session, attribute=pref_attr)
        self.assertEqual(fsa.source, "user_default")

    def test_start_checklist_with_active_session_continues_in_place(self):
        """start_checklist action reuses the existing session instead of creating a new one."""
        attr = Attribute.objects.create(title="ExistingAttr", order=10)
        request = self.create_request_with_session(
            "/", request_data={"action": "start_checklist"}
        )
        request.user = Mock(is_authenticated=False)
        # Seed an existing active session
        existing = FlightSession.objects.create()
        request.session["flight_session_key"] = existing.session_key
        request.session.save()

        profile_view(request)

        existing.refresh_from_db()
        self.assertTrue(existing.is_active)
        self.assertEqual(FlightSession.objects.filter(is_active=True).count(), 1)

    def test_new_flight_action_deactivates_existing_and_creates_new(self):
        request = self.create_request_with_session(
            "/", request_data={"action": "new_flight"}
        )
        request.user = Mock(is_authenticated=False)
        existing = FlightSession.objects.create()
        request.session["flight_session_key"] = existing.session_key
        request.session.save()

        profile_view(request)

        existing.refresh_from_db()
        self.assertFalse(existing.is_active)
        new_key = request.session.get("flight_session_key")
        self.assertNotEqual(new_key, existing.session_key)

    def test_continue_updates_attributes_in_place(self):
        attr = Attribute.objects.create(title="NewAttr", order=11)
        existing = FlightSession.objects.create()
        FlightSessionAttribute.objects.create(
            flight_session=existing, attribute=attr, is_active=False
        )
        request = self.create_request_with_session(
            "/",
            request_data={"action": "start_checklist", "attributes": str(attr.id)},
        )
        request.user = Mock(is_authenticated=False)
        request.session["flight_session_key"] = existing.session_key
        request.session.save()

        profile_view(request)

        fsa = FlightSessionAttribute.objects.get(flight_session=existing, attribute=attr)
        self.assertTrue(fsa.is_active)

    def test_profile_get_with_active_session_passes_prechecked_ids(self):
        attr = Attribute.objects.create(title="ActiveAttr", order=12)
        existing = FlightSession.objects.create()
        FlightSessionAttribute.objects.create(
            flight_session=existing, attribute=attr, is_active=True
        )
        request = self.create_request_with_session("/")
        request.user = Mock(is_authenticated=False)
        request.session["flight_session_key"] = existing.session_key
        request.session.save()

        response = profile_view(request)

        self.assertIn(attr.id, response.context_data["prechecked_ids"])
        self.assertIsNotNone(response.context_data["active_flight_session"])

    def test_profile_get_without_active_session_prechecked_ids_from_defaults(self):
        from django.contrib.auth.models import User
        user = User.objects.create_user(username="pilot5", password="pass!")
        pref_attr = Attribute.objects.create(title="Default5", order=13, is_user_preference=True)
        UserAttributeDefault.objects.create(user_profile=user.profile, attribute=pref_attr)

        request = self.create_request_with_session("/")
        request.user = user
        response = profile_view(request)

        self.assertIn(pref_attr.id, response.context_data["prechecked_ids"])
        self.assertIsNone(response.context_data["active_flight_session"])

    def test_start_checklist_dual_mode_sets_pilot_role(self):
        request = self.create_request_with_session(
            "/",
            request_data={"action": "start_checklist", "dual_mode": "on"},
        )
        request.user = Mock(is_authenticated=False)
        profile_view(request)

        key = request.session["flight_session_key"]
        session = FlightSession.objects.get(session_key=key)
        self.assertEqual(session.pilot_role, "PF")
        self.assertTrue(request.session.get("dual_mode"))


class TestProcedureView(ViewTestCase):

    def test_procedure_list_redirects_without_session(self):
        request = self.create_request_with_session("procedures/")
        request.user = Mock(is_authenticated=False)
        response = IndexView.as_view()(request)
        self.assertEqual(response.status_code, 302)

    @patch("checklist.views.IndexView.get_queryset")
    def test_procedure_list_with_session(self, query_set):
        request = self.create_request_with_session("procedures/")
        request.session["flight_session_key"] = FlightSession.objects.create().session_key
        request.session.save()
        qs = Mock(spec=QuerySet)
        query_set.return_value = qs
        response = IndexView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "checklist/index.html")


class TestProcedureDetailView(ViewTestCase):

    @patch("checklist.views.get_object_or_404")
    def test_procedure_detail_get_checkitems(self, get_object):
        atrib_one = AttributeFactory()
        atrib_two = AttributeFactory()
        check_item = CheckItemFactory(attributes=[atrib_one, atrib_two])
        get_object.return_value = check_item.procedure

        request = self.create_request_with_session("/")
        _create_session_with_flight(request, [atrib_one.id, atrib_two.id])

        response = procedure_detail(request, slug="procedure1")
        self.assertEqual(len(response.context_data["check_items"]), 1)

    def test_procedure_detail_with_zero_checkitems_will_redirect(self):
        atrib_one = AttributeFactory()
        atrib_two = AttributeFactory()
        check_item = CheckItemFactory(attributes=[atrib_one, atrib_two])
        ProcedureFactory(step=check_item.procedure.step - 1)
        proc_two = ProcedureFactory(step=check_item.procedure.step + 1)

        request = self.create_request_with_session("/", referer="Any string")
        _create_session_with_flight(request, [atrib_one.id])

        response = procedure_detail(request, slug=check_item.procedure.slug)
        self.assertEqual(response.status_code, 302)
        self.assertAlmostEqual(response.url, "/" + proc_two.slug)

    def test_procedure_detail_with_zero_checkitems_no_redirect_if_no_next(self):
        atrib_one = AttributeFactory()
        atrib_two = AttributeFactory()
        check_item = CheckItemFactory(attributes=[atrib_one, atrib_two])
        ProcedureFactory(step=check_item.procedure.step - 1)

        request = self.create_request_with_session("/", referer="Any string")
        _create_session_with_flight(request, [atrib_one.id])

        response = procedure_detail(request, slug=check_item.procedure.slug)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["procedure"].id, check_item.procedure.id)

    def test_procedure_detail_with_zero_checkitems_will_redirect_backward(self):
        atrib_one = AttributeFactory()
        atrib_two = AttributeFactory()
        check_item = CheckItemFactory(attributes=[atrib_one, atrib_two])
        proc_prev = ProcedureFactory(step=check_item.procedure.step - 1)
        proc_next = ProcedureFactory(step=check_item.procedure.step + 1)

        request = self.create_request_with_session(
            "/", referer="A long url with" + proc_next.slug
        )
        _create_session_with_flight(request, [atrib_one.id])

        response = procedure_detail(request, slug=check_item.procedure.slug)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/" + proc_prev.slug)

    def test_procedure_detail_with_checkitems_should_provide_next_prev(self):
        atrib_one = AttributeFactory()
        AttributeFactory()
        check_item = CheckItemFactory(attributes=[atrib_one])
        proc_one = ProcedureFactory(step=check_item.procedure.step - 1)
        proc_two = ProcedureFactory(step=check_item.procedure.step + 1)

        request = self.create_request_with_session("/")
        _create_session_with_flight(request, [atrib_one.id])

        response = procedure_detail(request, slug=check_item.procedure.slug)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["nextproc"], proc_two)
        self.assertEqual(response.context_data["prevproc"], proc_one)

    def test_procedure_detail_with_checkitems_should_provide_next_prev_other_step(self):
        atrib_one = AttributeFactory()
        AttributeFactory()
        check_item = CheckItemFactory(attributes=[atrib_one])
        proc_one = ProcedureFactory(
            step=check_item.procedure.step - random.randint(1, 20)
        )
        proc_two = ProcedureFactory(
            step=check_item.procedure.step + random.randint(1, 20)
        )

        request = self.create_request_with_session("/")
        _create_session_with_flight(request, [atrib_one.id])

        response = procedure_detail(request, slug=check_item.procedure.slug)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["nextproc"], proc_two)
        self.assertEqual(response.context_data["prevproc"], proc_one)

    def test_procedure_detail_without_session_redirects_to_start(self):
        check_item = CheckItemFactory()
        ProcedureFactory(step=check_item.procedure.step - 1)
        ProcedureFactory(step=check_item.procedure.step + 1)

        request = self.create_request_with_session("/")

        response = procedure_detail(request, slug=check_item.procedure.slug)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

    def test_procedure_detail_without_dualmode_lowlight_all_false(self):
        atrib_one = AttributeFactory()
        AttributeFactory()
        check_item = CheckItemFactory(attributes=[atrib_one])
        ProcedureFactory(step=check_item.procedure.step - 1)
        ProcedureFactory(step=check_item.procedure.step + 1)

        request = self.create_request_with_session("/")
        _create_session_with_flight(request, [atrib_one.id])

        response = procedure_detail(request, slug=check_item.procedure.slug)
        self.assertEqual(response.status_code, 200)
        for item in response.context_data["check_items"]:
            self.assertFalse(item.lowlight)

    def test_procedure_detail_lowlight_logic(self):
        test_cases = [
            ("PM", "FO", "BOTH", False),
            ("PM", "FO", "PM", False),
            ("PM", "FO", "FO", False),
            ("PM", "FO", "C", True),
            ("C", "FO", "PM", True),
            ("C", "FO", "C", False),
            ("C", "FO", "FO", False),
        ]

        for pilot_role, captain_role, check_item_role, expected_lowlight in test_cases:
            with self.subTest(
                pilot_role=pilot_role,
                captain_role=captain_role,
                check_item_role=check_item_role,
            ):
                atrib_one = AttributeFactory()
                check_item = CheckItemFactory(attributes=[atrib_one])
                check_item.role = check_item_role
                check_item.save()
                ProcedureFactory(step=check_item.procedure.step - 1)
                ProcedureFactory(step=check_item.procedure.step + 1)

                request = self.create_request_with_session("/")
                _create_session_with_flight(
                    request,
                    [atrib_one.id],
                    extra_session={
                        "dual_mode": True,
                        "pilot_role": pilot_role,
                        "captain_role": captain_role,
                    },
                )

                response = procedure_detail(request, slug=check_item.procedure.slug)
                self.assertEqual(response.status_code, 200)
                for item in response.context_data["check_items"]:
                    self.assertEqual(item.lowlight, expected_lowlight)


    def test_procedure_detail_advances_active_phase(self):
        attr = AttributeFactory()
        item = CheckItemFactory(attributes=[attr])
        request = self.create_request_with_session("/")
        session = _create_session_with_flight(request, [attr.id])
        # active_phase starts at the first procedure created by _create_flight_session
        # which is empty here — set it to a lower step so visiting item.procedure advances it
        session.active_phase = ""
        session.save()

        procedure_detail(request, slug=item.procedure.slug)

        session.refresh_from_db()
        self.assertEqual(session.active_phase, item.procedure.slug)

    def test_procedure_detail_does_not_retreat_active_phase(self):
        attr = AttributeFactory()
        item_low = CheckItemFactory(attributes=[attr])
        item_high = CheckItemFactory(attributes=[attr])
        # Ensure distinct steps
        item_low.procedure.step = 1
        item_low.procedure.save()
        item_high.procedure.step = 10
        item_high.procedure.save()

        request = self.create_request_with_session("/")
        session = _create_session_with_flight(request, [attr.id])
        session.active_phase = item_high.procedure.slug
        session.save()

        # Navigate to a lower-step procedure
        procedure_detail(request, slug=item_low.procedure.slug)

        session.refresh_from_db()
        self.assertEqual(session.active_phase, item_high.procedure.slug)

    def test_procedure_detail_active_phase_step_in_context(self):
        attr = AttributeFactory()
        item = CheckItemFactory(attributes=[attr])
        request = self.create_request_with_session("/")
        _create_session_with_flight(request, [attr.id])

        response = procedure_detail(request, slug=item.procedure.slug)

        self.assertIn("active_phase_step", response.context_data)

    def test_checked_manual_item_annotated_with_ci_manual(self):
        from datetime import datetime, timezone
        attr = AttributeFactory()
        item = CheckItemFactory(attributes=[attr])
        request = self.create_request_with_session("/")
        session = _create_session_with_flight(request, [attr.id])
        FlightItemState.objects.create(
            flight_session=session,
            checklist_item=item,
            status="checked",
            source="manual",
            checked_at=datetime.now(tz=timezone.utc),
        )
        response = procedure_detail(request, slug=item.procedure.slug)
        items = response.context_data["check_items"]
        self.assertEqual(items[0].checked_css, "ci-manual")

    def test_checked_auto_item_annotated_with_ci_auto(self):
        from datetime import datetime, timezone
        attr = AttributeFactory()
        item = CheckItemFactory(attributes=[attr])
        request = self.create_request_with_session("/")
        session = _create_session_with_flight(request, [attr.id])
        FlightItemState.objects.create(
            flight_session=session,
            checklist_item=item,
            status="checked",
            source="auto",
            checked_at=datetime.now(tz=timezone.utc),
        )
        response = procedure_detail(request, slug=item.procedure.slug)
        items = response.context_data["check_items"]
        self.assertEqual(items[0].checked_css, "ci-auto")

    def test_unchecked_item_annotated_with_empty_string(self):
        attr = AttributeFactory()
        item = CheckItemFactory(attributes=[attr])
        request = self.create_request_with_session("/")
        _create_session_with_flight(request, [attr.id])
        response = procedure_detail(request, slug=item.procedure.slug)
        items = response.context_data["check_items"]
        self.assertEqual(items[0].checked_css, "")

    def test_skipped_item_annotated_as_ci_skipped(self):
        attr = AttributeFactory()
        item = CheckItemFactory(attributes=[attr])
        request = self.create_request_with_session("/")
        session = _create_session_with_flight(request, [attr.id])
        FlightItemState.objects.create(
            flight_session=session,
            checklist_item=item,
            status="skipped",
            source=None,
        )
        response = procedure_detail(request, slug=item.procedure.slug)
        items = response.context_data["check_items"]
        self.assertEqual(items[0].checked_css, "ci-skipped")


class TestUpdateSessionRole(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_no_post_returns_400(self):
        request = self.factory.get("/update-session-role/")
        response = update_session_role(request)
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(response.content, {"success": False})

    def test_defaults_are_assigned(self):
        request = self.factory.post("/update-session-role/", data={})
        request.session = {}
        response = update_session_role(request)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {"success": True, "pilot_role": "PM", "captain_role": "FO"},
        )
        self.assertEqual(request.session["pilot_role"], "PM")
        self.assertEqual(request.session["captain_role"], "FO")

    def test_correct_assignment(self):
        request = self.factory.post(
            "/update-session-role/",
            data={"pilot_role": "PF", "captain_role": "C"},
        )
        request.session = {}
        response = update_session_role(request)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {"success": True, "pilot_role": "PF", "captain_role": "C"},
        )
        self.assertEqual(request.session["pilot_role"], "PF")
        self.assertEqual(request.session["captain_role"], "C")
