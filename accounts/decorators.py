"""Проверка ролей: декоратор для функций и миксин для классов.

Неавторизованный пользователь отправляется на страницу входа,
авторизованный пользователь с чужой ролью получает 403.
Администратор проходит любую проверку.
"""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not user.has_role(*roles):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        wrapper.required_roles = roles
        return wrapper

    return decorator


class RoleRequiredMixin:
    required_roles: tuple = ()

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not user.has_role(*self.required_roles):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
