"""Auth views: registration, logout confirmation, user profile, account deletion."""

import re

from django import forms
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.shortcuts import redirect, render

_INPUT = {"class": "auth-input"}


# ── Styled form wrappers ──────────────────────────────────────────────────────

class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(_INPUT)


class StyledPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(_INPUT)


class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(_INPUT)


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(_INPUT)


# ── Registration ──────────────────────────────────────────────────────────────

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs=_INPUT))
    simbrief_id = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={**_INPUT, "placeholder": "e.g. 784213"}),
    )

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "simbrief_id":  # already has placeholder set above
                field.widget.attrs.update(_INPUT)


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            simbrief_id = form.cleaned_data.get("simbrief_id", "").strip()
            if simbrief_id:
                user.profile.simbrief_id = simbrief_id
                user.profile.save()
            login(request, user)
            return redirect("checklist:start")
    else:
        form = RegisterForm()
    return render(request, "registration/register.html", {"form": form})


# ── Logout confirmation ───────────────────────────────────────────────────────

@login_required
def logout_confirm_view(request):
    return render(request, "registration/logout_confirm.html")


# ── Profile ───────────────────────────────────────────────────────────────────

class SimBriefIdForm(forms.Form):
    simbrief_id = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={**_INPUT, "placeholder": "e.g. 784213"}
        ),
    )

    def clean_simbrief_id(self):
        value = self.cleaned_data["simbrief_id"].strip()
        if value and not re.fullmatch(r"\d{1,20}", value):
            raise forms.ValidationError("SimBrief ID must be numeric.")
        return value


@login_required
def account_profile_view(request):
    profile = request.user.profile
    if request.method == "POST" and request.POST.get("action") == "update_simbrief":
        form = SimBriefIdForm(request.POST)
        if form.is_valid():
            profile.simbrief_id = form.cleaned_data["simbrief_id"]
            profile.save()
            return redirect("checklist:account")
        return render(
            request,
            "registration/profile.html",
            {"simbrief_form": form, "profile": profile},
        )
    return render(
        request,
        "registration/profile.html",
        {
            "simbrief_form": SimBriefIdForm(
                initial={"simbrief_id": profile.simbrief_id}
            ),
            "profile": profile,
        },
    )


# ── Delete account ────────────────────────────────────────────────────────────

class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label="Current password",
        widget=forms.PasswordInput(attrs=_INPUT),
    )


@login_required
def delete_account_view(request):
    if request.method == "POST":
        form = DeleteAccountForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=request.user.username,
                password=form.cleaned_data["password"],
            )
            if user is not None:
                user.delete()
                return redirect("login")
            form.add_error("password", "Incorrect password.")
    else:
        form = DeleteAccountForm()
    return render(request, "registration/delete_confirm.html", {"form": form})
