from django.conf import settings
from django.utils.translation import get_language
from django.utils.translation import gettext as _


def site(request):
    return {
        "SITE": {
            "name": settings.SITE_NAME,
            "phone": settings.SITE_PHONE,
            "phone_href": "tel:" + "".join(ch for ch in settings.SITE_PHONE if ch.isdigit() or ch == "+"),
            "email": settings.SITE_EMAIL,
            "address": settings.SITE_ADDRESS or _("Osh, Gapar Aitiev street 14a"),
            "hours": settings.SITE_HOURS or _("Mon–Sat, 9:00–20:00"),
            "instagram": settings.SITE_INSTAGRAM,
            "telegram": settings.SITE_TELEGRAM,
            "whatsapp": settings.SITE_WHATSAPP,
            "map_url": settings.SITE_MAP_URL,
            # Google Maps не знает кыргызский интерфейс — для ky показываем русский.
            "map_embed": (
                f"https://maps.google.com/maps?q={settings.SITE_MAP_LAT},{settings.SITE_MAP_LON}"
                f"&z=17&hl={'en' if get_language() == 'en' else 'ru'}&output=embed"
            ),
        },
        "MAX_VIDEO_UPLOAD_MB": settings.MAX_VIDEO_UPLOAD_MB,
        "SHOW_DEMO_ACCOUNTS": settings.SHOW_DEMO_ACCOUNTS,
    }
