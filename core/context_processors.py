from django.conf import settings
from django.utils.translation import gettext as _


def site(request):
    return {
        "SITE": {
            "name": settings.SITE_NAME,
            "phone": settings.SITE_PHONE,
            "phone_href": "tel:" + "".join(ch for ch in settings.SITE_PHONE if ch.isdigit() or ch == "+"),
            "email": settings.SITE_EMAIL,
            "address": settings.SITE_ADDRESS or _("Bishkek, Chui Avenue 155, 3rd floor"),
            "hours": settings.SITE_HOURS or _("Mon–Sat, 9:00–20:00"),
            "instagram": settings.SITE_INSTAGRAM,
            "telegram": settings.SITE_TELEGRAM,
            "whatsapp": settings.SITE_WHATSAPP,
            "map_url": settings.SITE_MAP_URL,
        },
        "MAX_VIDEO_UPLOAD_MB": settings.MAX_VIDEO_UPLOAD_MB,
    }
