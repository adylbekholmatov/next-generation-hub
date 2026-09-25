"""Точка входа для Vercel: WSGI-приложение Django."""
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

try:
    from config.wsgi import application
    from django.conf import settings

    if settings.AUTO_MIGRATE:
        # Внешняя база (Neon): при первом запуске создаём таблицы и демо-данные.
        from core.bootstrap import ensure_database

        ensure_database()
except Exception as exc:  # noqa: BLE001
    # Если Django не стартовал, отдаём короткую причину (полный traceback — в логах Vercel),
    # вместо безликого FUNCTION_INVOCATION_FAILED.
    traceback.print_exc()
    _startup_error = f"{type(exc).__name__}: {exc}"
    # Только имена переменных (без значений) — чтобы понять, дошли ли настройки до функции.
    _names = sorted(k for k in os.environ if any(w in k for w in ("DJANGO", "SECRET", "DATABASE", "POSTGRES")))
    _startup_error += (
        f"\nVERCEL_ENV={os.environ.get('VERCEL_ENV')}; env names: {_names or '-'}; "
        f"DJANGO_SECRET_KEY length: {len(os.environ.get('DJANGO_SECRET_KEY', ''))}"
    )

    def application(environ, start_response):
        start_response("500 Internal Server Error", [("Content-Type", "text/plain; charset=utf-8")])
        return [f"Next-Generation-Hub failed to start.\n{_startup_error}\n".encode()]

app = application
