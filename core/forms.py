import re

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Course, EnrollmentRequest

PHONE_RE = re.compile(r"^\+?[\d\s\-()]{7,20}$")


class EnrollmentForm(forms.ModelForm):
    # Скрытое поле-ловушка для ботов: люди его не видят и не заполняют.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))

    class Meta:
        model = EnrollmentRequest
        fields = ["name", "phone", "email", "age", "course", "message"]
        labels = {
            "name": _("Your name"),
            "phone": _("Phone"),
            "email": _("Email"),
            "age": _("Student's age"),
            "course": _("Course"),
            "message": _("Comment"),
        }
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name", "placeholder": _("Aibek Asanov")}),
            "phone": forms.TextInput(
                attrs={"autocomplete": "tel", "inputmode": "tel", "placeholder": "+996 555 000 000"}
            ),
            "email": forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "name@mail.kg"}),
            "age": forms.NumberInput(attrs={"min": 5, "max": 99, "placeholder": "12"}),
            "message": forms.Textarea(attrs={"rows": 3, "placeholder": _("Questions, convenient time to call…")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = Course.objects.filter(is_active=True)
        self.fields["course"].empty_label = _("Not decided yet — help me choose")
        self.fields["course"].label_from_instance = lambda c: c.tr("title")

    def clean_phone(self):
        phone = self.cleaned_data["phone"].strip()
        if not PHONE_RE.match(phone):
            raise forms.ValidationError(_("Enter a valid phone number, for example +996 555 123 456."))
        return phone

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("spam")
        return ""
