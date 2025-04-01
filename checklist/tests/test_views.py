"""Test views"""

# pylint: disable=no-member
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
import random
from unittest.mock import Mock, patch, MagicMock

from django.db.models.query import QuerySet
from django.http import QueryDict
from checklist.tests.ViewTestCase import ViewTestCase

from checklist.tests.testFactories import (
    AttributeFactory,
    CheckItemFactory,
    ProcedureFactory,
)
from checklist.views import (
    IndexView,
    procedure_detail,
    profile_view,
    update_profile,
    update_profile_with_simbrief,
)


class TestProfileView(ViewTestCase):

    def test_called_with_template(self):
        # Create a POST request
        request = self.req_factory.post("/")

        # Mock the session as a dict-like object
        session = {}
        request.session = session

        # Call the profile_view function
        response = profile_view(request)

        # Assert the response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, "checklist/profile.html")

    @patch("checklist.views.Attribute.objects.order_by")
    def test_profile_view_returns_attributes(self, qs):
        qs.return_value.order_by.return_value = qs
        qs.__iter__.return_value = [Mock(), Mock()]
        qs.count.return_value = 2
        request = self.req_factory.get("/")
        # Mock the session as a dict-like object
        session = {}
        request.session = session

        response = profile_view(request)
        # render.assert_called_once_with("checklist/profile.html")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, "checklist/profile.html")
        qs.assert_called_once()

    @patch("checklist.views.Attribute.objects.order_by")
    def test_profile_view_updates_session_attrib(self, mock_order_by):
        """
        Test that the profile_view updates the session['attrib'] key correctly.
        """
        # Mock the session as a dict-like object
        session = {}
        request = self.req_factory.post("/")
        request.session = session

        # Mock SimBrief data
        mock_simbrief = MagicMock()
        mock_simbrief.temperature = "15°C"
        mock_simbrief.bleed_setting = "ON"

        # Patch SimBrief initialization and fetch_data
        with patch("checklist.views.SimBrief", return_value=mock_simbrief):
            response = profile_view(request)

        # Assert that session['attrib'] is updated
        self.assertIn("attrib", request.session)
        self.assertIsInstance(request.session["attrib"], list)

        # Assert the response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, "checklist/profile.html")

    def test_profile_clean_upper_removes_atrributes_from_session(self):
        """
        Test that the profile_view function flushes the session when the 'clean' parameter is passed.
        """
        # Create a POST request with the 'clean' parameter
        request = self.req_factory.post("/", data={"Clean": True})

        # Mock the session as a dict-like object
        session = {"attrib": [1, 2, 3]}  # Simulate some attributes in the session

        # Add a mock flush method to the session
        class MockSession(dict):
            def flush(self):
                self.clear()

        request.session = MockSession(session)

        # Call the profile_view function
        profile_view(request)

        # Assert that the session's flush method was called
        self.assertEqual(request.session["attrib"], [])  # The session should be cleared

    def test_profile_clean_lower_does_not_remove_atrributes_from_session(self):
        """
        Test that the profile_view function flushes the session when the 'clean' parameter is passed.
        """
        # Create a POST request with the 'clean' parameter
        request = self.req_factory.post("/", data={"clean": True})

        # Mock the session as a dict-like object
        session = {"attrib": [1, 2, 3]}  # Simulate some attributes in the session

        # Add a mock flush method to the session
        class MockSession(dict):
            def flush(self):
                self.clear()

        request.session = MockSession(session)

        # Call the profile_view function
        profile_view(request)

        # Assert that the session's flush method was called
        self.assertEqual(
            request.session["attrib"], [1, 2, 3]
        )  # The session should be cleared

    # Test if the post request is handled correctly
    @patch("checklist.views.SimBrief")
    def test_profile_view_id_in_post_request(self, mock_simbrief):

        request = self.create_request_with_session(
            "/", session_data={"attrib": []}, request_data={"simbrief_id": "67890"}
        )

        profile_view(request)
        mock_simbrief.assert_called_once_with("67890")

    # test if the cookie in the post request is handled correctly

    @patch("checklist.views.SimBrief")
    def test_profile_view_id_in_cookie(self, mock_simbrief):
        request = self.create_request_with_session("/", session_data={"attrib": []})
        request.COOKIES["simbrief_pilot_id"] = "67890"
        request.method = "POST"

        profile_view(request)
        mock_simbrief.assert_called_once_with("67890")


class TestProcedureView(ViewTestCase):
    @patch("checklist.views.Procedure.objects.order_by")
    def test_procedure_list(self, procedure_orderby):
        # Create an instance of a GET request.
        request = self.req_factory.get("procedures/")
        procedure_orderby.return_value.order_by.return_value = procedure_orderby
        # procedure_orderby.__iter__.return_value = [Mock(), Mock()]
        procedure_orderby.__iter__.return_value = None
        procedure_orderby.count.return_value = 0

        # Test my_view() as if it were deployed at /customer/details
        response = IndexView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "checklist/index.html")

    @patch("checklist.views.IndexView.get_queryset")
    def test_procedure_list_function(self, query_set):
        # Create an instance of a GET request.
        request = self.req_factory.get("procedures/")
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

        request = self.create_request_with_session(
            "/", session_data={"attrib": [atrib_one.id, atrib_two.id]}
        )

        get_object.return_value = check_item.procedure
        response = procedure_detail(request, slug="procedure1")
        self.assertEqual(len(response.context_data["check_items"]), 1)

    def test_procedure_detail_with_zero_checkitems_will_redirect(self):
        atrib_one = AttributeFactory()
        atrib_two = AttributeFactory()
        check_item = CheckItemFactory(attributes=[atrib_one, atrib_two])
        ProcedureFactory(step=check_item.procedure.step - 1)

        proc_two = ProcedureFactory(step=check_item.procedure.step + 1)

        request = self.create_request_with_session(
            "/", session_data={"attrib": [atrib_one.id]}, referer="Any string"
        )

        response = procedure_detail(request, slug=check_item.procedure.slug)

        self.assertEqual(response.status_code, 302)
        self.assertAlmostEqual(response.url, "/" + proc_two.slug)

    def test_procedure_detail_with_zero_checkitems_no_redirect_if_no_next(self):
        atrib_one = AttributeFactory()
        atrib_two = AttributeFactory()
        check_item = CheckItemFactory(attributes=[atrib_one, atrib_two])
        ProcedureFactory(step=check_item.procedure.step - 1)

        # proc_two = ProcedureFactory(step=check_item.procedure.step + 1)

        request = self.create_request_with_session(
            "/", session_data={"attrib": [atrib_one.id]}, referer="Any string"
        )
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
            "/",
            session_data={"attrib": [atrib_one.id]},
            referer="A long url with" + proc_next.slug,
        )

        response = procedure_detail(request, slug=check_item.procedure.slug)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/" + proc_prev.slug)

    def test_procedure_detail_with_checkitems_should_provide_next_prev(self):
        atrib_one = AttributeFactory()
        AttributeFactory()
        check_item = CheckItemFactory(attributes=[atrib_one])
        proc_one = ProcedureFactory(step=check_item.procedure.step - 1)

        proc_two = ProcedureFactory(step=check_item.procedure.step + 1)

        request = self.create_request_with_session(
            "/", session_data={"attrib": [atrib_one.id]}
        )

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

        request = self.create_request_with_session(
            "/", session_data={"attrib": [atrib_one.id]}
        )

        response = procedure_detail(request, slug=check_item.procedure.slug)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["nextproc"], proc_two)
        self.assertEqual(response.context_data["prevproc"], proc_one)

    def test_procedure_detail_without_profile_should_revert_to_profile(self):
        AttributeFactory()
        AttributeFactory()
        check_item = CheckItemFactory()
        ProcedureFactory(step=check_item.procedure.step - 1)

        ProcedureFactory(step=check_item.procedure.step + 1)

        request = self.create_request_with_session("/")

        response = procedure_detail(request, slug=check_item.procedure.slug)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")


class TestUpdateProfile(ViewTestCase):
    def test_update_profile_should_redirect(self):
        request = self.create_request_with_session("/", session_data={"attrib": []})

        response = update_profile(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/procedures/")

    def test_update_profile_adds_non_visuals(self):
        request = self.create_request_with_session("/", session_data={"attrib": []})

        atrib_visual = AttributeFactory()
        atrib_non_visual = AttributeFactory(show=False)

        response = update_profile(request)
        self.assertIn(atrib_non_visual.id, request.session["attrib"])
        self.assertNotIn(atrib_visual.id, request.session["attrib"])
        self.assertEqual(response.status_code, 302)

    def test_update_profile_adds_selected(self):
        atrib_visual = AttributeFactory()
        atrib_non_visual = AttributeFactory(show=False)

        post_data = QueryDict("", mutable=True)
        post_data.appendlist("attributes", str(atrib_visual.id))

        request = self.create_request_with_session("/", session_data={"attrib": []})
        request.POST = post_data

        response = update_profile(request)
        self.assertIn(atrib_non_visual.id, request.session["attrib"])
        self.assertIn(atrib_visual.id, request.session["attrib"])
        self.assertEqual(response.status_code, 302)

    def test_update_profile_removes_default_if_overruled(self):
        atrib_visual = AttributeFactory()
        # now create non visual, default Attribute, that is over_ruled by n
        atrib_non_visual = AttributeFactory(show=False, set_over_ruled_by=atrib_visual)

        post_data = QueryDict("", mutable=True)
        post_data.appendlist("attributes", str(atrib_visual.id))

        request = self.create_request_with_session("/", session_data={"attrib": []})
        request.POST = post_data

        response = update_profile(request)
        self.assertNotIn(atrib_non_visual.id, request.session["attrib"])
        self.assertIn(atrib_visual.id, request.session["attrib"])
        self.assertEqual(response.status_code, 302)


class TestUpdateProfileWithSimBrief(ViewTestCase):
    def test_adds_attribute_7_when_temperature_below_zero(self):
        request = self.create_request_with_session("/", session_data={"attrib": []})
        mock_simbrief = MagicMock()
        mock_simbrief.temperature = "-5°C"
        mock_simbrief.bleed_setting = "ON"

        update_profile_with_simbrief(request, mock_simbrief)

        self.assertIn(7, request.session["attrib"])

    def test_adds_attribute_9_and_removes_7_when_temperature_between_zero_and_ten(
        self,
    ):
        request = self.create_request_with_session("/", session_data={"attrib": [7]})
        mock_simbrief = MagicMock()
        mock_simbrief.temperature = "5°C"
        mock_simbrief.bleed_setting = "ON"

        update_profile_with_simbrief(request, mock_simbrief)

        self.assertIn(9, request.session["attrib"])
        self.assertNotIn(7, request.session["attrib"])

    def test_removes_attributes_7_and_9_when_temperature_above_ten(self):
        request = self.create_request_with_session("/", session_data={"attrib": [7, 9]})
        mock_simbrief = MagicMock()
        mock_simbrief.temperature = "15°C"
        mock_simbrief.bleed_setting = "ON"

        update_profile_with_simbrief(request, mock_simbrief)

        self.assertNotIn(7, request.session["attrib"])
        self.assertNotIn(9, request.session["attrib"])

    def test_adds_attribute_8_when_bleed_setting_is_off(self):
        request = self.create_request_with_session("/", session_data={"attrib": []})
        mock_simbrief = MagicMock()
        mock_simbrief.temperature = "15°C"
        mock_simbrief.bleed_setting = "OFF"

        update_profile_with_simbrief(request, mock_simbrief)

        self.assertIn(8, request.session["attrib"])

    def test_removes_attribute_8_when_bleed_setting_is_on(self):
        request = self.create_request_with_session("/", session_data={"attrib": [8]})
        mock_simbrief = MagicMock()
        mock_simbrief.temperature = "15°C"
        mock_simbrief.bleed_setting = "ON"

        update_profile_with_simbrief(request, mock_simbrief)

        self.assertNotIn(8, request.session["attrib"])

    def test_handles_missing_temperature_gracefully(self):
        request = self.create_request_with_session("/", session_data={"attrib": []})
        mock_simbrief = MagicMock()
        mock_simbrief.temperature = None
        mock_simbrief.bleed_setting = "ON"

        update_profile_with_simbrief(request, mock_simbrief)

        self.assertEqual(request.session["attrib"], [])

    def test_handles_missing_bleed_setting_gracefully(self):
        request = self.create_request_with_session("/", session_data={"attrib": []})
        mock_simbrief = MagicMock()
        mock_simbrief.temperature = "15°C"
        mock_simbrief.bleed_setting = None

        update_profile_with_simbrief(request, mock_simbrief)

        self.assertEqual(request.session["attrib"], [])
