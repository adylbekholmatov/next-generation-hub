import datetime

from django.contrib import messages
from django.contrib.auth import password_validation, update_session_auth_hash
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.db.models.functions import TruncWeek
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from accounts.utils import generate_password
from core.models import Attendance, Course, EnrollmentRequest, Group, Lesson, News, attendance_percent
from core.models import directions as direction_list

from ..forms import CourseForm, PasswordResetByAdminForm, UserAdminForm
from .common import paginate

R = User.Role
ADMIN = R.ADMIN


@role_required(ADMIN)
def dashboard(request):
    today = timezone.localdate()
    since = today - datetime.timedelta(days=30)
    users = dict(User.objects.filter(is_active=True).values_list("role").annotate(n=Count("id")).values_list("role", "n"))
    recent_statuses = list(Attendance.objects.filter(date__gte=since).values_list("status", flat=True))

    # График 1: посещаемость по группам за 30 дней.
    per_group = {}
    for gid, status in Attendance.objects.filter(date__gte=since).values_list("group_id", "status"):
        per_group.setdefault(gid, []).append(status)
    group_bars = []
    for g in Group.objects.filter(is_active=True).select_related("course"):
        value = attendance_percent(per_group.get(g.pk, []))
        group_bars.append({"label": g.name, "value": value or 0, "empty": value is None, "url_pk": g.pk})
    group_bars.sort(key=lambda b: -b["value"])

    # График 2: заявки по неделям (8 недель).
    start = today - datetime.timedelta(days=today.weekday() + 7 * 7)
    weekly = dict(
        EnrollmentRequest.objects.filter(created_at__date__gte=start)
        .annotate(week=TruncWeek("created_at"))
        .values_list("week")
        .annotate(n=Count("id"))
        .values_list("week", "n")
    )
    weekly = {k.date() if hasattr(k, "date") else k: v for k, v in weekly.items()}
    weeks = []
    for i in range(8):
        wk = start + datetime.timedelta(weeks=i)
        weeks.append({"date": wk, "count": weekly.get(wk, 0)})
    max_week = max([w["count"] for w in weeks] + [1])
    for w in weeks:
        w["height"] = round(w["count"] * 100 / max_week)

    # График 3: студенты по направлениям.
    by_direction = dict(
        Group.objects.filter(is_active=True)
        .values_list("course__direction")
        .annotate(n=Count("students", distinct=True))
        .values_list("course__direction", "n")
    )
    max_dir = max(list(by_direction.values()) + [1])
    directions = [
        {**d, "count": by_direction.get(d["code"], 0), "width": round(by_direction.get(d["code"], 0) * 100 / max_dir)}
        for d in direction_list()
    ]

    request_counts = dict(
        EnrollmentRequest.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n")
    )
    return render(
        request,
        "cabinet/admin/dashboard.html",
        {
            "kpi": {
                "students": users.get(R.STUDENT, 0),
                "teachers": users.get(R.TEACHER, 0),
                "groups": Group.objects.filter(is_active=True).count(),
                "new_requests": request_counts.get(EnrollmentRequest.Status.NEW, 0),
                "attendance": attendance_percent(recent_statuses),
                "lessons": Lesson.objects.count(),
                "courses": Course.objects.filter(is_active=True).count(),
                "news": News.objects.filter(is_published=True).count(),
            },
            "group_bars": group_bars,
            "weeks": weeks,
            "directions": directions,
            "latest_requests": EnrollmentRequest.objects.select_related("course")[:6],
            "latest_lessons": Lesson.objects.select_related("course", "teacher")[:5],
            "page_title": _("Dashboard"),
        },
    )


# ---------------------------------------------------------------------------
# Пользователи
# ---------------------------------------------------------------------------
@role_required(ADMIN)
def user_list(request):
    qs = User.objects.all()
    role = request.GET.get("role", "")
    q = request.GET.get("q", "").strip()
    state = request.GET.get("state", "")
    if role in R.values:
        qs = qs.filter(role=role)
    if state == "blocked":
        qs = qs.filter(is_active=False)
    if q:
        qs = qs.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
            | Q(email__icontains=q) | Q(phone__icontains=q)
        )
    counts = dict(User.objects.values_list("role").annotate(n=Count("id")).values_list("role", "n"))
    return render(
        request,
        "cabinet/admin/user_list.html",
        {
            "page_obj": paginate(request, qs, 25),
            "roles": [{"key": k, "label": l, "count": counts.get(k, 0)} for k, l in R.choices],
            "total": sum(counts.values()),
            "role_filter": role,
            "state": state,
            "q": q,
            "page_title": _("Users"),
        },
    )


@role_required(ADMIN)
def user_create(request):
    form = UserAdminForm(request.POST or None, request.FILES or None, editor=request.user,
                         initial={"role": request.GET.get("role", R.STUDENT), "is_active": True})
    if request.method == "POST" and form.is_valid():
        user = form.save()
        if form.generated_password:
            messages.success(
                request,
                _("User created. Login: %(login)s, password: %(password)s")
                % {"login": user.username, "password": form.generated_password},
                extra_tags="sticky",
            )
        else:
            messages.success(request, _("User created."))
        return redirect("cabinet:admin_users")
    return render(request, "cabinet/admin/user_form.html", {"form": form, "page_title": _("New user")})


@role_required(ADMIN)
def user_edit(request, pk):
    target = get_object_or_404(User, pk=pk)
    form = UserAdminForm(request.POST or None, request.FILES or None, instance=target, editor=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("User saved."))
        return redirect("cabinet:admin_users")
    return render(
        request,
        "cabinet/admin/user_form.html",
        {"form": form, "target": target, "reset_form": PasswordResetByAdminForm(), "page_title": target.display_name},
    )


@role_required(ADMIN)
@require_POST
def user_password(request, pk):
    target = get_object_or_404(User, pk=pk)
    form = PasswordResetByAdminForm(request.POST)
    form.is_valid()
    password = form.cleaned_data.get("new_password") or generate_password()
    try:
        password_validation.validate_password(password, target)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("cabinet:admin_user_edit", pk=pk)
    target.set_password(password)
    target.save(update_fields=["password"])
    if target.pk == request.user.pk:
        update_session_auth_hash(request, target)
    messages.success(
        request,
        _("New password for %(login)s: %(password)s") % {"login": target.username, "password": password},
        extra_tags="sticky",
    )
    return redirect("cabinet:admin_user_edit", pk=pk)


@role_required(ADMIN)
@require_POST
def user_toggle(request, pk):
    target = get_object_or_404(User, pk=pk)
    if target.pk == request.user.pk:
        messages.error(request, _("You cannot block yourself."))
    else:
        target.is_active = not target.is_active
        target.save(update_fields=["is_active"])
        if target.is_active:
            messages.success(request, _("User %(name)s unblocked.") % {"name": target.display_name})
        else:
            messages.success(request, _("User %(name)s blocked.") % {"name": target.display_name})
    back = request.POST.get("next", "")
    return redirect(back if back.startswith("/cabinet/") else "cabinet:admin_users")


# ---------------------------------------------------------------------------
# Курсы
# ---------------------------------------------------------------------------
@role_required(ADMIN)
def course_list(request):
    courses = Course.objects.prefetch_related("teachers").annotate(
        n_groups=Count("groups", distinct=True), n_lessons=Count("lessons", distinct=True)
    )
    return render(request, "cabinet/admin/course_list.html", {"courses": courses, "page_title": _("Courses")})


def _course_form(request, course=None):
    form = CourseForm(request.POST or None, request.FILES or None, instance=course)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Course saved."))
        return redirect("cabinet:admin_courses")
    return render(
        request,
        "cabinet/admin/course_form.html",
        {"form": form, "course": course, "page_title": course.title_ru if course else _("New course")},
    )


@role_required(ADMIN)
def course_create(request):
    return _course_form(request)


@role_required(ADMIN)
def course_edit(request, pk):
    return _course_form(request, get_object_or_404(Course, pk=pk))


@role_required(ADMIN)
@require_POST
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if course.groups.exists():
        course.is_active = False
        course.save(update_fields=["is_active"])
        messages.info(request, _("The course has groups, so it was hidden from the site instead of being deleted."))
    else:
        course.delete()
        messages.success(request, _("Course deleted."))
    return redirect("cabinet:admin_courses")

