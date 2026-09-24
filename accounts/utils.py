import re
import secrets
import string

from django.contrib.auth import get_user_model

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z",
    "и": "i", "й": "i", "к": "k", "л": "l", "м": "m", "н": "n", "ң": "ng", "о": "o", "ө": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ү": "u", "ф": "f", "х": "h", "ц": "ts",
    "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def transliterate(text):
    return "".join(TRANSLIT.get(ch, ch) for ch in text.lower())


def generate_username(first_name="", last_name="", fallback="student"):
    """Логин из имени и фамилии латиницей: aibek.asanov, aibek.asanov2 …"""
    base = ".".join(p for p in (transliterate(first_name), transliterate(last_name)) if p)
    base = re.sub(r"[^a-z0-9.]", "", base).strip(".")[:30] or fallback
    User = get_user_model()
    candidate, n = base, 1
    while User.objects.filter(username=candidate).exists():
        n += 1
        candidate = f"{base}{n}"
    return candidate


def generate_password(length=10):
    alphabet = string.ascii_letters + string.digits
    alphabet = "".join(ch for ch in alphabet if ch not in "0O1lI")
    return "".join(secrets.choice(alphabet) for _ in range(length))


def split_full_name(full_name):
    parts = (full_name or "").split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])
