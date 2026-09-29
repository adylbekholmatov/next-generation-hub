"""Подготовка базы при старте сервера (для хостингов без консоли, например Vercel).

1. Применяет недостающие миграции.
2. Если в базе ещё нет ни одного пользователя, заполняет её демо-данными (`seed`).

Параллельные холодные старты не мешают друг другу: в PostgreSQL работа идёт под
advisory lock, поэтому миграции выполнит только один экземпляр, остальные подождут.
"""
import io
import os
import logging

from django.core.management import call_command
from django.db import ProgrammingError, connection
from django.db.migrations.executor import MigrationExecutor

logger = logging.getLogger(__name__)

LOCK_ID = 7_406_251_901  # произвольный номер блокировки проекта


def _pending_migrations():
    executor = MigrationExecutor(connection)
    return executor.migration_plan(executor.loader.graph.leaf_nodes())


def reset_admin_password():
    """Восстановление доступа без консоли: переменная окружения DJANGO_ADMIN_PASSWORD.

    Если она задана, аккаунт администратора (логин из DJANGO_ADMIN_USERNAME, по умолчанию
    admin) создаётся или получает этот пароль, роль администратора и снимается блокировка.
    После входа переменную нужно удалить из настроек хостинга.
    """
    password = os.environ.get("DJANGO_ADMIN_PASSWORD", "").strip()
    if not password:
        return
    from django.contrib.auth import get_user_model

    User = get_user_model()
    username = os.environ.get("DJANGO_ADMIN_USERNAME", "").strip() or "admin"
    user = User.objects.filter(username=username).first() or User(username=username)
    if user.pk and user.is_active and user.is_superuser and user.check_password(password):
        return  # уже восстановлен
    user.role = User.Role.ADMIN
    user.is_active = user.is_staff = user.is_superuser = True
    user.set_password(password)
    user.save()
    logger.warning("Administrator account %r restored from DJANGO_ADMIN_PASSWORD.", username)


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

        reset_admin_password()
    finally:
        if use_lock:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [LOCK_ID])
        connection.close()
