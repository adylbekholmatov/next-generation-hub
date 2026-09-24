"""
Next-Generation-Hub — настройки проекта.

Все чувствительные и зависящие от окружения значения берутся из переменных
окружения. Для удобства локальной разработки поддерживается файл `.env`
в корне проекта (простой формат KEY=VALUE, без сторонних библиотек).
"""
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Минимальный загрузчик .env: не перетирает уже заданные переменные."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")


def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


# --- Безопасность -----------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-key-change-me-in-production-0123456789")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")
INTERNAL_IPS = ["127.0.0.1"]

if not DEBUG:
    SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", True)
    CSRF_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

# --- Приложения -------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "accounts",
    "core",
    "cabinet",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.site",
                "cabinet.navigation.sidebar",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- База данных ------------------------------------------------------------
# По умолчанию SQLite. Для PostgreSQL задайте DB_ENGINE=postgres и DB_* (см. README).
if env("DB_ENGINE", "sqlite").lower() in {"postgres", "postgresql"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME", "nextgenhub"),
            "USER": env("DB_USER", "nextgenhub"),
            "PASSWORD": env("DB_PASSWORD", ""),
            "HOST": env("DB_HOST", "localhost"),
            "PORT": env("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "cabinet:home"
LOGOUT_REDIRECT_URL = "core:home"

# --- Языки и время ----------------------------------------------------------
LANGUAGE_CODE = "ru"
LANGUAGES = [
    ("ky", "Кыргызча"),
    ("ru", "Русский"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
LANGUAGE_COOKIE_NAME = "ngh_language"
LANGUAGE_COOKIE_AGE = 60 * 60 * 24 * 365

TIME_ZONE = "Asia/Bishkek"
USE_I18N = True
USE_TZ = True

# --- Статика и медиа --------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Загрузка видео ---------------------------------------------------------
MAX_VIDEO_UPLOAD_MB = int(env("MAX_VIDEO_UPLOAD_MB", "500"))
VIDEO_EXTENSIONS = ["mp4", "webm", "mov"]
# Файлы крупнее 5 МБ Django пишет во временный файл, а не держит в памяти.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# --- Контакты сайта ---------------------------------------------------------
SITE_NAME = env("SITE_NAME", "Next-Generation-Hub")
SITE_PHONE = env("SITE_PHONE", "+996 555 123 456")
SITE_EMAIL = env("SITE_EMAIL", "hello@nextgenhub.kg")
SITE_ADDRESS = env("SITE_ADDRESS", "")  # если пусто — берётся перевод по умолчанию
SITE_HOURS = env("SITE_HOURS", "")
SITE_INSTAGRAM = env("SITE_INSTAGRAM", "https://instagram.com/nextgenhub.kg")
SITE_TELEGRAM = env("SITE_TELEGRAM", "https://t.me/nextgenhub_kg")
SITE_WHATSAPP = env("SITE_WHATSAPP", "https://wa.me/996555123456")
SITE_MAP_URL = env("SITE_MAP_URL", "https://2gis.kg/bishkek")

# --- Сообщения --------------------------------------------------------------
from django.contrib.messages import constants as message_constants  # noqa: E402

MESSAGE_TAGS = {message_constants.ERROR: "error"}

# --- Логирование ------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "WARNING")},
}
