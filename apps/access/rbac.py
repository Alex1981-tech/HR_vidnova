"""Permission service + scope engine (RBAC, Этап 3).

Вычисляет эффективные роли/права/scope пользователя. Источники роли:
- системные computed-роли (self/all_people/manager/team_lead/admin) — состав
  определяется графом сотрудников (ManagerAssignment/Team), а не явным assignment;
- явные `AccessRoleAssignment` (активные, в окне дат), со своим scope.

Права наполняются через `AccessRolePermission` (матрица — Этап 0/4). Пока роли
пустые, `get_effective_permissions` вернёт пусто — это нормально, движок готов.

Здесь НЕТ DRF enforcement (Этап 4). Только чистые функции + request-level cache.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.utils import timezone

from apps.access.role_seeds import ADMIN_ROLE_SLUG

# Суперпользователь Django обходит проверки (стандартное поведение). Состав admin
# computed-роли тоже включает суперюзера, пока нет иного решения (Этап 0).
SUPERUSER_IS_ADMIN = True

# Sentinel: scope без ограничения (вся компания).
ALL_COMPANY = object()

# Синтетические scope для computed-ролей.
_COMPUTED_ROLE_SCOPE = {
    "self": "self",
    "all_people": "all_company",
    "manager": "direct_and_indirect_reports",
    "team_lead": "team_members",
    ADMIN_ROLE_SLUG: "all_company",
}


@dataclass(frozen=True)
class EffectiveGrant:
    role_slug: str
    scope_type: str
    scope_payload: dict = field(default_factory=dict)
    is_computed: bool = False


# ── graph helpers ────────────────────────────────────────────────────────────


def _today():
    return timezone.localdate()


def current_direct_report_ids(manager_id: int) -> set[int]:
    from django.db.models import Q

    from apps.employees.models import ManagerAssignment

    today = _today()
    rows = (
        ManagerAssignment.objects.filter(manager_id=manager_id, is_primary=True, valid_from__lte=today)
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today))
        .values_list("employee_id", flat=True)
    )
    return set(rows)


def all_report_ids(manager_id: int) -> set[int]:
    """Прямые + непрямые подчинённые (BFS с защитой от циклов)."""
    result: set[int] = set()
    frontier = {manager_id}
    visited: set[int] = {manager_id}
    while frontier:
        next_frontier: set[int] = set()
        for mid in frontier:
            for rid in current_direct_report_ids(mid):
                if rid not in visited:
                    visited.add(rid)
                    result.add(rid)
                    next_frontier.add(rid)
        frontier = next_frontier
    result.discard(manager_id)
    return result


def team_member_ids(lead_employee_id: int) -> set[int]:
    from apps.employees.models import TeamMembership

    rows = TeamMembership.objects.filter(
        team__lead_id=lead_employee_id, team__is_active=True, is_active=True
    ).values_list("employee_id", flat=True)
    return set(rows)


# ── role / permission resolution ─────────────────────────────────────────────


def _subject_employee(user):
    return getattr(user, "employee_profile", None)


def _explicit_admin(user) -> bool:
    from apps.access.models import AccessRoleAssignment

    today = _today()
    from django.db.models import Q

    qs = AccessRoleAssignment.objects.filter(
        role__slug=ADMIN_ROLE_SLUG, role__is_active=True, is_active=True
    ).filter(Q(user=user) | Q(employee=getattr(user, "employee_profile", None)))
    qs = qs.filter(Q(valid_from__isnull=True) | Q(valid_from__lte=today)).filter(
        Q(valid_to__isnull=True) | Q(valid_to__gte=today)
    )
    return qs.exists()


def get_effective_grants(user) -> list[EffectiveGrant]:
    """Список (роль, scope), который реально есть у пользователя."""
    if user is None or not getattr(user, "is_authenticated", False):
        return []

    grants: list[EffectiveGrant] = []
    seen_computed: set[str] = set()

    def add_computed(slug):
        if slug not in seen_computed:
            seen_computed.add(slug)
            grants.append(EffectiveGrant(slug, _COMPUTED_ROLE_SCOPE[slug], {}, is_computed=True))

    emp = _subject_employee(user)
    is_admin = _explicit_admin(user) or (SUPERUSER_IS_ADMIN and getattr(user, "is_superuser", False))
    if is_admin:
        add_computed(ADMIN_ROLE_SLUG)

    if emp is not None:
        from apps.employees.models import Employee

        add_computed("self")
        if emp.status == Employee.Status.ACTIVE:
            add_computed("all_people")
        if current_direct_report_ids(emp.id):
            add_computed("manager")
        if team_member_ids(emp.id):
            add_computed("team_lead")

    # Явные assignment (не computed-роли).
    from django.db.models import Q

    from apps.access.models import AccessRoleAssignment

    today = _today()
    explicit = (
        AccessRoleAssignment.objects.filter(role__is_active=True, is_active=True)
        .filter(Q(user=user) | (Q(employee=emp) if emp is not None else Q(pk__in=[])))
        .filter(Q(valid_from__isnull=True) | Q(valid_from__lte=today))
        .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today))
        .select_related("role")
    )
    for assignment in explicit:
        if assignment.role.slug in seen_computed:
            continue
        grants.append(
            EffectiveGrant(
                assignment.role.slug,
                assignment.scope_type,
                dict(assignment.scope_payload or {}),
                is_computed=False,
            )
        )
    return grants


def _role_permissions(slug: str) -> dict[str, str]:
    """code -> level ('' для atomic) для активной роли."""
    from apps.access.models import AccessRole

    role = AccessRole.objects.filter(slug=slug, is_active=True).first()
    if role is None:
        return {}
    return {p.permission_code: p.level for p in role.permissions.all()}


def get_effective_roles(user) -> set[str]:
    return {grant.role_slug for grant in get_effective_grants(user)}


def get_effective_permissions(user) -> dict[str, set[str]]:
    """code -> множество уровней. 'edit' подразумевает 'view'."""
    perms: dict[str, set[str]] = {}
    for grant in get_effective_grants(user):
        for code, level in _role_permissions(grant.role_slug).items():
            bucket = perms.setdefault(code, set())
            if level:
                bucket.add(level)
                if level == "edit":
                    bucket.add("view")
            else:
                bucket.add("")
    return perms


def _cached_grants(user):
    cache = getattr(user, "_rbac_grants_cache", None)
    if cache is None:
        cache = get_effective_grants(user)
        try:
            user._rbac_grants_cache = cache
        except (AttributeError, TypeError):
            pass
    return cache


def _grant_scope(grant: EffectiveGrant, subject_emp):
    """Множество employee id для grant, либо ALL_COMPANY."""
    scope = grant.scope_type
    if scope == "all_company":
        return ALL_COMPANY
    if scope == "self":
        return {subject_emp.id} if subject_emp is not None else set()
    if scope == "direct_reports":
        return current_direct_report_ids(subject_emp.id) if subject_emp else set()
    if scope == "direct_and_indirect_reports":
        return all_report_ids(subject_emp.id) if subject_emp else set()
    if scope == "team_members":
        return team_member_ids(subject_emp.id) if subject_emp else set()
    if scope == "explicit_employees":
        return set(grant.scope_payload.get("employee_ids", []))
    if scope in {"department", "clinic", "division"}:
        return _org_scope_ids(scope, grant, subject_emp)
    # custom_conditions и неизвестные — пока пусто (реализация позже).
    return set()


def _org_scope_ids(scope, grant, subject_emp):
    from apps.employees.models import Employee

    key = f"{scope}_id"
    target = grant.scope_payload.get(key)
    if target is None and subject_emp is not None:
        target = getattr(subject_emp, key, None)
    if target is None:
        return set()
    return set(
        Employee.objects.filter(**{key: target}).values_list("id", flat=True)
    )


def has_perm(user, code: str, level: str | None = None, employee=None) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    perms = get_effective_permissions(user)
    levels = perms.get(code)
    if levels is None:
        return False
    if level is not None and level not in levels:
        return False
    if employee is not None:
        return employee_scope_queryset(user, code).filter(pk=employee.pk).exists()
    return True


def employee_scope_queryset(user, code: str, base_qs=None):
    """Employee queryset, доступный пользователю по праву `code`."""
    from apps.employees.models import Employee

    base = base_qs if base_qs is not None else Employee.objects.all()
    if user is None or not getattr(user, "is_authenticated", False):
        return base.none()
    if getattr(user, "is_superuser", False):
        return base

    subject = _subject_employee(user)
    ids: set[int] = set()
    for grant in _cached_grants(user):
        if code not in _role_permissions(grant.role_slug):
            continue
        scope = _grant_scope(grant, subject)
        if scope is ALL_COMPANY:
            return base
        ids |= scope
    if not ids:
        return base.none()
    return base.filter(pk__in=ids)


def field_access(user, employee, field) -> str:
    """Уровень доступа к полю профиля сотрудника: 'none' | 'view' | 'edit'."""
    if user is None or not getattr(user, "is_authenticated", False):
        return "none"
    if not getattr(field, "is_enabled", True):
        return "none"
    if getattr(user, "is_superuser", False):
        return "edit"

    tab = field.group.tab
    code = f"people.field.{tab}"
    subject = _subject_employee(user)
    levels: set[str] = set()
    for grant in _cached_grants(user):
        role_perms = _role_permissions(grant.role_slug)
        level = role_perms.get(code)
        if level is None:
            continue
        scope = _grant_scope(grant, subject)
        in_scope = scope is ALL_COMPANY or employee.id in scope
        if in_scope and level:
            levels.add(level)
    if "edit" in levels:
        return "edit"
    if "view" in levels:
        return "view"
    return "none"
