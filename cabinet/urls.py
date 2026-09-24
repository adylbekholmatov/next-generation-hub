from django.urls import path

from .views import admin, common, manager, student, teacher

app_name = "cabinet"

urlpatterns = [
    path("", common.home, name="home"),
    path("lessons/<int:pk>/", common.lesson_detail, name="lesson_detail"),
    path("journal/<int:pk>/", common.journal_month, name="journal_month"),
    path("journal/<int:pk>/export.<str:fmt>", common.journal_export, name="journal_export"),
    # Админ-панель
    path("admin/", admin.dashboard, name="admin_dashboard"),
    path("admin/users/", admin.user_list, name="admin_users"),
    path("admin/users/new/", admin.user_create, name="admin_user_create"),
    path("admin/users/<int:pk>/", admin.user_edit, name="admin_user_edit"),
    path("admin/users/<int:pk>/password/", admin.user_password, name="admin_user_password"),
    path("admin/users/<int:pk>/toggle/", admin.user_toggle, name="admin_user_toggle"),
    path("admin/courses/", admin.course_list, name="admin_courses"),
    path("admin/courses/new/", admin.course_create, name="admin_course_create"),
    path("admin/courses/<int:pk>/", admin.course_edit, name="admin_course_edit"),
    path("admin/courses/<int:pk>/delete/", admin.course_delete, name="admin_course_delete"),
    # Менеджер
    path("manager/", manager.dashboard, name="manager_dashboard"),
    path("manager/requests/", manager.request_list, name="manager_requests"),
    path("manager/requests/<int:pk>/", manager.request_detail, name="manager_request_detail"),
    path("manager/requests/<int:pk>/status/", manager.request_status, name="manager_request_status"),
    path("manager/requests/<int:pk>/student/", manager.request_to_student, name="manager_request_to_student"),
    path("manager/requests/<int:pk>/delete/", manager.request_delete, name="manager_request_delete"),
    path("manager/students/", manager.student_list, name="manager_students"),
    path("manager/students/new/", manager.student_create, name="manager_student_create"),
    path("manager/students/<int:pk>/", manager.student_edit, name="manager_student_edit"),
    path("manager/groups/", manager.group_list, name="manager_groups"),
    path("manager/groups/new/", manager.group_create, name="manager_group_create"),
    path("manager/groups/<int:pk>/", manager.group_detail, name="manager_group_detail"),
    path("manager/groups/<int:pk>/edit/", manager.group_edit, name="manager_group_edit"),
    path("manager/groups/<int:pk>/delete/", manager.group_delete, name="manager_group_delete"),
    path("manager/news/", manager.news_list, name="manager_news"),
    path("manager/news/new/", manager.news_create, name="manager_news_create"),
    path("manager/news/<int:pk>/", manager.news_edit, name="manager_news_edit"),
    path("manager/news/<int:pk>/delete/", manager.news_delete, name="manager_news_delete"),
    path("manager/journals/", manager.journals, name="manager_journals"),
    # Учитель
    path("teacher/", teacher.dashboard, name="teacher_dashboard"),
    path("teacher/lessons/", teacher.lesson_list, name="teacher_lessons"),
    path("teacher/lessons/new/", teacher.lesson_create, name="teacher_lesson_create"),
    path("teacher/lessons/<int:pk>/", teacher.lesson_edit, name="teacher_lesson_edit"),
    path("teacher/lessons/<int:pk>/delete/", teacher.lesson_delete, name="teacher_lesson_delete"),
    path("teacher/attendance/", teacher.mark_attendance, name="teacher_mark"),
    path("teacher/journal/", teacher.journal, name="teacher_journal"),
    # Студент
    path("student/", student.dashboard, name="student_dashboard"),
    path("student/lessons/", student.lessons, name="student_lessons"),
    path("student/attendance/", student.attendance, name="student_attendance"),
]
