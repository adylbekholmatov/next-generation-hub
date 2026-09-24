from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from accounts.utils import generate_username, split_full_name
from core.models import Course, EnrollmentRequest, Group, News

from ..forms import GroupForm, NewsForm, RequestForm, RequestFullForm, StudentForm
from .common import groups_for, paginate, with_month_percent

R = User.Role
S = EnrollmentRequest.Status


def _credentials_message(request, user, password):
    messages.success(
        request,
        _("Account created. Login: %(login)s, password: %(password)s — pass them to the student.")
        % {"login": user.username, "password": password},
        extra_tags="sticky",
    )


@role_required(R.MANAGER)
def dashboard(request):
    counts = dict(EnrollmentRequest.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    week_ago = timezone.now() - timezone.timedelta(days=7)
    return render(
        request,
        "cabinet/manager/dashboard.html",
        {
            "status_cards": [
                {"key": key, "label": label, "count": counts.get(key, 0)} for key, label in S.choices
            ],
            "new_requests": EnrollmentRequest.objects.filter(status=S.NEW).select_related("course")[:6],
            "week_requests": EnrollmentRequest.objects.filter(created_at__gte=week_ago).count(),
            "students_count": User.objects.filter(role=R.STUDENT, is_active=True).count(),
            "groups": with_month_percent(groups_for(request.user).filter(is_active=True)[:6]),
            "news_count": News.objects.filter(is_published=True).count(),
            "page_title": _("Overview"),
        },
    )


# ---------------------------------------------------------------------------
# Заявки
# ---------------------------------------------------------------------------
@role_required(R.MANAGER)
def request_list(request):
    qs = EnrollmentRequest.objects.select_related("course", "handled_by", "student")
    status = request.GET.get("status", "")
    course = request.GET.get("course", "")
    q = request.GET.get("q", "").strip()
    if status in S.values:
        qs = qs.filter(status=status)
    if course.isdigit():
        qs = qs.filter(course_id=course)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q))
    counts = dict(EnrollmentRequest.objects.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    return render(
        request,
        "cabinet/manager/request_list.html",
        {
            "page_obj": paginate(request, qs, 20),
            "statuses": [{"key": k, "label": l, "count": counts.get(k, 0)} for k, l in S.choices],
            "total": sum(counts.values()),
            "courses": Course.objects.all(),
            "status_filter": status,
            "course_filter": course,
            "q": q,
            "page_title": _("Requests"),
        },
    )


@role_required(R.MANAGER)
def request_detail(request, pk):
    obj = get_object_or_404(EnrollmentRequest.objects.select_related("course", "handled_by", "student"), pk=pk)
    form_class = RequestFullForm if request.GET.get("full") or "name" in request.POST else RequestForm
    form = form_class(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.handled_by = request.user
        item.save()
        messages.success(request, _("Request updated."))
        return redirect("cabinet:manager_request_detail", pk=obj.pk)
    return render(
        request,
        "cabinet/manager/request_detail.html",
        {"obj": obj, "form": form, "full": form_class is RequestFullForm, "page_title": obj.name},
    )


@role_required(R.MANAGER)
@require_POST
def request_status(request, pk):
    """Быстрая смена статуса прямо из списка."""
    obj = get_object_or_404(EnrollmentRequest, pk=pk)
    status = request.POST.get("status")
    if status in S.values:
        obj.status = status
        obj.handled_by = request.user
        obj.save(update_fields=["status", "handled_by", "updated_at"])
        messages.success(request, _("Status changed: %(status)s.") % {"status": obj.get_status_display()})
    back = request.POST.get("next", "")
    return redirect(back if back.startswith("/cabinet/") else "cabinet:manager_requests")


@role_required(R.MANAGER)
@require_POST
def request_delete(request, pk):
    obj = get_object_or_404(EnrollmentRequest, pk=pk)
    obj.delete()
    messages.success(request, _("Request deleted."))
    return redirect("cabinet:manager_requests")


@role_required(R.MANAGER)
def request_to_student(request, pk):
    """Создание аккаунта студента на основе заявки."""
    obj = get_object_or_404(EnrollmentRequest.objects.select_related("course"), pk=pk)
    if obj.student_id:
        messages.info(request, _("A student account has already been created for this request."))
        return redirect("cabinet:manager_student_edit", pk=obj.student_id)
    first, last = split_full_name(obj.name)
    initial = {
        "first_name": first,
        "last_name": last,
        "username": generate_username(first, last),
        "phone": obj.phone,
        "email": obj.email,
        "is_active": True,
    }
    if obj.course_id:
        initial["groups_field"] = list(
            Group.objects.filter(course_id=obj.course_id, is_active=True).values_list("pk", flat=True)[:1]
        )
    form = StudentForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        student = form.save()
        obj.student = student
        obj.status = S.ENROLLED
        obj.handled_by = request.user
        obj.save(update_fields=["student", "status", "handled_by", "updated_at"])
        if form.generated_password:
            _credentials_message(request, student, form.generated_password)
        else:
            messages.success(request, _("Student created."))
        return redirect("cabinet:manager_students")
    return render(
        request,
        "cabinet/manager/student_form.html",
        {"form": form, "from_request": obj, "page_title": _("Student from request")},
    )


# ---------------------------------------------------------------------------
# Студенты
# ---------------------------------------------------------------------------
@role_required(R.MANAGER)
def student_list(request):
    qs = User.objects.filter(role=R.STUDENT).prefetch_related("study_groups__course")
    q = request.GET.get("q", "").strip()
    group = request.GET.get("group", "")
    state = request.GET.get("state", "")
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q)
            | Q(phone__icontains=q) | Q(email__icontains=q)
        )
    if group.isdigit():
        qs = qs.filter(study_groups=group)
    if state == "inactive":
        qs = qs.filter(is_active=False)
    elif state == "nogroup":
        qs = qs.filter(study_groups__isnull=True)
    return render(
        request,
        "cabinet/manager/student_list.html",
        {
            "page_obj": paginate(request, qs.distinct(), 25),
            "groups": Group.objects.filter(is_active=True),
            "q": q,
            "group_filter": group,
            "state": state,
            "page_title": _("Students"),
        },
    )


@role_required(R.MANAGER)
def student_create(request):
    form = StudentForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        student = form.save()
        if form.generated_password:
            _credentials_message(request, student, form.generated_password)
        else:
            messages.success(request, _("Student created."))
        return redirect("cabinet:manager_students")
    return render(request, "cabinet/manager/student_form.html", {"form": form, "page_title": _("New student")})


@role_required(R.MANAGER)
def student_edit(request, pk):
    student = get_object_or_404(User, pk=pk, role=R.STUDENT)
    form = StudentForm(request.POST or None, request.FILES or None, instance=student)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Student saved."))
        return redirect("cabinet:manager_students")
    return render(
        request,
        "cabinet/manager/student_form.html",
        {"form": form, "student": student, "page_title": student.display_name},
    )


# ---------------------------------------------------------------------------
# Группы
# ---------------------------------------------------------------------------
@role_required(R.MANAGER)
def group_list(request):
    qs = Group.objects.select_related("course", "teacher")
    show = request.GET.get("show", "active")
    if show == "active":
        qs = qs.filter(is_active=True)
    elif show == "archive":
        qs = qs.filter(is_active=False)
    return render(
        request,
        "cabinet/manager/group_list.html",
        {"groups": with_month_percent(qs), "show": show, "page_title": _("Groups")},
    )


def _group_form(request, group=None):
    form = GroupForm(request.POST or None, instance=group)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, _("Group saved."))
        return redirect("cabinet:manager_group_detail", pk=saved.pk)
    return render(
        request,
        "cabinet/manager/group_form.html",
        {"form": form, "group": group, "page_title": group.name if group else _("New group")},
    )


@role_required(R.MANAGER)
def group_create(request):
    return _group_form(request)


@role_required(R.MANAGER)
def group_edit(request, pk):
    return _group_form(request, get_object_or_404(Group, pk=pk))


@role_required(R.MANAGER)
def group_detail(request, pk):
    group = get_object_or_404(Group.objects.select_related("course", "teacher"), pk=pk)
    return render(
        request,
        "cabinet/manager/group_detail.html",
        {
            "group": with_month_percent([group])[0],
            "students": group.students.order_by("last_name", "first_name"),
            "lessons": group.course.lessons.filter(Q(group=group) | Q(group__isnull=True)).select_related("teacher")[:8],
            "page_title": group.name,
        },
    )


@role_required(R.MANAGER)
@require_POST
def group_delete(request, pk):
    group = get_object_or_404(Group, pk=pk)
    if group.attendance.exists():
        group.is_active = False
        group.save(update_fields=["is_active"])
        messages.info(request, _("The group has attendance records, so it was moved to the archive instead."))
    else:
        group.delete()
        messages.success(request, _("Group deleted."))
    return redirect("cabinet:manager_groups")


# ---------------------------------------------------------------------------
# Новости
# ---------------------------------------------------------------------------
@role_required(R.MANAGER)
def news_list(request):
    return render(
        request,
        "cabinet/manager/news_list.html",
        {"page_obj": paginate(request, News.objects.select_related("author"), 15), "page_title": _("News")},
    )


def _news_form(request, item=None):
    form = NewsForm(request.POST or None, request.FILES or None, instance=item)
    if request.method == "POST" and form.is_valid():
        news = form.save(commit=False)
        if not news.author_id:
            news.author = request.user
        news.save()
        messages.success(request, _("News saved."))
        return redirect("cabinet:manager_news")
    return render(
        request,
        "cabinet/manager/news_form.html",
        {"form": form, "item": item, "page_title": _("Edit news") if item else _("New news item")},
    )


@role_required(R.MANAGER)
def news_create(request):
    return _news_form(request)


@role_required(R.MANAGER)
def news_edit(request, pk):
    return _news_form(request, get_object_or_404(News, pk=pk))


@role_required(R.MANAGER)
@require_POST
def news_delete(request, pk):
    item = get_object_or_404(News, pk=pk)
    if item.image:
        item.image.delete(save=False)
    item.delete()
    messages.success(request, _("News deleted."))
    return redirect("cabinet:manager_news")


# ---------------------------------------------------------------------------
# Журналы (только чтение)
# ---------------------------------------------------------------------------
@role_required(R.MANAGER)
def journals(request):
    return render(
        request,
        "cabinet/shared/journal_groups.html",
        {
            "groups": with_month_percent(groups_for(request.user).filter(is_active=True)),
            "page_title": _("Attendance journals"),
            "read_only": not request.user.is_admin_role,
        },
    )
