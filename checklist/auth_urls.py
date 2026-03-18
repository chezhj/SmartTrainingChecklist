"""URL patterns for authentication."""

from django.contrib.auth import views as auth_views
from django.urls import path

from .auth_views import (
    StyledAuthenticationForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
    logout_confirm_view,
    register_view,
)

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(authentication_form=StyledAuthenticationForm),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", register_view, name="register"),
    path("logout/confirm/", logout_confirm_view, name="logout_confirm"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(form_class=StyledPasswordResetForm),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            form_class=StyledSetPasswordForm
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
