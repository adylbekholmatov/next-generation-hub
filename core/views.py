from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import EnrollmentForm
from .models import Course, Direction, Group, News, directions

User = get_user_model()


def _teachers():
    return (
        User.objects.filter(role=User.Role.TEACHER, is_active=True)
        .prefetch_related("courses_taught")
        .order_by("last_name", "first_name")
    )


def home(request):
    courses = Course.objects.filter(is_active=True).prefetch_related("teachers")
    stats = {
        "students": User.objects.filter(role=User.Role.STUDENT, is_active=True).count(),
        "teachers": User.objects.filter(role=User.Role.TEACHER, is_active=True).count(),
        "groups": Group.objects.filter(is_active=True).count(),
        "courses": courses.count(),
    }
    return render(
        request,
        "core/home.html",
        {
            "directions": directions(),
            "courses": courses[:6],
            "teachers": _teachers()[:8],
            "news_list": News.visible().select_related("author")[:3],
            "stats": stats,
            "form": EnrollmentForm(),
        },
    )


def course_list(request):
    direction = request.GET.get("direction", "")
    courses = Course.objects.filter(is_active=True).prefetch_related("teachers")
    if direction in Direction.values:
        courses = courses.filter(direction=direction)
    else:
        direction = ""
    counts = dict(
        Course.objects.filter(is_active=True).values_list("direction").annotate(n=Count("id")).values_list(
            "direction", "n"
        )
    )
    dirs = directions()
    for d in dirs:
        d["count"] = counts.get(d["code"], 0)
    return render(
        request,
        "core/course_list.html",
        {"courses": courses, "directions": dirs, "active_direction": direction},
    )


def course_detail(request, slug):
    course = get_object_or_404(Course.objects.prefetch_related("teachers"), slug=slug, is_active=True)
    form = EnrollmentForm(initial={"course": course})
    related = Course.objects.filter(is_active=True).exclude(pk=course.pk).order_by("?")[:3]
    groups = course.groups.filter(is_active=True).select_related("teacher")
    return render(
        request,
        "core/course_detail.html",
        {"course": course, "form": form, "related": related, "groups": groups},
    )


def news_list(request):
    paginator = Paginator(News.visible().select_related("author"), 9)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "core/news_list.html", {"page_obj": page})


def news_detail(request, pk):
    item = get_object_or_404(News.visible(), pk=pk)
    more = News.visible().exclude(pk=pk)[:3]
    return render(request, "core/news_detail.html", {"item": item, "more": more})


def about(request):
    return render(
        request,
        "core/about.html",
        {"teachers": _teachers(), "directions": directions(), "form": EnrollmentForm()},
    )


def contacts(request):
    return render(request, "core/contacts.html", {"form": EnrollmentForm()})


@require_POST
def enroll(request):
    form = EnrollmentForm(request.POST)
    back = request.POST.get("next") or "/"
    if not url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()}):
        back = "/"
    if form.is_valid():
        form.save()
        request.session["enroll_name"] = form.cleaned_data["name"]
        return redirect("core:enroll_success")
    if "website" in form.errors:
        # Бот заполнил ловушку — делаем вид, что всё прошло успешно.
        return redirect("core:enroll_success")
    return render(request, "core/enroll_error.html", {"form": form, "back": back}, status=400)


def enroll_success(request):
    name = request.session.pop("enroll_name", "")
    return render(request, "core/enroll_success.html", {"name": name})


def error_403(request, exception=None):
    return render(request, "403.html", status=403)


def error_404(request, exception=None):
    return render(request, "404.html", status=404)



def health(request):
    """Техническая проверка для хостинга: тип базы без адресов и паролей."""
    return JsonResponse({
        "status": "ok",
        "database": connection.vendor,
        "demo_database": settings.USING_DEMO_DATABASE,
        "courses": Course.objects.count(),
    })
