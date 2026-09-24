"""Точка входа для Vercel: WSGI-приложение Django."""
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

try:
    from config.wsgi import application
except Exception as exc:  # noqa: BLE001
    # Если Django не стартовал, отдаём короткую причину (полный traceback — в логах Vercel),
    # вместо безликого FUNCTION_INVOCATION_FAILED.
    traceback.print_exc()
    _startup_error = f"{type(exc).__name__}: {exc}"

    def application(environ, start_response):
        start_response("500 Internal Server Error", [("Content-Type", "text/plain; charset=utf-8")])
        return [f"Next-Generation-Hub failed to start.\n{_startup_error}\n".encode()]

app = application
