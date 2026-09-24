from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CabinetConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cabinet"
    verbose_name = _("Cabinets")
