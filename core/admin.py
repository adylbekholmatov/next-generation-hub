from django.contrib import admin

from .models import Attendance, Course, EnrollmentRequest, Group, Lesson, News


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title_ru", "direction", "level", "price", "duration_months", "is_active", "order")
    list_filter = ("direction", "level", "is_active")
    list_editable = ("is_active", "order")
    search_fields = ("title_ru", "title_ky", "title_en", "slug")
    prepopulated_fields = {"slug": ("title_en",)}
    filter_horizontal = ("teachers",)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "teacher", "weekdays", "start_time", "room", "start_date", "is_active")
    list_filter = ("course", "is_active", "teacher")
    search_fields = ("name",)
    filter_horizontal = ("students",)
    list_select_related = ("course", "teacher")


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "course", "group", "teacher", "is_published", "created_at")
    list_filter = ("course", "is_published")
    search_fields = ("title", "description")
    list_select_related = ("course", "group", "teacher")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("date", "group", "student", "status", "grade", "marked_by")
    list_filter = ("status", "group", "date")
    search_fields = ("student__first_name", "student__last_name", "student__username")
    date_hierarchy = "date"
    list_select_related = ("group", "student", "marked_by")


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title_ru", "is_published", "is_pinned", "published_at", "author")
    list_filter = ("is_published", "is_pinned")
    search_fields = ("title_ru", "title_ky", "title_en")
    date_hierarchy = "published_at"


@admin.register(EnrollmentRequest)
class EnrollmentRequestAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "course", "status", "created_at", "handled_by")
    list_filter = ("status", "course")
    search_fields = ("name", "phone", "email", "message")
    list_select_related = ("course", "handled_by")
