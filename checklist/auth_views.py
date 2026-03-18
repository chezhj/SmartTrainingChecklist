"""Auth views: registration and logout confirmation."""

from django import forms
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.shortcuts import redirect, render

_INPUT = {"class": "auth-input"}


class StyledAuthenticationForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(_INPUT)


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs=_INPUT))

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email", "password1", "password2")

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


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("checklist:index")
    else:
        form = RegisterForm()
    return render(request, "registration/register.html", {"form": form})


@login_required
def logout_confirm_view(request):
    return render(request, "registration/logout_confirm.html")
