"""
Next-Generation-Hub — настройки проекта.

Все чувствительные и зависящие от окружения значения берутся из переменных
окружения. Для удобства локальной разработки поддерживается файл `.env`
в корне проекта (простой формат KEY=VALUE, без сторонних библиотек).
"""
import os
import shutil
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from django.core.exceptions import ImproperlyConfigured


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
    # Пустая переменная (например, созданная хостингом без значения) считается незаданной.
    value = os.environ.get(name, "").strip()
    return value if value else default


def env_bool(name, default=False):
    value = env(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name, default=""):
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


# Vercel выставляет VERCEL=1. Там сайт работает как serverless-функция в демо-режиме:
# база копируется в /tmp, сессии хранятся в подписанных cookie (см. README → Vercel).
ON_VERCEL = bool(os.environ.get("VERCEL"))

# --- Безопасность -----------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-key-change-me-in-production-0123456789")
if ON_VERCEL and not env("DJANGO_SECRET_KEY"):
    # Репозиторий публичный: с известным ключом можно подделать cookie-сессию администратора.
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY in the Vercel project environment variables.")
# На Vercel сайт публичный: режим отладки там не включается никогда.
DEBUG = False if ON_VERCEL else env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1],testserver")
if ON_VERCEL:
    ALLOWED_HOSTS.append(".vercel.app")
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
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
# Порядок выбора:
# 1. строка подключения DATABASE_URL (её сам добавляет Vercel при подключении Neon);
# 2. DB_ENGINE=postgres и DB_* (см. README);
# 3. SQLite (на Vercel без внешней базы — временная демо-копия в /tmp).
# Прямое (не pooled) подключение предпочтительнее: миграции используют блокировки сессии.
DATABASE_URL_KEYS = ("DATABASE_URL_UNPOOLED", "POSTGRES_URL_NON_POOLING", "DATABASE_URL", "POSTGRES_URL")


def _find_database_url():
    for key in DATABASE_URL_KEYS:
        if env(key):
            return env(key)
    # Vercel Storage может добавить префикс к именам: STORAGE_DATABASE_URL и т. п.
    for suffix in DATABASE_URL_KEYS:
        for key in sorted(os.environ):
            if key.endswith("_" + suffix) and env(key):
                return env(key)
    # Любой другой префикс (STORAGE_URL, NEON_URL…): ищем строку подключения PostgreSQL по значению,
    # прямое подключение (UNPOOLED / NON_POOLING) в приоритете.
    candidates = sorted(
        (key for key in os.environ if (env(key) or "").startswith(("postgres://", "postgresql://"))),
        key=lambda k: (not any(mark in k for mark in ("UNPOOLED", "NON_POOLING")), k),
    )
    return env(candidates[0]) if candidates else None


def _database_from_url(url):
    parsed = urlparse(url)
    if parsed.scheme in {"postgres", "postgresql"}:
        options = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        options.setdefault("sslmode", "prefer" if parsed.hostname in {"localhost", "127.0.0.1"} else "require")
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": unquote(parsed.path.lstrip("/")),
            "USER": unquote(parsed.username or ""),
            "PASSWORD": unquote(parsed.password or ""),
            "HOST": parsed.hostname or "",
            "PORT": str(parsed.port or 5432),
            "OPTIONS": options,
            # Serverless: соединение не держим между запросами.
            "CONN_MAX_AGE": 0 if ON_VERCEL else 60,
            # Через пулер (PgBouncer) серверные курсоры не работают.
            "DISABLE_SERVER_SIDE_CURSORS": "pooler" in (parsed.hostname or ""),
        }
    if parsed.scheme == "sqlite":
        path = unquote(parsed.path)
        if len(path) > 2 and path[0] == "/" and path[2] == ":":  # /C:/... на Windows
            path = path[1:]
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": path}
    raise ImproperlyConfigured(f"Unsupported database URL scheme: {parsed.scheme}")


DATABASE_URL = _find_database_url()
if DATABASE_URL:
    DATABASES = {"default": _database_from_url(DATABASE_URL)}
elif env("DB_ENGINE", "sqlite").lower() in {"postgres", "postgresql"}:
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
    SQLITE_PATH = Path(env("SQLITE_PATH", BASE_DIR / "db.sqlite3"))
    if ON_VERCEL and not env("SQLITE_PATH"):
        # На Vercel писать можно только в /tmp: копируем туда готовую демо-базу.
        SQLITE_PATH = Path("/tmp/ngh-demo.sqlite3")
        if not SQLITE_PATH.exists():
            shutil.copyfile(BASE_DIR / "deploy" / "demo.sqlite3", SQLITE_PATH)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": SQLITE_PATH,
        }
    }

# Временная демо-база: на Vercel без внешней БД (изменения сбрасываются).
USING_DEMO_DATABASE = ON_VERCEL and DATABASES["default"]["ENGINE"].endswith("sqlite3")
# Автоматически применять миграции и заполнять пустую базу демо-данными при старте
# (нужно на Vercel, где нет доступа к консоли). Выключить: DJANGO_AUTO_MIGRATE=False.
AUTO_MIGRATE = env_bool("DJANGO_AUTO_MIGRATE", ON_VERCEL and not USING_DEMO_DATABASE)

if ON_VERCEL:
    # Serverless: сессии в подписанных cookie, чтобы не зависеть от экземпляра функции.
    SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

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
# На Vercel collectstatic не запускается — статику WhiteNoise берёт из исходных папок.
STATIC_ROOT = None if ON_VERCEL else BASE_DIR / "staticfiles"
# WhiteNoise отдаёт статику прямо из STATICFILES_DIRS и приложений, collectstatic не обязателен.
WHITENOISE_USE_FINDERS = True

MEDIA_URL = "/media/"
MEDIA_ROOT = Path("/tmp/media") if ON_VERCEL else BASE_DIR / "media"
# На Vercel медиа временные и отдаются самим Django (для продакшена — nginx, см. README).
SERVE_MEDIA = DEBUG or ON_VERCEL
# Показывать демо-логины на странице входа.
SHOW_DEMO_ACCOUNTS = env_bool("SHOW_DEMO_ACCOUNTS", DEBUG or ON_VERCEL)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Загрузка видео ---------------------------------------------------------
# Vercel ограничивает тело запроса 4,5 МБ.
MAX_VIDEO_UPLOAD_MB = int(env("MAX_VIDEO_UPLOAD_MB", "4" if ON_VERCEL else "500"))
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
SITE_MAP_URL = env("SITE_MAP_URL", "https://go.2gis.com/fdRkC")  # карточка центра в 2ГИС
# Точка на встроенной карте (Ош, ул. Гапара Айтиева, 14а).
SITE_MAP_LAT = env("SITE_MAP_LAT", "40.524921")
SITE_MAP_LON = env("SITE_MAP_LON", "72.772097")

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
