import os
from unittest import mock
from django.test import SimpleTestCase
from checklist.templatetags import (
    environment_tags,
)  # Update with actual module name
from django.conf import settings as conf_settings


class TemplateFiltersTest(SimpleTestCase):

    @mock.patch.dict(os.environ, {"TEST_ENV_VAR": "mocked_value"})
    def test_env_filter(self):
        """Test that env filter correctly retrieves environment variables"""
        self.assertEqual(environment_tags.env("TEST_ENV_VAR"), "mocked_value")
        self.assertIsNone(environment_tags.env("NON_EXISTENT_ENV_VAR"))

    @mock.patch.object(
        conf_settings, "TEST_SETTING", "mocked_setting_value", create=True
    )
    def test_setting_filter(self):
        """Test that setting filter correctly retrieves Django settings"""
        self.assertEqual(
            environment_tags.setting("TEST_SETTING"), "mocked_setting_value"
        )
        self.assertIsNone(environment_tags.setting("NON_EXISTENT_SETTING"))
