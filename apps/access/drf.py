"""DRF enforcement-слой RBAC (Этап 4), flag-gated через settings.RBAC_ENFORCE.

Shadow-режим (RBAC_ENFORCE=False, по умолчанию): would-deny логируется, но доступ
НЕ блокируется и queryset НЕ сужается — поведение API не меняется. Это позволяет
выкатить код и собрать сигнал на реальном трафике до включения deny-режима.

Deny-режим (RBAC_ENFORCE=True): permission class реально возвращает False,
а scoped queryset реально фильтруется (get_object → 404 вне scope).

Использование во viewset:
    class FooViewSet(RBACScopedEmployeeQuerysetMixin, ...):
        permission_classes = [ConfiguredReadOnlyOrAuthenticated, HasRBACPermission]
        rbac_read_perm = "documents.view"
        rbac_write_perm = "documents.manage"   # опционально
        rbac_scope_field = "employee_id"        # или "pk" для Employee-viewset
"""

from __future__ import annotations

import logging

from django.conf import settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.access import rbac

logger = logging.getLogger("apps.access.rbac")


def rbac_enforced() -> bool:
    return bool(getattr(settings, "RBAC_ENFORCE", False))


class HasRBACPermission(BasePermission):
    """Проверяет rbac.has_perm по коду из view (rbac_read_perm/rbac_write_perm)."""

    message = "Недостатньо прав."

    def has_permission(self, request, view):
        read_code = getattr(view, "rbac_read_perm", None)
        write_code = getattr(view, "rbac_write_perm", None)
        code = read_code if request.method in SAFE_METHODS else (write_code or read_code)
        if not code:
            return True
        if rbac.has_perm(request.user, code):
            return True
        if rbac_enforced():
            return False
        logger.warning(
            "rbac.shadow.would_deny perm=%s method=%s path=%s user=%s",
            code, request.method, request.path, getattr(request.user, "id", None),
        )
        return True


def apply_rbac_scope(view, queryset):
    """Сужает queryset до employee-scope (только в deny-режиме)."""
    code = getattr(view, "rbac_read_perm", None)
    if not code or not rbac_enforced():
        return queryset
    user = getattr(getattr(view, "request", None), "user", None)
    ids = rbac.scoped_employee_ids(user, code)
    if ids is None:
        return queryset  # без ограничения (admin / all_company)
    field = getattr(view, "rbac_scope_field", "employee_id")
    lookup = "pk__in" if field in ("pk", "id") else f"{field}__in"
    return queryset.filter(**{lookup: ids})


def assert_employee_in_scope(user, code, employee):
    """Для APIView (без queryset): в deny-режиме запретить доступ к employee вне scope."""
    if not rbac_enforced():
        return
    if rbac.has_perm(user, code, employee=employee):
        return
    raise PermissionDenied("Поза доступним scope.")


class RBACScopedViewSetMixin:
    """Применяет employee-scope через filter_queryset (покрывает list и get_object).

    В shadow-режиме ничего не меняет. Concrete viewset задаёт rbac_read_perm и
    rbac_scope_field ("pk" для Employee-viewset, иначе FK-поле на Employee).
    """

    rbac_read_perm: str | None = None
    rbac_scope_field: str = "employee_id"

    def filter_queryset(self, queryset):
        return apply_rbac_scope(self, super().filter_queryset(queryset))
