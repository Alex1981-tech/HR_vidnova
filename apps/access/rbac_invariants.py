"""RBAC инварианты (Этап 2): нельзя оставить систему без администратора.

Сервис-уровень: вызывается из API/команд/seed перед деактивацией/удалением
admin-назначений. Не подменяет, а дополняет защиту system-роли от удаления.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db.models import Q

from apps.access.role_seeds import ADMIN_ROLE_SLUG


def active_admin_assignments(exclude_pk: int | None = None):
    """Активные назначения admin-роли (опц. без одного pk — кандидата на снятие)."""
    from apps.access.models import AccessRoleAssignment

    qs = AccessRoleAssignment.objects.filter(
        role__slug=ADMIN_ROLE_SLUG, role__is_active=True, is_active=True
    ).filter(Q(user__isnull=False) | Q(employee__isnull=False))
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs


def would_remove_last_admin(assignment) -> bool:
    """True, если снятие/деактивация этого assignment оставит 0 активных админов."""
    if assignment.role.slug != ADMIN_ROLE_SLUG:
        return False
    return not active_admin_assignments(exclude_pk=assignment.pk).exists()


def assert_admin_remains(assignment) -> None:
    """Бросает ValidationError, если действие оставит систему без администратора."""
    if would_remove_last_admin(assignment):
        raise ValidationError("Не можна зняти останнього адміністратора системи.")
