from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "get_full_name", "role", "phone", "email", "is_active", "last_login")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email", "phone")
    fieldsets = BaseUserAdmin.fieldsets + (
        (_("Learning center profile"), {"fields": ("role", "phone", "photo", "specialization", "about")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_("Learning center profile"), {"fields": ("role", "first_name", "last_name", "phone")}),
    )
