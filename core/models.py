import datetime
import re
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

# ---------------------------------------------------------------------------
# Мультиязычность контента
# ---------------------------------------------------------------------------
CONTENT_LANGUAGES = ("ru", "ky", "en")
FALLBACK_LANGUAGE = "ru"


class TranslatableMixin:
    """Даёт метод tr(field): значение поля на текущем языке, иначе — на русском.

    Поля хранятся как <field>_ru, <field>_ky, <field>_en.
    """

    def tr(self, field, lang=None):
        lang = (lang or get_language() or FALLBACK_LANGUAGE).split("-")[0]
        if lang not in CONTENT_LANGUAGES:
            lang = FALLBACK_LANGUAGE
        value = getattr(self, f"{field}_{lang}", "") or ""
        if not value and lang != FALLBACK_LANGUAGE:
            value = getattr(self, f"{field}_{FALLBACK_LANGUAGE}", "") or ""
        return value


# ---------------------------------------------------------------------------
# Направления
# ---------------------------------------------------------------------------
class Direction(models.TextChoices):
    ROBOTICS = "robotics", _("Robotics")
    FRONTEND = "frontend", _("Programming: Frontend")
    BACKEND = "backend", _("Programming: Backend")
    FUSION = "fusion360", _("3D modeling: Fusion 360")
    BLENDER = "blender", _("3D modeling: Blender")


DIRECTION_INFO = {
    Direction.ROBOTICS: {
        "short": _("Robotics"),
        "tagline": _("Arduino, sensors, motors and real robots you build with your own hands."),
    },
    Direction.FRONTEND: {
        "short": _("Frontend"),
        "tagline": _("HTML, CSS and JavaScript: interfaces that people love to use."),
    },
    Direction.BACKEND: {
        "short": _("Backend"),
        "tagline": _("Python, Django, databases and APIs — the engine of every service."),
    },
    Direction.FUSION: {
        "short": _("Fusion 360"),
        "tagline": _("Engineering 3D design, drawings and models ready for 3D printing."),
    },
    Direction.BLENDER: {
        "short": _("Blender"),
        "tagline": _("Modeling, materials, light and animation for games and film."),
    },
}


def directions():
    """Список направлений для шаблонов: код, название, короткое имя, описание."""
    return [
        {"code": value, "label": label, **DIRECTION_INFO[value]}
        for value, label in Direction.choices
    ]


# ---------------------------------------------------------------------------
# Курс
# ---------------------------------------------------------------------------
class Course(TranslatableMixin, models.Model):
    class Level(models.TextChoices):
        BEGINNER = "beginner", _("Beginner")
        INTERMEDIATE = "intermediate", _("Intermediate")
        ADVANCED = "advanced", _("Advanced")

    direction = models.CharField(_("direction"), max_length=20, choices=Direction.choices, db_index=True)
    slug = models.SlugField(_("slug"), max_length=80, unique=True)
    title_ru = models.CharField(_("title (RU)"), max_length=160)
    title_ky = models.CharField(_("title (KY)"), max_length=160, blank=True)
    title_en = models.CharField(_("title (EN)"), max_length=160, blank=True)
    short_ru = models.CharField(_("short description (RU)"), max_length=300, blank=True)
    short_ky = models.CharField(_("short description (KY)"), max_length=300, blank=True)
    short_en = models.CharField(_("short description (EN)"), max_length=300, blank=True)
    description_ru = models.TextField(_("full description (RU)"), blank=True)
    description_ky = models.TextField(_("full description (KY)"), blank=True)
    description_en = models.TextField(_("full description (EN)"), blank=True)
    level = models.CharField(_("level"), max_length=20, choices=Level.choices, default=Level.BEGINNER)
    age_from = models.PositiveSmallIntegerField(_("age from"), default=10)
    age_to = models.PositiveSmallIntegerField(_("age to"), default=17)
    duration_months = models.PositiveSmallIntegerField(_("duration, months"), default=6)
    lessons_per_week = models.PositiveSmallIntegerField(_("lessons per week"), default=2)
    price = models.PositiveIntegerField(_("price, KGS per month"), default=0)
    cover = models.ImageField(_("cover"), upload_to="courses/", blank=True)
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("teachers"),
        related_name="courses_taught",
        blank=True,
        limit_choices_to={"role": "teacher"},
    )
    is_active = models.BooleanField(_("active"), default=True)
    order = models.PositiveSmallIntegerField(_("order"), default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("course")
        verbose_name_plural = _("courses")
        ordering = ["order", "title_ru"]

    def __str__(self):
        return self.title_ru

    def get_absolute_url(self):
        return reverse("core:course_detail", args=[self.slug])

    @property
    def age_range(self):
        return f"{self.age_from}–{self.age_to}"

    @property
    def direction_info(self):
        return DIRECTION_INFO.get(self.direction, {})


# ---------------------------------------------------------------------------
# Группа
# ---------------------------------------------------------------------------
WEEKDAYS = [
    (0, _("Mon")),
    (1, _("Tue")),
    (2, _("Wed")),
    (3, _("Thu")),
    (4, _("Fri")),
    (5, _("Sat")),
    (6, _("Sun")),
]


class Group(models.Model):
    name = models.CharField(_("name"), max_length=120)
    course = models.ForeignKey(Course, verbose_name=_("course"), on_delete=models.PROTECT, related_name="groups")
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("teacher"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teaching_groups",
        limit_choices_to={"role": "teacher"},
    )
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("students"),
        related_name="study_groups",
        blank=True,
        limit_choices_to={"role": "student"},
    )
    weekdays = models.CharField(
        _("days of week"), max_length=20, blank=True, help_text=_("Comma-separated numbers: 0 = Monday … 6 = Sunday.")
    )
    start_time = models.TimeField(_("start time"), null=True, blank=True)
    end_time = models.TimeField(_("end time"), null=True, blank=True)
    room = models.CharField(_("room"), max_length=60, blank=True)
    start_date = models.DateField(_("start date"), default=datetime.date.today)
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("group")
        verbose_name_plural = _("groups")
        ordering = ["-is_active", "name"]

    def __str__(self):
        return self.name

    @property
    def weekday_list(self):
        return sorted({int(d) for d in re.findall(r"\d", self.weekdays or "") if int(d) < 7})

    @property
    def schedule_display(self):
        labels = dict(WEEKDAYS)
        days = ", ".join(str(labels[d]) for d in self.weekday_list)
        if self.start_time and self.end_time:
            time = f"{self.start_time:%H:%M}–{self.end_time:%H:%M}"
            return f"{days} · {time}" if days else time
        return days

    def is_lesson_day(self, day):
        return day.weekday() in self.weekday_list

    def upcoming_sessions(self, days=7, start=None):
        """Ближайшие занятия по расписанию группы."""
        start = start or timezone.localdate()
        now = timezone.localtime()
        result = []
        for offset in range(days):
            day = start + datetime.timedelta(days=offset)
            if day < self.start_date or not self.is_lesson_day(day):
                continue
            if offset == 0 and self.end_time and now.time() > self.end_time:
                continue
            result.append(day)
        return result

    def lesson_dates_in_range(self, first, last):
        today = timezone.localdate()
        day = max(first, self.start_date)
        dates = []
        while day <= last and day <= today:
            if self.is_lesson_day(day):
                dates.append(day)
            day += datetime.timedelta(days=1)
        return dates


# ---------------------------------------------------------------------------
# Видеоурок
# ---------------------------------------------------------------------------
YOUTUBE_ID_RE = re.compile(
    r"(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|live/|v/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def youtube_id(url):
    match = YOUTUBE_ID_RE.search(url or "")
    return match.group(1) if match else ""


def validate_video_file(file):
    ext = Path(file.name).suffix.lower().lstrip(".")
    allowed = settings.VIDEO_EXTENSIONS
    if ext not in allowed:
        raise ValidationError(
            _("Unsupported video format. Allowed: %(formats)s."),
            params={"formats": ", ".join(allowed)},
            code="video_ext",
        )
    limit = settings.MAX_VIDEO_UPLOAD_MB * 1024 * 1024
    if file.size and file.size > limit:
        raise ValidationError(
            _("The video is too large. Maximum size is %(size)s MB."),
            params={"size": settings.MAX_VIDEO_UPLOAD_MB},
            code="video_size",
        )


def validate_youtube_url(url):
    if url and not youtube_id(url):
        raise ValidationError(_("This does not look like a YouTube video link."), code="youtube")


class Lesson(models.Model):
    course = models.ForeignKey(Course, verbose_name=_("course"), on_delete=models.CASCADE, related_name="lessons")
    group = models.ForeignKey(
        Group,
        verbose_name=_("group"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lessons",
        help_text=_("Leave empty to show the lesson to all groups of the course."),
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("teacher"),
        on_delete=models.SET_NULL,
        null=True,
        related_name="lessons",
    )
    number = models.PositiveSmallIntegerField(_("lesson number"), default=1)
    title = models.CharField(_("title"), max_length=200)
    description = models.TextField(_("description"), blank=True)
    video_file = models.FileField(
        _("video file"), upload_to="lessons/video/%Y/%m/", blank=True, validators=[validate_video_file]
    )
    youtube_url = models.URLField(_("YouTube link"), blank=True, validators=[validate_youtube_url])
    materials = models.FileField(_("materials"), upload_to="lessons/materials/%Y/%m/", blank=True)
    is_published = models.BooleanField(_("published"), default=True)
    created_at = models.DateTimeField(_("created"), auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("video lesson")
        verbose_name_plural = _("video lessons")
        ordering = ["course", "number", "-created_at"]

    def __str__(self):
        return f"{self.number}. {self.title}"

    def clean(self):
        if not self.video_file and not self.youtube_url:
            raise ValidationError(_("Upload a video file or paste a YouTube link."))
        if self.group_id and self.course_id and self.group.course_id != self.course_id:
            raise ValidationError({"group": _("The group belongs to a different course.")})

    @property
    def youtube_id(self):
        return youtube_id(self.youtube_url)

    @property
    def youtube_embed_url(self):
        vid = self.youtube_id
        return f"https://www.youtube-nocookie.com/embed/{vid}?rel=0" if vid else ""

    @property
    def youtube_thumbnail(self):
        vid = self.youtube_id
        return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else ""

    @property
    def video_mime(self):
        ext = Path(self.video_file.name).suffix.lower()
        return {".webm": "video/webm", ".mov": "video/quicktime"}.get(ext, "video/mp4")

    @property
    def source_label(self):
        return "YouTube" if self.youtube_url and not self.video_file else _("File")

    @property
    def materials_name(self):
        return Path(self.materials.name).name if self.materials else ""


# ---------------------------------------------------------------------------
# Журнал посещаемости
# ---------------------------------------------------------------------------
class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", _("Present")
        LATE = "late", _("Late")
        ABSENT = "absent", _("Absent")
        EXCUSED = "excused", _("Excused")

    group = models.ForeignKey(Group, verbose_name=_("group"), on_delete=models.CASCADE, related_name="attendance")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_("student"), on_delete=models.CASCADE, related_name="attendance"
    )
    date = models.DateField(_("date"), db_index=True)
    status = models.CharField(_("status"), max_length=10, choices=Status.choices, default=Status.PRESENT)
    grade = models.PositiveSmallIntegerField(
        _("grade"), null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.CharField(_("comment"), max_length=255, blank=True)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("marked by"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("attendance record")
        verbose_name_plural = _("attendance")
        unique_together = ("group", "student", "date")
        ordering = ["-date", "student__last_name"]

    def __str__(self):
        return f"{self.group} · {self.student} · {self.date:%d.%m.%Y}"

    @property
    def attended(self):
        return self.status in (self.Status.PRESENT, self.Status.LATE)

    @property
    def short_label(self):
        return STATUS_SHORT.get(self.status, "")

    @classmethod
    def status_options(cls):
        return [{"value": v, "label": label, "short": STATUS_SHORT[v]} for v, label in cls.Status.choices]


# Короткие обозначения статусов для журнала (одна-две буквы).
STATUS_SHORT = {
    Attendance.Status.PRESENT: pgettext_lazy("attendance", "P"),
    Attendance.Status.LATE: pgettext_lazy("attendance", "L"),
    Attendance.Status.ABSENT: pgettext_lazy("attendance", "A"),
    Attendance.Status.EXCUSED: pgettext_lazy("attendance", "E"),
}


def attendance_percent(records):
    """Процент посещаемости: (присутствовал + опоздал) / (все отметки − уважительные).

    Принимает список Attendance или список статусов.
    """
    statuses = [r.status if hasattr(r, "status") else r for r in records]
    counted = [s for s in statuses if s != Attendance.Status.EXCUSED]
    if not counted:
        return None
    attended = sum(1 for s in counted if s in (Attendance.Status.PRESENT, Attendance.Status.LATE))
    return round(attended * 100 / len(counted))


# ---------------------------------------------------------------------------
# Новости
# ---------------------------------------------------------------------------
class News(TranslatableMixin, models.Model):
    title_ru = models.CharField(_("title (RU)"), max_length=200)
    title_ky = models.CharField(_("title (KY)"), max_length=200, blank=True)
    title_en = models.CharField(_("title (EN)"), max_length=200, blank=True)
    body_ru = models.TextField(_("text (RU)"))
    body_ky = models.TextField(_("text (KY)"), blank=True)
    body_en = models.TextField(_("text (EN)"), blank=True)
    image = models.ImageField(_("image"), upload_to="news/", blank=True)
    is_published = models.BooleanField(_("published"), default=True)
    is_pinned = models.BooleanField(_("pinned"), default=False)
    published_at = models.DateTimeField(_("publication date"), default=timezone.now, db_index=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("author"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="news",
    )

    class Meta:
        verbose_name = _("news item")
        verbose_name_plural = _("news")
        ordering = ["-is_pinned", "-published_at"]

    def __str__(self):
        return self.title_ru

    def get_absolute_url(self):
        return reverse("core:news_detail", args=[self.pk])

    @classmethod
    def visible(cls):
        return cls.objects.filter(is_published=True, published_at__lte=timezone.now())


# ---------------------------------------------------------------------------
# Заявка с сайта
# ---------------------------------------------------------------------------
class EnrollmentRequest(models.Model):
    class Status(models.TextChoices):
        NEW = "new", _("New")
        CONTACTED = "contacted", _("Contacted")
        ENROLLED = "enrolled", _("Enrolled")
        REJECTED = "rejected", _("Rejected")

    name = models.CharField(_("name"), max_length=120)
    phone = models.CharField(_("phone"), max_length=32)
    email = models.EmailField(_("email"), blank=True)
    age = models.PositiveSmallIntegerField(
        _("age"), null=True, blank=True, validators=[MinValueValidator(5), MaxValueValidator(99)]
    )
    course = models.ForeignKey(
        Course, verbose_name=_("course"), on_delete=models.SET_NULL, null=True, blank=True, related_name="requests"
    )
    message = models.TextField(_("message"), blank=True)
    status = models.CharField(_("status"), max_length=12, choices=Status.choices, default=Status.NEW, db_index=True)
    manager_note = models.TextField(_("manager note"), blank=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("handled by"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_requests",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("student account"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrollment_requests",
    )
    created_at = models.DateTimeField(_("received"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("enrollment request")
        verbose_name_plural = _("enrollment requests")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} · {self.phone}"
