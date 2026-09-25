from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("courses/", views.course_list, name="course_list"),
    path("courses/<slug:slug>/", views.course_detail, name="course_detail"),
    path("news/", views.news_list, name="news_list"),
    path("news/<int:pk>/", views.news_detail, name="news_detail"),
    path("about/", views.about, name="about"),
    path("contacts/", views.contacts, name="contacts"),
    path("enroll/", views.enroll, name="enroll"),
    path("enroll/success/", views.enroll_success, name="enroll_success"),
    path("health/", views.health, name="health"),
]
