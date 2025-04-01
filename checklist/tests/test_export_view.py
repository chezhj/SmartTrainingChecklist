from django.test import TestCase, RequestFactory
from checklist.models import Procedure, CheckItem
from checklist.export_view import ExportChecklistView


class ExportChecklistViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ExportChecklistView.as_view()

        # Create test data
        self.procedure = Procedure.objects.create(
            title="Test Procedure",
            step=1,
            show_expression="test_expression",
            auto_continue=True,
        )
        self.checkitem = CheckItem.objects.create(
            procedure=self.procedure,
            step=1,
            item="Test Item",
            setting="Test Setting",
            action_label="ACTION",
            dataref_expression="dataref_test",
        )

    def test_export_checklist_view_response(self):
        request = self.factory.get("/export/")
        request.session = {"attrib": []}  # Mock session data

        response = self.view(request)

        # Assert response is a text file
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain")
        self.assertIn(
            'attachment; filename="clist.txt"', response["Content-Disposition"]
        )

    def test_export_checklist_content(self):
        request = self.factory.get("/export/")
        request.session = {"attrib": []}  # Mock session data

        response = self.view(request)
        content = response.content.decode("utf-8")

        # Assert header lines are present
        self.assertIn("SMART PROCEDURES CHECKLIST", content)

        # Assert procedure lines are present
        self.assertIn("sw_checklist:Test Procedure:Test Procedure", content)
        self.assertIn("sw_show:test_expression", content)

        # Assert check item lines are present
        self.assertIn(
            "sw_item_c:\\white\\Test Item\\grey\\, Test Setting|ACTION", content
        )
        self.assertIn(":dataref_test", content)

        # Assert auto-continue lines are present
        self.assertIn("sw_continue", content)
