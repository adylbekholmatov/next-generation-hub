"""Подготовка базы при старте сервера (для хостингов без консоли, например Vercel).

1. Применяет недостающие миграции.
2. Если в базе ещё нет ни одного пользователя, заполняет её демо-данными (`seed`).

Параллельные холодные старты не мешают друг другу: в PostgreSQL работа идёт под
advisory lock, поэтому миграции выполнит только один экземпляр, остальные подождут.
"""
import io
import logging

from django.core.management import call_command
from django.db import ProgrammingError, connection
from django.db.migrations.executor import MigrationExecutor

logger = logging.getLogger(__name__)

LOCK_ID = 7_406_251_901  # произвольный номер блокировки проекта


def _pending_migrations():
    executor = MigrationExecutor(connection)
    return executor.migration_plan(executor.loader.graph.leaf_nodes())


def ensure_database():
    use_lock = connection.vendor == "postgresql"
    try:
        if use_lock:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_lock(%s)", [LOCK_ID])
        if _pending_migrations():
            logger.warning("Applying database migrations…")
            try:
                call_command("migrate", interactive=False, verbosity=1)
            except ProgrammingError as exc:
                if "already exists" not in str(exc):
                    raise
                # Таблицы уже есть, а записи о миграциях нет (прерванный первый запуск):
                # отмечаем начальные миграции выполненными и применяем остальное.
                logger.warning("Tables already exist, retrying with --fake-initial: %s", exc)
                call_command("migrate", interactive=False, fake_initial=True, verbosity=1)

        from django.contrib.auth import get_user_model

        if not get_user_model().objects.exists():
            logger.warning("Empty database: loading demo data…")
            output = io.StringIO()
            call_command("seed", stdout=output)
            logger.warning(output.getvalue())
    finally:
        if use_lock:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [LOCK_ID])
        connection.close()
