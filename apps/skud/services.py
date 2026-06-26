"""Pure SKUD domain helpers.

Adapters for UPROX/ZKTeco will live behind these domain models so the UI and
attendance calculation do not depend on PeopleForce or device-specific payloads.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from django.db.models import Q

from apps.employees.models import EmployeeEmploymentStatus, WorkingPattern


WEEKDAY_HOUR_FIELDS = {
    0: "monday_hours",
    1: "tuesday_hours",
    2: "wednesday_hours",
    3: "thursday_hours",
    4: "friday_hours",
    5: "saturday_hours",
    6: "sunday_hours",
}


@dataclass(frozen=True)
class NormalizedPunch:
    occurred_at: datetime
    direction: str
    source_event_id: str


@dataclass(frozen=True)
class PlannedWorkingTime:
    minutes: int
    pattern_names: tuple[str, ...] = ()


def collapse_near_duplicates(events: Iterable[NormalizedPunch], seconds: int = 180) -> list[NormalizedPunch]:
    """Collapse repeated same-direction punches inside a short window.

    This mirrors the useful ZKTeco "stutter" rule from sunc_v4, but keeps it
    pure so raw events remain immutable in the database.
    """

    ordered = sorted(events, key=lambda item: item.occurred_at)
    if not ordered:
        return []

    collapsed: list[NormalizedPunch] = [ordered[0]]
    threshold = timedelta(seconds=seconds)
    for event in ordered[1:]:
        previous = collapsed[-1]
        if event.direction == previous.direction and event.occurred_at - previous.occurred_at <= threshold:
            collapsed[-1] = event
            continue
        collapsed.append(event)
    return collapsed


def planned_working_time_for_employees(
    employee_ids: Iterable[int],
    date_from: date,
    date_to: date,
) -> dict[int, PlannedWorkingTime]:
    """Calculate expected time from imported PeopleForce working patterns."""

    ids = list(dict.fromkeys(employee_ids))
    if not ids or date_to < date_from:
        return {}

    patterns = list(WorkingPattern.objects.filter(is_active=True))
    if not patterns:
        return {employee_id: PlannedWorkingTime(minutes=0) for employee_id in ids}

    patterns_by_name = {_working_pattern_key(pattern.name): pattern for pattern in patterns}
    default_pattern = next((pattern for pattern in patterns if pattern.is_default), None)
    statuses_by_employee: dict[int, list[EmployeeEmploymentStatus]] = defaultdict(list)
    statuses = (
        EmployeeEmploymentStatus.objects.filter(employee_id__in=ids)
        .exclude(working_pattern_name="")
        .filter(Q(effective_from__lte=date_to) | Q(effective_from__isnull=True))
        .only("employee_id", "working_pattern_name", "effective_from", "created_at")
    )
    for status in statuses:
        statuses_by_employee[status.employee_id].append(status)
    for employee_statuses in statuses_by_employee.values():
        employee_statuses.sort(key=lambda item: (item.effective_from or date.min, item.created_at))

    planned_by_employee: dict[int, PlannedWorkingTime] = {}
    days = list(_date_range(date_from, date_to))
    for employee_id in ids:
        total = 0
        pattern_names: set[str] = set()
        employee_statuses = statuses_by_employee.get(employee_id, [])
        for work_date in days:
            status = _status_for_day(employee_statuses, work_date)
            pattern = None
            if status:
                pattern = patterns_by_name.get(_working_pattern_key(status.working_pattern_name))
            if pattern is None:
                pattern = default_pattern
            if pattern is None:
                continue
            pattern_names.add(pattern.name)
            total += _pattern_minutes_for_date(pattern, work_date)
        planned_by_employee[employee_id] = PlannedWorkingTime(minutes=total, pattern_names=tuple(sorted(pattern_names)))
    return planned_by_employee


def planned_working_time_by_date_for_employee(
    employee_id: int,
    date_from: date,
    date_to: date,
) -> dict[date, PlannedWorkingTime]:
    """Calculate daily expected time for one employee from imported schedules."""

    if date_to < date_from:
        return {}

    patterns = list(WorkingPattern.objects.filter(is_active=True))
    if not patterns:
        return {work_date: PlannedWorkingTime(minutes=0) for work_date in _date_range(date_from, date_to)}

    patterns_by_name = {_working_pattern_key(pattern.name): pattern for pattern in patterns}
    default_pattern = next((pattern for pattern in patterns if pattern.is_default), None)
    statuses = list(
        EmployeeEmploymentStatus.objects.filter(employee_id=employee_id)
        .exclude(working_pattern_name="")
        .filter(Q(effective_from__lte=date_to) | Q(effective_from__isnull=True))
        .only("employee_id", "working_pattern_name", "effective_from", "created_at")
    )
    statuses.sort(key=lambda item: (item.effective_from or date.min, item.created_at))

    planned_by_date: dict[date, PlannedWorkingTime] = {}
    for work_date in _date_range(date_from, date_to):
        status = _status_for_day(statuses, work_date)
        pattern = None
        if status:
            pattern = patterns_by_name.get(_working_pattern_key(status.working_pattern_name))
        if pattern is None:
            pattern = default_pattern
        if pattern is None:
            planned_by_date[work_date] = PlannedWorkingTime(minutes=0)
            continue
        planned_by_date[work_date] = PlannedWorkingTime(minutes=_pattern_minutes_for_date(pattern, work_date), pattern_names=(pattern.name,))
    return planned_by_date


def _date_range(date_from: date, date_to: date) -> Iterable[date]:
    current = date_from
    while current <= date_to:
        yield current
        current += timedelta(days=1)


def _working_pattern_key(value: str) -> str:
    return " ".join((value or "").casefold().split())


def _status_for_day(statuses: list[EmployeeEmploymentStatus], work_date: date) -> EmployeeEmploymentStatus | None:
    selected = None
    for status in statuses:
        if status.effective_from and status.effective_from > work_date:
            break
        selected = status
    return selected


def _pattern_minutes_for_date(pattern: WorkingPattern, work_date: date) -> int:
    field_name = WEEKDAY_HOUR_FIELDS[work_date.weekday()]
    hours = Decimal(getattr(pattern, field_name) or 0)
    return int((hours * Decimal("60")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
