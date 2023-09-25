"""Test views"""

from unittest.mock import Mock, patch
from django.test import RequestFactory, TestCase
from django.db.models.query import QuerySet
from django.contrib.sessions.middleware import SessionMiddleware
from checklist.views import IndexView, procedure_detail, profile_view
from checklist.tests.testFactories import (
    AttributeFactory,
    ProcedureFactory,
    CheckItemFactory,
)


class testProfileView(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.req_factory = RequestFactory()
        # self.user = User.objects.create_user(
        #    username='jacob', email='jacob@…', password='top_secret')

    def create_request_with_session(self, path, session_data=None):
        # Create a request using the factory
        request = self.req_factory.get(path)

        # Add session support to the request
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)

        # Set session data if provided
        if session_data:
            request.session.update(session_data)
            request.session.save()

        return request

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
        # procedure_orderby.__iter__.return_value = [Mock(), Mock()]
        # query_set.__iter__.return_value = None
        # query_set.count.return_value = 0

        # Test my_view() as if it were deployed at /customer/details
        response = IndexView.as_view()(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], "checklist/index.html")

    def test_called_with_template(self):
        request = self.req_factory.get("/")

        response = profile_view(request)
        # render.assert_called_once_with("checklist/profile.html")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, "checklist/profile.html")

    @patch("checklist.views.Attribute.objects.order_by")
    def test_profile_view_returns_attributes(self, qs):
        qs.return_value.order_by.return_value = qs
        qs.__iter__.return_value = [Mock(), Mock()]
        qs.count.return_value = 2
        request = self.req_factory.get("/")

        response = profile_view(request)
        # render.assert_called_once_with("checklist/profile.html")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, "checklist/profile.html")
        qs.assert_called_once()

    def test_profile_clean_upper_removes_atrributes_from_session(self):
        request = self.req_factory.get("/?Clean")
        session = Mock()
        request.session = session

        response = profile_view(request)
        session.flush.assert_called_once()

    def test_profile_clean_lower_does_not_remove_atrributes_from_session(self):
        request = self.req_factory.get("/?clean")
        session = Mock()
        request.session = session

        response = profile_view(request)

        session.flush.assert_not_called()

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
        proc_one = ProcedureFactory(step=check_item.procedure.step - 2)

        proc_two = ProcedureFactory(step=check_item.procedure.step + 2)

        request = self.create_request_with_session(
            "/", session_data={"attrib": [atrib_one.id]}
        )

        response = procedure_detail(request, slug=check_item.procedure.slug)

        self.assertEqual(response.status_code, 302)
        self.assertAlmostEqual(response.url, "/" + proc_two.slug)

    def test_procedure_detail_with_checkitems_should_provide_next_prev(self):
        atrib_one = AttributeFactory()
        atrib_two = AttributeFactory()
        check_item = CheckItemFactory(attributes=[atrib_one])
        proc_one = ProcedureFactory(step=check_item.procedure.step - 2)

        proc_two = ProcedureFactory(step=check_item.procedure.step + 2)

        request = self.create_request_with_session(
            "/", session_data={"attrib": [atrib_one.id]}
        )

        response = procedure_detail(request, slug=check_item.procedure.slug)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data["nextproc"], proc_two)
        self.assertEqual(response.context_data["prevproc"], proc_one)
