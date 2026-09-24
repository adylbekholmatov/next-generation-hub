from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", _("Administrator")
        MANAGER = "manager", _("Manager")
        TEACHER = "teacher", _("Teacher")
        STUDENT = "student", _("Student")

    role = models.CharField(_("role"), max_length=16, choices=Role.choices, default=Role.STUDENT, db_index=True)
    phone = models.CharField(_("phone"), max_length=32, blank=True)
    photo = models.ImageField(_("photo"), upload_to="users/", blank=True)
    specialization = models.CharField(_("specialization"), max_length=160, blank=True)
    about = models.TextField(_("about"), blank=True)

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["last_name", "first_name", "username"]

    def save(self, *args, **kwargs):
        # Суперпользователь, созданный через createsuperuser, сразу получает роль администратора.
        if self.is_superuser and self.role != self.Role.ADMIN:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def initials(self):
        parts = [p for p in (self.first_name, self.last_name) if p]
        if parts:
            return "".join(p[0] for p in parts).upper()[:2]
        return self.username[:2].upper()

    # Удобные проверки ролей. Администратор (и суперпользователь) имеет доступ ко всему.
    @property
    def is_admin_role(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    def has_role(self, *roles):
        return self.is_admin_role or self.role in roles
