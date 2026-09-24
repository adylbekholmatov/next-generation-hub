import datetime

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from core.models import Attendance, Lesson, attendance_percent

from ..forms import LessonForm
from .common import get_allowed_or_403, groups_for, is_ajax, paginate, with_month_percent

R = User.Role


@role_required(R.TEACHER)
def dashboard(request):
    user = request.user
    groups = list(
        groups_for(user).filter(is_active=True).annotate(n_students=Count("students", distinct=True))
    )
    since = timezone.localdate() - datetime.timedelta(days=30)
    recent = Attendance.objects.filter(group__in=groups, date__gte=since)
    status_counts = dict(recent.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    per_group = {}
    for group_id, status in recent.values_list("group_id", "status"):
        per_group.setdefault(group_id, []).append(status)
    for g in groups:
        g.percent = attendance_percent(per_group.get(g.pk, []))

    today = timezone.localdate()
    upcoming = []
    for g in groups:
        for day in g.upcoming_sessions(days=7):
            upcoming.append({"group": g, "date": day, "is_today": day == today})
    upcoming.sort(key=lambda s: (s["date"], s["group"].start_time or datetime.time.min))

    marked_today = set(
        Attendance.objects.filter(group__in=groups, date=today).values_list("group_id", flat=True).distinct()
    )
    for s in upcoming:
        s["marked"] = s["is_today"] and s["group"].pk in marked_today

    total = sum(status_counts.values())
    stats = [
        {"key": key, "label": label, "count": status_counts.get(key, 0),
         "share": round(status_counts.get(key, 0) * 100 / total) if total else 0}
        for key, label in Attendance.Status.choices
    ]
    return render(
        request,
        "cabinet/teacher/dashboard.html",
        {
            "groups": groups,
            "upcoming": upcoming[:8],
            "stats": stats,
            "overall": attendance_percent(recent.values_list("status", flat=True)),
            "students_total": sum(g.n_students for g in groups),
            "lessons_total": Lesson.objects.filter(teacher=user).count(),
            "recent_lessons": Lesson.objects.filter(teacher=user).select_related("course", "group")[:4],
            "page_title": _("Overview"),
        },
    )


# ---------------------------------------------------------------------------
# Видеоуроки
# ---------------------------------------------------------------------------
def _lessons_for(user):
    qs = Lesson.objects.select_related("course", "group", "teacher")
    return qs if user.is_admin_role else qs.filter(teacher=user)


@role_required(R.TEACHER)
def lesson_list(request):
    lessons = _lessons_for(request.user).order_by("-created_at")
    q = request.GET.get("q", "").strip()
    course = request.GET.get("course", "")
    if q:
        lessons = lessons.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if course.isdigit():
        lessons = lessons.filter(course_id=course)
    courses = {l.course for l in _lessons_for(request.user).select_related("course")}
    return render(
        request,
        "cabinet/teacher/lesson_list.html",
        {
            "page_obj": paginate(request, lessons, 12),
            "courses": sorted(courses, key=lambda c: c.order),
            "q": q,
            "course_filter": course,
            "page_title": _("Video lessons"),
        },
    )


def _lesson_form_response(request, form, lesson=None):
    if request.method == "POST" and is_ajax(request):
        errors = {field: [str(e) for e in errs] for field, errs in form.errors.items()}
        return JsonResponse({"ok": False, "errors": errors}, status=400)
    return render(
        request,
        "cabinet/teacher/lesson_form.html",
        {
            "form": form,
            "lesson": lesson,
            "page_title": _("Edit lesson") if lesson else _("New video lesson"),
        },
    )


def _lesson_saved(request, lesson, created):
    messages.success(request, _("Lesson saved.") if not created else _("Lesson uploaded."))
    url = reverse("cabinet:teacher_lessons")
    if is_ajax(request):
        return JsonResponse({"ok": True, "redirect": url, "id": lesson.pk})
    return redirect(url)


@role_required(R.TEACHER)
def lesson_create(request):
    form = LessonForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "GET":
        initial_group = request.GET.get("group")
        if initial_group and initial_group.isdigit():
            group = groups_for(request.user).filter(pk=initial_group).first()
            if group:
                form.initial.update({"group": group.pk, "course": group.course_id})
        last = Lesson.objects.filter(teacher=request.user).order_by("-number").first()
        form.initial.setdefault("number", (last.number + 1) if last else 1)
    if request.method == "POST" and form.is_valid():
        lesson = form.save(commit=False)
        if not request.user.is_admin_role or not lesson.teacher_id:
            lesson.teacher = request.user
        lesson.save()
        return _lesson_saved(request, lesson, created=True)
    return _lesson_form_response(request, form)


@role_required(R.TEACHER)
def lesson_edit(request, pk):
    lesson = get_allowed_or_403(_lessons_for(request.user), Lesson, pk)
    form = LessonForm(request.POST or None, request.FILES or None, instance=lesson, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return _lesson_saved(request, lesson, created=False)
    return _lesson_form_response(request, form, lesson)


@role_required(R.TEACHER)
@require_POST
def lesson_delete(request, pk):
    lesson = get_allowed_or_403(_lessons_for(request.user), Lesson, pk)
    for f in (lesson.video_file, lesson.materials):
        if f:
            f.delete(save=False)
    lesson.delete()
    messages.success(request, _("Lesson deleted."))
    return redirect("cabinet:teacher_lessons")


# ---------------------------------------------------------------------------
# Журнал: отметка занятия
# ---------------------------------------------------------------------------
def _markable_groups(user):
    qs = groups_for(user).filter(is_active=True)
    return qs if user.is_admin_role else qs.filter(teacher=user)


@role_required(R.TEACHER)
def mark_attendance(request):
    groups = list(_markable_groups(request.user))
    today = timezone.localdate()
    source = request.POST if request.method == "POST" else request.GET

    group = None
    group_id = source.get("group")
    if group_id and str(group_id).isdigit():
        group = next((g for g in groups if g.pk == int(group_id)), None)
        if group is None:
            # Чужая группа или несуществующая — доступ запрещён.
            raise PermissionDenied
    elif len(groups) == 1:
        group = groups[0]

    day = parse_date(source.get("date") or "") or today
    date_error = day > today

    students, existing = [], {}
    if group:
        students = list(group.students.filter(is_active=True).order_by("last_name", "first_name"))
        existing = {a.student_id: a for a in Attendance.objects.filter(group=group, date=day)}

    if request.method == "POST" and group:
        if date_error:
            messages.error(request, _("You cannot mark a lesson in the future."))
        else:
            saved = _save_attendance(request, group, day, students)
            messages.success(request, _("Journal saved: %(n)s students.") % {"n": saved})
            return redirect(f'{reverse("cabinet:teacher_mark")}?group={group.pk}&date={day:%Y-%m-%d}')

    rows = []
    for s in students:
        rec = existing.get(s.pk)
        rows.append(
            {
                "student": s,
                "status": rec.status if rec else "",
                "grade": rec.grade if rec and rec.grade else "",
                "comment": rec.comment if rec else "",
            }
        )
    return render(
        request,
        "cabinet/teacher/mark.html",
        {
            "groups": groups,
            "group": group,
            "day": day,
            "today": today,
            "date_error": date_error,
            "rows": rows,
            "is_lesson_day": group.is_lesson_day(day) if group else False,
            "already_marked": bool(existing),
            "statuses": Attendance.status_options(),
            "page_title": _("Mark attendance"),
        },
    )


@transaction.atomic
def _save_attendance(request, group, day, students):
    saved = 0
    valid_statuses = set(Attendance.Status.values)
    for s in students:
        status = request.POST.get(f"status_{s.pk}")
        if status not in valid_statuses:
            continue
        grade = request.POST.get(f"grade_{s.pk}", "").strip()
        grade = int(grade) if grade.isdigit() and 1 <= int(grade) <= 5 else None
        if status in (Attendance.Status.ABSENT, Attendance.Status.EXCUSED):
            grade = None
        comment = request.POST.get(f"comment_{s.pk}", "").strip()[:255]
        Attendance.objects.update_or_create(
            group=group,
            student=s,
            date=day,
            defaults={"status": status, "grade": grade, "comment": comment, "marked_by": request.user},
        )
        saved += 1
    return saved


@role_required(R.TEACHER)
def journal(request):
    """Выбор группы для журнала за месяц."""
    groups = list(_markable_groups(request.user))
    if len(groups) == 1:
        return redirect("cabinet:journal_month", pk=groups[0].pk)
    return render(
        request,
        "cabinet/shared/journal_groups.html",
        {"groups": with_month_percent(groups), "page_title": _("Monthly journal")},
    )
