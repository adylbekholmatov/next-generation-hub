from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from core.icons import svg
from core.models import Attendance

register = template.Library()


@register.filter
def tr(obj, field):
    """{{ course|tr:"title" }} — значение на текущем языке, иначе на русском."""
    if obj is None:
        return ""
    return obj.tr(field)


@register.simple_tag
def icon(name, size=20, cls="", label=""):
    return mark_safe(svg(name, size, escape(cls), escape(label)))


@register.filter
def get_item(mapping, key):
    if mapping is None:
        return None
    try:
        return mapping.get(key)
    except AttributeError:
        return None


@register.simple_tag(takes_context=True)
def query(context, **kwargs):
    """Собирает querystring из текущего GET, заменяя переданные параметры."""
    request = context.get("request")
    params = request.GET.copy() if request else {}
    for key, value in kwargs.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = value
    encoded = params.urlencode()
    return f"?{encoded}" if encoded else "?"


STATUS_SYMBOL = {
    Attendance.Status.PRESENT: "●",
    Attendance.Status.LATE: "◐",
    Attendance.Status.ABSENT: "○",
    Attendance.Status.EXCUSED: "◇",
}


@register.filter
def status_symbol(status):
    return STATUS_SYMBOL.get(status, "·")


@register.filter
def percent_level(value):
    """Цветовой уровень для процента посещаемости."""
    if value is None:
        return "none"
    if value >= 85:
        return "good"
    if value >= 65:
        return "mid"
    return "low"


@register.filter
def field_type(bound_field):
    return bound_field.field.widget.__class__.__name__.lower()


@register.filter
def startswith(value, prefix):
    return str(value).startswith(str(prefix))


@register.filter
def intcomma_space(value):
    """4500 → «4 500» (неразрывный пробел между разрядами)."""
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return value


@register.filter
def filesize(value):
    try:
        size = float(value)
    except (TypeError, ValueError):
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
