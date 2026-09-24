from django import forms
from django.conf import settings
from django.contrib.auth import password_validation
from django.db.models import Q
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from accounts.models import User
from accounts.utils import generate_password, transliterate
from core.models import CONTENT_LANGUAGES, WEEKDAYS, Course, EnrollmentRequest, Group, Lesson, News

LANGUAGE_LABELS = {"ru": "RU", "ky": "KY", "en": "EN"}


class MultilingualFormMixin:
    """Группирует поля <name>_ru/_ky/_en во вкладки по языкам."""

    i18n_fields: tuple = ()

    def lang_panes(self):
        panes = []
        for lang in CONTENT_LANGUAGES:
            fields = [self[f"{name}_{lang}"] for name in self.i18n_fields if f"{name}_{lang}" in self.fields]
            panes.append(
                {
                    "code": lang,
                    "label": LANGUAGE_LABELS[lang],
                    "fields": fields,
                    "has_errors": any(f.errors for f in fields),
                    "required": lang == "ru",
                }
            )
        return panes

    def common_fields(self):
        i18n = {f"{name}_{lang}" for name in self.i18n_fields for lang in CONTENT_LANGUAGES}
        return [self[name] for name in self.fields if name not in i18n]


class CourseForm(MultilingualFormMixin, forms.ModelForm):
    i18n_fields = ("title", "short", "description")

    class Meta:
        model = Course
        fields = [
            "title_ru", "title_ky", "title_en",
            "short_ru", "short_ky", "short_en",
            "description_ru", "description_ky", "description_en",
            "direction", "slug", "level", "age_from", "age_to", "duration_months",
            "lessons_per_week", "price", "cover", "teachers", "is_active", "order",
        ]
        labels = {
            "title_ru": _("Title"), "title_ky": _("Title"), "title_en": _("Title"),
            "short_ru": _("Short description"), "short_ky": _("Short description"), "short_en": _("Short description"),
            "description_ru": _("Full description"), "description_ky": _("Full description"),
            "description_en": _("Full description"),
        }
        widgets = {
            "short_ru": forms.Textarea(attrs={"rows": 2}),
            "short_ky": forms.Textarea(attrs={"rows": 2}),
            "short_en": forms.Textarea(attrs={"rows": 2}),
            "description_ru": forms.Textarea(attrs={"rows": 8}),
            "description_ky": forms.Textarea(attrs={"rows": 8}),
            "description_en": forms.Textarea(attrs={"rows": 8}),
            "teachers": forms.CheckboxSelectMultiple,
            "cover": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False
        self.fields["slug"].help_text = _("Part of the page address. Leave empty to generate from the title.")
        self.fields["teachers"].queryset = User.objects.filter(role=User.Role.TEACHER, is_active=True)

    def clean_slug(self):
        slug = self.cleaned_data.get("slug")
        if not slug:
            source = self.cleaned_data.get("title_en") or transliterate(self.cleaned_data.get("title_ru", ""))
            slug = slugify(source)[:70] or "course"
            base, n = slug, 1
            while Course.objects.filter(slug=slug).exclude(pk=self.instance.pk).exists():
                n += 1
                slug = f"{base}-{n}"
        return slug

    def clean(self):
        data = super().clean()
        if data.get("age_from") and data.get("age_to") and data["age_from"] > data["age_to"]:
            self.add_error("age_to", _("The maximum age must not be less than the minimum."))
        return data


class NewsForm(MultilingualFormMixin, forms.ModelForm):
    i18n_fields = ("title", "body")

    class Meta:
        model = News
        fields = [
            "title_ru", "title_ky", "title_en", "body_ru", "body_ky", "body_en",
            "image", "published_at", "is_published", "is_pinned",
        ]
        labels = {
            "title_ru": _("Title"), "title_ky": _("Title"), "title_en": _("Title"),
            "body_ru": _("Text"), "body_ky": _("Text"), "body_en": _("Text"),
        }
        widgets = {
            "body_ru": forms.Textarea(attrs={"rows": 10}),
            "body_ky": forms.Textarea(attrs={"rows": 10}),
            "body_en": forms.Textarea(attrs={"rows": 10}),
            "published_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }


class GroupForm(forms.ModelForm):
    weekdays = forms.TypedMultipleChoiceField(
        label=_("Days of week"),
        choices=WEEKDAYS,
        coerce=int,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "chips"}),
    )

    class Meta:
        model = Group
        fields = ["name", "course", "teacher", "weekdays", "start_time", "end_time", "room", "start_date", "is_active", "students"]
        widgets = {
            "start_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "end_time": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "students": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = Course.objects.all()
        self.fields["course"].label_from_instance = lambda c: c.tr("title")
        self.fields["teacher"].queryset = User.objects.filter(role=User.Role.TEACHER, is_active=True)
        self.fields["students"].queryset = User.objects.filter(role=User.Role.STUDENT).filter(
            Q(is_active=True) | Q(study_groups=self.instance.pk or 0)
        ).distinct()
        self.fields["students"].label_from_instance = lambda u: u.display_name
        if self.instance.pk:
            self.initial["weekdays"] = self.instance.weekday_list

    def clean_weekdays(self):
        return ",".join(str(d) for d in sorted(set(self.cleaned_data.get("weekdays") or [])))

    def clean(self):
        data = super().clean()
        if data.get("start_time") and data.get("end_time") and data["start_time"] >= data["end_time"]:
            self.add_error("end_time", _("The lesson must end after it starts."))
        return data


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ["course", "group", "teacher", "number", "title", "description", "youtube_url", "video_file", "materials", "is_published"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "youtube_url": forms.URLInput(attrs={"placeholder": "https://www.youtube.com/watch?v=…"}),
            "video_file": forms.ClearableFileInput(attrs={"accept": ".mp4,.webm,.mov,video/mp4,video/webm,video/quicktime"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        courses = Course.objects.all()
        groups = Group.objects.select_related("course")
        if user and not user.is_admin_role:
            groups = groups.filter(teacher=user)
            courses = courses.filter(Q(teachers=user) | Q(groups__teacher=user)).distinct()
            self.fields.pop("teacher")
        else:
            self.fields["teacher"].queryset = User.objects.filter(role=User.Role.TEACHER)
            self.fields["teacher"].required = True
        self.fields["course"].queryset = courses
        self.fields["course"].label_from_instance = lambda c: c.tr("title")
        self.fields["group"].queryset = groups
        self.fields["group"].empty_label = _("All groups of the course")
        self.fields["group"].label_from_instance = lambda g: f"{g.name} · {g.course.tr('title')}"
        self.fields["video_file"].help_text = _("MP4, WebM or MOV, up to %(size)s MB.") % {
            "size": settings.MAX_VIDEO_UPLOAD_MB
        }

    def clean(self):
        data = super().clean()
        video = data.get("video_file")
        youtube = data.get("youtube_url")
        if not video and not youtube:
            raise forms.ValidationError(_("Upload a video file or paste a YouTube link."))
        group, course = data.get("group"), data.get("course")
        if group and course and group.course_id != course.pk:
            self.add_error("group", _("The group belongs to a different course."))
        return data


class RequestForm(forms.ModelForm):
    class Meta:
        model = EnrollmentRequest
        fields = ["status", "manager_note"]
        widgets = {"manager_note": forms.Textarea(attrs={"rows": 4, "placeholder": _("Call results, agreements…")})}


class RequestFullForm(forms.ModelForm):
    """Полное редактирование заявки (для администратора и менеджера)."""

    class Meta:
        model = EnrollmentRequest
        fields = ["name", "phone", "email", "age", "course", "message", "status", "manager_note"]
        widgets = {"message": forms.Textarea(attrs={"rows": 3}), "manager_note": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].label_from_instance = lambda c: c.tr("title")


class _AccountFormBase(forms.ModelForm):
    password = forms.CharField(
        label=_("Password"),
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = _("Latin letters, digits and . _ - only.")
        if self.instance.pk:
            self.fields["password"].help_text = _("Leave empty to keep the current password.")
        else:
            self.fields["password"].help_text = _("Leave empty to generate a password automatically.")

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if password:
            password_validation.validate_password(password, self.instance)
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        self.generated_password = None
        if password:
            user.set_password(password)
        elif not user.pk:
            self.generated_password = generate_password()
            user.set_password(self.generated_password)
        if commit:
            user.save()
            self.save_m2m()
        return user


class StudentForm(_AccountFormBase):
    groups_field = forms.ModelMultipleChoiceField(
        label=_("Groups"),
        queryset=Group.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "phone", "email", "photo", "about", "is_active"]
        labels = {"about": _("Note"), "is_active": _("Account is active")}
        widgets = {"about": forms.Textarea(attrs={"rows": 3}), "photo": forms.ClearableFileInput(attrs={"accept": "image/*"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        self.fields["groups_field"].queryset = Group.objects.filter(is_active=True).select_related("course")
        self.fields["groups_field"].label_from_instance = lambda g: f"{g.name} · {g.course.tr('title')}"
        if self.instance.pk:
            self.initial["groups_field"] = list(self.instance.study_groups.values_list("pk", flat=True))

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        if commit:
            user.save()
            self.save_m2m()
            self.save_groups(user)
        return user

    def save_groups(self, user):
        selected = set(self.cleaned_data.get("groups_field") or [])
        active = set(Group.objects.filter(is_active=True, students=user))
        for group in selected - active:
            group.students.add(user)
        for group in active - selected:
            group.students.remove(user)


class UserAdminForm(_AccountFormBase):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "role", "email", "phone", "photo", "specialization", "about", "is_active"]
        labels = {"is_active": _("Account is active"), "about": _("About")}
        widgets = {"about": forms.Textarea(attrs={"rows": 3}), "photo": forms.ClearableFileInput(attrs={"accept": "image/*"})}

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor
        if editor and self.instance.pk == editor.pk:
            # Администратор не может случайно лишить себя доступа.
            self.fields["role"].disabled = True
            self.fields["is_active"].disabled = True


class PasswordResetByAdminForm(forms.Form):
    new_password = forms.CharField(
        label=_("New password"),
        required=False,
        strip=False,
        widget=forms.TextInput(attrs={"autocomplete": "off", "placeholder": _("Leave empty to generate")}),
    )
