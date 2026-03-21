"""Tests for auth views: register, login, logout confirmation, profile, delete."""

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
        self.assertRedirects(response, reverse("checklist:start"))
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


class TestRegisterViewWithSimBriefId(TestCase):

    def test_register_with_simbrief_id_saves_to_profile(self):
        self.client.post(
            reverse("register"),
            {
                "username": "pilot",
                "email": "",
                "password1": "Securepass123!",
                "password2": "Securepass123!",
                "simbrief_id": "784213",
            },
        )
        user = User.objects.get(username="pilot")
        self.assertEqual(user.profile.simbrief_id, "784213")

    def test_register_without_simbrief_id_creates_empty_profile(self):
        self.client.post(
            reverse("register"),
            {
                "username": "pilot",
                "email": "",
                "password1": "Securepass123!",
                "password2": "Securepass123!",
            },
        )
        user = User.objects.get(username="pilot")
        self.assertEqual(user.profile.simbrief_id, "")


class TestAccountProfileView(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="pilot", password="Securepass123!"
        )
        self.url = reverse("checklist:account")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_get_renders_profile_template(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/profile.html")

    def test_get_context_contains_profile_and_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertIn("profile", response.context)
        self.assertIn("simbrief_form", response.context)

    def test_post_valid_simbrief_id_saves_and_redirects(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.url, {"action": "update_simbrief", "simbrief_id": "784213"}
        )
        self.assertRedirects(response, self.url)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.simbrief_id, "784213")

    def test_post_empty_simbrief_id_clears_value(self):
        self.user.profile.simbrief_id = "784213"
        self.user.profile.save()
        self.client.force_login(self.user)
        self.client.post(self.url, {"action": "update_simbrief", "simbrief_id": ""})
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.simbrief_id, "")

    def test_post_non_numeric_simbrief_id_returns_error(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.url, {"action": "update_simbrief", "simbrief_id": "ABC123"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/profile.html")
        self.assertTrue(response.context["simbrief_form"].errors)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.simbrief_id, "")  # unchanged


class TestDeleteAccountView(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="pilot", password="Securepass123!"
        )
        self.url = reverse("checklist:delete_account")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_get_renders_delete_confirm_template(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/delete_confirm.html")

    def test_post_correct_password_deletes_user_and_redirects(self):
        user_id = self.user.pk
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"password": "Securepass123!"})
        self.assertRedirects(response, reverse("login"))
        self.assertFalse(User.objects.filter(pk=user_id).exists())

    def test_post_correct_password_also_deletes_profile(self):
        from checklist.models import UserProfile
        user_id = self.user.pk
        self.client.force_login(self.user)
        self.client.post(self.url, {"password": "Securepass123!"})
        self.assertFalse(UserProfile.objects.filter(user_id=user_id).exists())

    def test_post_wrong_password_keeps_user(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"password": "wrongpassword"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())

    def test_post_wrong_password_shows_field_error(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"password": "wrongpassword"})
        self.assertIn("password", response.context["form"].errors)
