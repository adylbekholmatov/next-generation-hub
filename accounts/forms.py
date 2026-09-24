from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.utils.translation import gettext_lazy as _

from .models import User


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = _("Login")
        self.fields["username"].widget.attrs.update({"autocomplete": "username", "placeholder": "login"})
        self.fields["password"].label = _("Password")
        self.fields["password"].widget.attrs.update({"autocomplete": "current-password", "placeholder": "••••••••"})


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = _("Current password")
        self.fields["new_password1"].label = _("New password")
        self.fields["new_password2"].label = _("Repeat new password")
        self.fields["new_password1"].help_text = _("At least 6 characters, not too simple.")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "photo", "specialization", "about"]
        labels = {
            "first_name": _("First name"),
            "last_name": _("Last name"),
            "email": _("Email"),
            "phone": _("Phone"),
            "photo": _("Photo"),
            "specialization": _("Specialization"),
            "about": _("About me"),
        }
        widgets = {"about": forms.Textarea(attrs={"rows": 4}), "photo": forms.ClearableFileInput(attrs={"accept": "image/*"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.has_role(User.Role.TEACHER, User.Role.MANAGER):
            # Специализация нужна только сотрудникам.
            self.fields.pop("specialization")
