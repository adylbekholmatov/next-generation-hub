from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.decorators import role_required
from accounts.models import User
from core.models import Attendance, Group, Lesson, attendance_percent

from ..journal import build_month_journal, export_csv, export_xlsx, parse_month

R = User.Role


def get_allowed_or_403(queryset, model, pk):
    """Объект из разрешённого набора; существующий, но чужой — 403, несуществующий — 404."""
    obj = queryset.filter(pk=pk).first()
    if obj is None:
        if model.objects.filter(pk=pk).exists():
            raise PermissionDenied
        raise Http404
    return obj


def paginate(request, queryset, per_page=20):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def groups_for(user):
    """Группы, которые пользователь может вести / просматривать в журнале."""
    qs = Group.objects.select_related("course", "teacher")
    if user.has_role(R.MANAGER):  # админ и менеджер видят все группы
        return qs
    if user.is_teacher:
        return qs.filter(teacher=user)
    return qs.none()


def lessons_visible_to(user):
    qs = Lesson.objects.select_related("course", "group", "teacher")
    if user.has_role(R.MANAGER):
        return qs
    if user.is_teacher:
        return qs.filter(teacher=user)
    if user.is_student:
        groups = user.study_groups.filter(is_active=True)
        return qs.filter(is_published=True).filter(
            Q(group__in=groups) | Q(group__isnull=True, course__groups__in=groups)
        ).distinct()
    return qs.none()


def with_month_percent(groups):
    """Добавляет группам процент посещаемости за текущий месяц и число студентов."""
    groups = list(groups)
    month_start = timezone.localdate().replace(day=1)
    statuses = {}
    for group_id, status in Attendance.objects.filter(group__in=groups, date__gte=month_start).values_list(
        "group_id", "status"
    ):
        statuses.setdefault(group_id, []).append(status)
    counts = dict(
        Group.students.through.objects.filter(group_id__in=[g.pk for g in groups])
        .values_list("group_id")
        .annotate(n=Count("id"))
        .values_list("group_id", "n")
    )
    for g in groups:
        g.month_percent = attendance_percent(statuses.get(g.pk, []))
        g.month_marks = len(statuses.get(g.pk, []))
        g.n_students = counts.get(g.pk, 0)
    return groups


@login_required
def home(request):
    user = request.user
    if user.is_admin_role:
        return redirect("cabinet:admin_dashboard")
    target = {
        R.MANAGER: "cabinet:manager_dashboard",
        R.TEACHER: "cabinet:teacher_dashboard",
        R.STUDENT: "cabinet:student_dashboard",
    }.get(user.role)
    if not target:
        raise PermissionDenied
    return redirect(target)


@login_required
def lesson_detail(request, pk):
    lesson = get_allowed_or_403(lessons_visible_to(request.user), Lesson, pk)
    siblings = lessons_visible_to(request.user).filter(course=lesson.course).order_by("number", "created_at")
    siblings = list(siblings)
    index = next((i for i, item in enumerate(siblings) if item.pk == lesson.pk), 0)
    return render(
        request,
        "cabinet/shared/lesson_detail.html",
        {
            "lesson": lesson,
            "siblings": siblings,
            "prev_lesson": siblings[index - 1] if index > 0 else None,
            "next_lesson": siblings[index + 1] if index + 1 < len(siblings) else None,
            "can_edit": request.user.is_admin_role or lesson.teacher_id == request.user.pk,
            "page_title": lesson.title,
        },
    )


def _journal_group(request, pk):
    return get_allowed_or_403(groups_for(request.user), Group, pk)


@role_required(R.TEACHER, R.MANAGER)
def journal_month(request, pk):
    group = _journal_group(request, pk)
    journal = build_month_journal(group, parse_month(request.GET.get("month")))
    can_mark = request.user.is_admin_role or group.teacher_id == request.user.pk
    return render(
        request,
        "cabinet/shared/journal_month.html",
        {
            "j": journal,
            "can_mark": can_mark,
            "groups": groups_for(request.user).filter(is_active=True),
            "page_title": group.name,
        },
    )


@role_required(R.TEACHER, R.MANAGER)
def journal_export(request, pk, fmt):
    if fmt not in ("csv", "xlsx"):
        raise Http404
    group = _journal_group(request, pk)
    journal = build_month_journal(group, parse_month(request.GET.get("month")))
    if fmt == "xlsx":
        return export_xlsx(journal)
    return export_csv(journal)
