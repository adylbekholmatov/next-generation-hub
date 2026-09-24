"""Боковое меню кабинетов. Пункты зависят от роли пользователя."""
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.models import EnrollmentRequest


def _item(label, url_name, icon, match=None, badge=None, external=False):
    return {
        "label": label,
        "url": url_name if external else reverse(url_name),
        "icon": icon,
        "match": match or [url_name.split(":")[-1]],
        "badge": badge,
        "external": external,
    }


def build_sidebar(user, current):
    new_requests = None
    if user.has_role(user.Role.MANAGER):
        new_requests = EnrollmentRequest.objects.filter(status=EnrollmentRequest.Status.NEW).count() or None

    sections = []
    if user.is_admin_role:
        sections.append(
            (
                _("Administration"),
                [
                    _item(_("Dashboard"), "cabinet:admin_dashboard", "grid"),
                    _item(_("Users"), "cabinet:admin_users", "users", ["admin_user"]),
                    _item(_("Courses"), "cabinet:admin_courses", "book", ["admin_course"]),
                ],
            )
        )
    if user.has_role(user.Role.MANAGER):
        items = []
        if not user.is_admin_role:
            items.append(_item(_("Overview"), "cabinet:manager_dashboard", "grid"))
        items += [
            _item(_("Requests"), "cabinet:manager_requests", "inbox", ["manager_request"], badge=new_requests),
            _item(_("Students"), "cabinet:manager_students", "graduation", ["manager_student"]),
            _item(_("Groups"), "cabinet:manager_groups", "layers", ["manager_group"]),
            _item(_("News"), "cabinet:manager_news", "news", ["manager_news"]),
            _item(_("Attendance journals"), "cabinet:manager_journals", "table", ["manager_journals", "journal_month"]),
        ]
        sections.append((_("Management") if not user.is_admin_role else _("Learning center"), items))
    if user.has_role(user.Role.TEACHER):
        items = []
        if not user.is_admin_role:
            items.append(_item(_("Overview"), "cabinet:teacher_dashboard", "grid"))
        items += [
            _item(_("Video lessons"), "cabinet:teacher_lessons", "video", ["teacher_lesson", "lesson_detail"]),
            _item(_("Mark attendance"), "cabinet:teacher_mark", "clipboard"),
        ]
        if not user.is_admin_role:
            items.append(_item(_("Monthly journal"), "cabinet:teacher_journal", "table", ["teacher_journal", "journal_month"]))
        sections.append((_("Teaching"), items))
    if user.is_student:
        sections.append(
            (
                _("Studying"),
                [
                    _item(_("Overview"), "cabinet:student_dashboard", "grid"),
                    _item(_("Video lessons"), "cabinet:student_lessons", "video", ["student_lesson", "lesson_detail"]),
                    _item(_("My attendance"), "cabinet:student_attendance", "calendar"),
                ],
            )
        )
    account = [
        _item(_("Profile"), "accounts:profile", "user"),
        _item(_("Password"), "accounts:password_change", "key"),
    ]
    if user.is_admin_role:
        account.append(_item(_("Django admin"), "/django-admin/", "database", external=True))
    sections.append((_("Account"), account))

    for _title, items in sections:
        for item in items:
            item["active"] = any(current.startswith(m) for m in item["match"]) and not item["external"]
    # Не подсвечиваем два пункта сразу: оставляем первый совпавший.
    seen = False
    for _title, items in sections:
        for item in items:
            if item["active"] and seen:
                item["active"] = False
            seen = seen or item["active"]
    return sections


def sidebar(request):
    path = request.path
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not (path.startswith("/cabinet/") or path.startswith("/accounts/")):
        return {}
    match = getattr(request, "resolver_match", None)
    current = match.url_name if match and match.url_name else ""
    return {"sidebar_sections": build_sidebar(user, current)}
