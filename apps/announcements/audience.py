"""Резолв аудиторії оголошення з умов конструктора.

Формат умови (UI): {"field": "department", "operator": "is", "value": [<id>, ...]}.
Базова умова PF «Цикл зайнятості є Працюючі» застосовується завжди → status=ACTIVE.
"""

from __future__ import annotations

from django.db.models import Q

from apps.employees.models import Employee

# field → ORM-шлях до id (для is/is_not/is_empty/is_not_empty).
FIELD_PATHS = {
    "department": "department_id",
    "department_level": "department__level_id",
    "division": "division_id",
    "clinic": "clinic_id",          # «Локація»
    "location": "clinic_id",
    "position": "position_id",
    "job_level": "job_level_id",
    "employment_type": "employment_type_id",
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
