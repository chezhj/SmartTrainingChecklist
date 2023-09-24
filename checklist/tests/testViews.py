"""Test views"""

import unittest
from unittest.mock import Mock, patch
from django.test import RequestFactory, TestCase
from django.db.models.query import QuerySet
from checklist.views import IndexView, profile_view


class testProfileView(TestCase):
    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        # self.user = User.objects.create_user(
        #    username='jacob', email='jacob@…', password='top_secret')

    @patch("checklist.views.Procedure.objects.order_by")
    def test_procedure_list(self, procedure_orderby):
        # Create an instance of a GET request.
        request = self.factory.get("procedures/")
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
        request = self.factory.get("procedures/")
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
        request = self.factory.get("/")

        response = profile_view(request)
        # render.assert_called_once_with("checklist/profile.html")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, "checklist/profile.html")

    @patch("checklist.views.Attribute.objects.order_by")
    def test_profile_view_returns_attributes(self, qs):
        qs.return_value.order_by.return_value = qs
        qs.__iter__.return_value = [Mock(), Mock()]
        qs.count.return_value = 2
        request = self.factory.get("/")

        response = profile_view(request)
        # render.assert_called_once_with("checklist/profile.html")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name, "checklist/profile.html")
        qs.assert_called_once()

    def test_profile_clean_upper_removes_atrributes_from_session(self):
        request = self.factory.get("/?Clean")
        session = Mock()
        request.session = session

        response = profile_view(request)
        session.flush.assert_called_once()

    def test_profile_clean_lower_does_not_remove_atrributes_from_session(self):
        request = self.factory.get("/?clean")
        session = Mock()
        request.session = session

        response = profile_view(request)

        session.flush.assert_not_called()
