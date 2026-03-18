"""Tests for auth views: register, login, logout confirmation."""

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class TestRegisterView(TestCase):

    def test_register_get(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/register.html")

    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "testpilot",
                "email": "test@example.com",
                "password1": "Securepass123!",
                "password2": "Securepass123!",
            },
        )
        self.assertRedirects(response, reverse("checklist:index"))
        self.assertTrue(User.objects.filter(username="testpilot").exists())
        self.assertIn("_auth_user_id", self.client.session)

    def test_register_duplicate_username(self):
        User.objects.create_user(username="testpilot", password="Securepass123!")
        response = self.client.post(
            reverse("register"),
            {
                "username": "testpilot",
                "email": "",
                "password1": "Securepass123!",
                "password2": "Securepass123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="testpilot").count(), 1)

    def test_register_password_mismatch(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newpilot",
                "email": "",
                "password1": "Securepass123!",
                "password2": "Wrongpass456!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newpilot").exists())


class TestLoginView(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="pilot", password="Securepass123!"
        )

    def test_login_get(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")

    def test_login_success(self):
        response = self.client.post(
            reverse("login"),
            {"username": "pilot", "password": "Securepass123!"},
        )
        self.assertRedirects(response, reverse("checklist:start"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_bad_credentials(self):
        response = self.client.post(
            reverse("login"),
            {"username": "pilot", "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


class TestLogoutConfirmView(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="pilot", password="Securepass123!"
        )

    def test_logout_confirm_requires_login(self):
        response = self.client.get(reverse("logout_confirm"))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('logout_confirm')}",
        )

    def test_logout_confirm_get(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("logout_confirm"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/logout_confirm.html")

    def test_logout_post(self):
        self.client.force_login(self.user)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)
