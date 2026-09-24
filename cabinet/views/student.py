from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _

from accounts.decorators import role_required
from accounts.models import User
from core.models import Attendance, attendance_percent

from .common import lessons_visible_to, paginate

R = User.Role


def _my_groups(user):
    return (
        user.study_groups.filter(is_active=True)
        .select_related("course", "teacher")
        .annotate(n_students=Count("students", distinct=True))
    )


@role_required(R.STUDENT)
def dashboard(request):
    user = request.user
    groups = list(_my_groups(user))
    today = timezone.localdate()
    upcoming = sorted(
        ({"group": g, "date": d, "is_today": d == today} for g in groups for d in g.upcoming_sessions(days=7)),
        key=lambda s: (s["date"], str(s["group"].start_time or "")),
    )
    records = Attendance.objects.filter(student=user).select_related("group")
    grades = [r.grade for r in records if r.grade]
    return render(
        request,
        "cabinet/student/dashboard.html",
        {
            "groups": groups,
            "upcoming": upcoming[:6],
            "lessons": lessons_visible_to(user).order_by("-created_at")[:3],
            "percent": attendance_percent(records),
            "avg_grade": round(sum(grades) / len(grades), 1) if grades else None,
            "recent_marks": records[:5],
            "lessons_count": lessons_visible_to(user).count(),
            "page_title": _("Overview"),
        },
    )


@role_required(R.STUDENT)
def lessons(request):
    qs = lessons_visible_to(request.user).order_by("course__order", "number")
    by_course = {}
    for lesson in qs:
        by_course.setdefault(lesson.course, []).append(lesson)
    return render(
        request,
        "cabinet/student/lessons.html",
        {"by_course": by_course.items(), "page_title": _("Video lessons")},
    )


@role_required(R.STUDENT)
def attendance(request):
    records = Attendance.objects.filter(student=request.user).select_related("group", "group__course")
    counts = dict(records.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    return render(
        request,
        "cabinet/student/attendance.html",
        {
            "page_obj": paginate(request, records, 25),
            "percent": attendance_percent(records.values_list("status", flat=True)),
            "counts": [{"key": k, "label": l, "count": counts.get(k, 0)} for k, l in Attendance.Status.choices],
            "page_title": _("My attendance"),
        },
    )
