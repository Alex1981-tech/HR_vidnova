"""Резолв аудиторії оголошення з умов конструктора.

Формат умови (UI): {"field": "department", "operator": "is", "value": [<id>, ...]}.
Базова умова PF «Цикл зайнятості є Працюючі» застосовується завжди → status=ACTIVE.
"""

from __future__ import annotations

from django.db.models import Q
from django.utils import timezone

from apps.employees.models import Employee, Gender, ManagerAssignment

# field → ORM-шлях до id (для is/is_not/is_empty/is_not_empty).
FIELD_PATHS = {
    "employee": "id",
    "person": "id",
    "specific_person": "id",
    "department": "department_id",
    "department_level": "department__level_id",
    "division": "division_id",
    "clinic": "clinic_id",          # «Локація»
    "location": "clinic_id",
    "position": "position_id",
    "job_level": "job_level_id",
    "employment_type": "employment_type_id",
}

PRESENCE_FIELD_PATHS = {
    "instagram_url": "instagram_url",
    "employee_number": "employee_number",
    "first_name": "first_name",
    "last_name": "last_name",
    "email": "email",
    "personal_email": "personal_email",
    "phone": "phone",
    "phone2": "phone2",
    "birth_date": "birth_date",
    "hired_on": "hired_on",
    "dismissed_on": "dismissed_on",
}

# M2M-поля резолвляться окремо (team через memberships).
M2M_FIELDS = {"team"}

OPERATORS = {"is", "is_not", "is_empty", "is_not_empty"}


def _ids(value):
    if value is None:
        return []
    if not isinstance(value, (list, tuple)):
        value = [value]
    out = []
    for v in value:
        try:
            out.append(int(v))
        except (ValueError, TypeError):
            continue
    return out


def _active_manager_q(prefix="manager_assignments"):
    today = timezone.localdate()
    return (
        Q(**{f"{prefix}__is_primary": True})
        & Q(**{f"{prefix}__valid_from__lte": today})
        & (Q(**{f"{prefix}__valid_to__isnull": True}) | Q(**{f"{prefix}__valid_to__gte": today}))
    )


def _field_empty_query(path):
    query = Q(**{f"{path}__isnull": True})
    if "__" not in path:
        query |= Q(**{path: ""})
    return query


def _descendant_employee_ids(manager_ids):
    today = timezone.localdate()
    seen = set()
    frontier = set(manager_ids)
    while frontier:
        direct = set(
            ManagerAssignment.objects.filter(
                manager_id__in=frontier,
                is_primary=True,
                valid_from__lte=today,
            )
            .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today))
            .values_list("employee_id", flat=True)
        )
        direct -= seen
        if not direct:
            break
        seen |= direct
        frontier = direct
    return list(seen)


def _apply_condition(qs, condition):
    if not isinstance(condition, dict):
        return qs
    field = condition.get("field")
    operator = condition.get("operator", "is")
    if operator not in OPERATORS:
        operator = "is"

    if field in M2M_FIELDS:
        # team через активні membership
        if operator == "is_empty":
            return qs.exclude(team_memberships__is_active=True)
        if operator == "is_not_empty":
            return qs.filter(team_memberships__is_active=True).distinct()
        ids = _ids(condition.get("value"))
        if not ids:
            return qs
        match = Q(team_memberships__team_id__in=ids, team_memberships__is_active=True)
        return qs.filter(~match if operator == "is_not" else match).distinct()

    if field == "gender":
        if operator == "is_empty":
            return qs.filter(Q(gender="") | Q(gender__isnull=True))
        if operator == "is_not_empty":
            return qs.exclude(Q(gender="") | Q(gender__isnull=True))
        ids = _ids(condition.get("value"))
        if not ids:
            return qs
        codes = list(Gender.objects.filter(pk__in=ids).values_list("code", flat=True))
        if not codes:
            return qs
        match = Q(gender__in=codes)
        return qs.filter(~match if operator == "is_not" else match)

    if field in {"manager", "direct_reports"}:
        active_manager = _active_manager_q()
        if operator == "is_empty":
            return qs.exclude(active_manager).distinct()
        if operator == "is_not_empty":
            return qs.filter(active_manager).distinct()
        ids = _ids(condition.get("value"))
        if not ids:
            return qs
        match = active_manager & Q(manager_assignments__manager_id__in=ids)
        return qs.filter(~match if operator == "is_not" else match).distinct()

    if field == "direct_and_indirect_reports":
        ids = _ids(condition.get("value"))
        if not ids:
            return qs
        descendant_ids = _descendant_employee_ids(ids)
        if not descendant_ids:
            return qs.none() if operator != "is_not" else qs
        match = Q(id__in=descendant_ids)
        return qs.filter(~match if operator == "is_not" else match).distinct()

    if field == "probation_policy":
        if operator == "is_empty":
            return qs.filter(employment_status_history__probation_policy__isnull=True).distinct()
        if operator == "is_not_empty":
            return qs.filter(employment_status_history__probation_policy__isnull=False).distinct()
        ids = _ids(condition.get("value"))
        if not ids:
            return qs
        match = Q(employment_status_history__probation_policy_id__in=ids)
        return qs.filter(~match if operator == "is_not" else match).distinct()

    presence_path = PRESENCE_FIELD_PATHS.get(field)
    if presence_path:
        empty_query = _field_empty_query(presence_path)
        if operator == "is_empty":
            return qs.filter(empty_query)
        if operator == "is_not_empty":
            return qs.exclude(empty_query)
        return qs

    path = FIELD_PATHS.get(field)
    if not path:
        return qs

    if operator == "is_empty":
        return qs.filter(**{f"{path}__isnull": True})
    if operator == "is_not_empty":
        return qs.filter(**{f"{path}__isnull": False})
    ids = _ids(condition.get("value"))
    if not ids:
        return qs
    flt = Q(**{f"{path}__in": ids})
    return qs.filter(~flt if operator == "is_not" else flt)


def resolve_audience(audience_type, conditions):
    """Повертає QuerySet активних співробітників за умовами оголошення."""
    qs = Employee.objects.filter(status=Employee.Status.ACTIVE)
    if audience_type == "all":
        return qs.distinct()
    for condition in conditions or []:
        qs = _apply_condition(qs, condition)
    return qs.distinct()
