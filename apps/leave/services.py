from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.employees.models import Employee, EmployeeEmploymentStatus, Holiday, ManagerAssignment

from .models import (
    EmployeeLeavePolicyAssignment,
    LeaveBalance,
    LeaveLedgerEntry,
    LeavePolicy,
    LeavePolicyAccrualRule,
    LeaveRequest,
    LeaveType,
)


ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def money(value) -> Decimal:
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value.quantize(CENT, rounding=ROUND_HALF_UP)
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def add_delay(value: date, amount: int, unit: str) -> date:
    if amount <= 0:
        return value
    if unit == LeavePolicyAccrualRule.DelayUnit.DAYS:
        return value + timedelta(days=amount)
    if unit == LeavePolicyAccrualRule.DelayUnit.YEARS:
        return add_months(value, amount * 12)
    return add_months(value, amount)


def add_period(value: date, frequency: str) -> date:
    if frequency == LeavePolicyAccrualRule.Frequency.WEEKLY:
        return value + timedelta(days=7)
    if frequency == LeavePolicyAccrualRule.Frequency.YEARLY:
        return add_months(value, 12)
    return add_months(value, 1)


def period_start_containing(value: date, frequency: str) -> date:
    if frequency == LeavePolicyAccrualRule.Frequency.WEEKLY:
        return value - timedelta(days=value.weekday())
    if frequency == LeavePolicyAccrualRule.Frequency.YEARLY:
        return value.replace(month=1, day=1)
    return value.replace(day=1)


def period_amount(rule: LeavePolicyAccrualRule) -> Decimal:
    explicit = money(rule.period_amount)
    if explicit:
        return explicit
    annual = money(rule.annual_allowance)
    if not annual:
        return ZERO
    if rule.frequency == LeavePolicyAccrualRule.Frequency.YEARLY:
        return annual
    if rule.frequency == LeavePolicyAccrualRule.Frequency.WEEKLY:
        return money(annual / Decimal("52"))
    return money(annual / Decimal("12"))


def current_balance(employee: Employee, leave_type: LeaveType, *, through_date: date | None = None) -> Decimal:
    qs = LeaveLedgerEntry.objects.filter(employee=employee, leave_type=leave_type)
    if through_date:
        qs = qs.filter(occurred_on__lte=through_date)
    total = qs.aggregate(total=Sum("amount"))["total"]
    return money(total)


def date_span(start: date, end: date):
    days = max(0, (end - start).days)
    for offset in range(days + 1):
        yield start + timedelta(days=offset)


def inclusive_calendar_days(start: date, end: date, *, exclude_dates: set[date] | None = None) -> int:
    excluded = exclude_dates or set()
    return sum(1 for current in date_span(start, end) if current not in excluded)


def inclusive_working_days(start: date, end: date, *, exclude_dates: set[date] | None = None) -> int:
    excluded = exclude_dates or set()
    return sum(1 for current in date_span(start, end) if current.weekday() < 5 and current not in excluded)


def active_assignment_for_request(leave_request: LeaveRequest) -> EmployeeLeavePolicyAssignment | None:
    return (
        EmployeeLeavePolicyAssignment.objects.select_related("policy", "leave_type", "employee")
        .filter(
            employee=leave_request.employee,
            leave_type=leave_request.leave_type,
            effective_on__lte=leave_request.date_from,
        )
        .filter(Q(ends_on__isnull=True) | Q(ends_on__gte=leave_request.date_from))
        .order_by("-is_active", "-effective_on", "-id")
        .first()
    )


def non_working_holiday_dates(employee: Employee, start: date, end: date) -> set[date]:
    clinic = getattr(employee, "clinic", None)
    policy = getattr(clinic, "holiday_policy_ref", None)
    if not policy:
        return set()
    holidays = (
        Holiday.objects.filter(policy=policy, is_active=True, working=False)
        .filter(
            Q(occurs_on__range=(start, end))
            | Q(observed_on__range=(start, end))
            | Q(starts_on__lte=end, ends_on__gte=start)
            | Q(recurrence=Holiday.Recurrence.YEARLY)
        )
    )
    dates: set[date] = set()
    for holiday in holidays:
        if holiday.starts_on and holiday.ends_on:
            for current in date_span(max(start, holiday.starts_on), min(end, holiday.ends_on)):
                dates.add(current)
            continue
        if holiday.observed_on and start <= holiday.observed_on <= end:
            dates.add(holiday.observed_on)
            continue
        if holiday.recurrence == Holiday.Recurrence.YEARLY:
            for year in range(start.year, end.year + 1):
                try:
                    recurring = holiday.occurs_on.replace(year=year)
                except ValueError:
                    continue
                if start <= recurring <= end:
                    dates.add(recurring)
            continue
        if start <= holiday.occurs_on <= end:
            dates.add(holiday.occurs_on)
    return dates


def leave_request_amount(leave_request: LeaveRequest, assignment: EmployeeLeavePolicyAssignment | None = None) -> Decimal:
    if leave_request.amount is not None:
        amount = money(leave_request.amount)
        if amount > ZERO and not (assignment and assignment.policy.forbid_breakdown_edit):
            return amount
    counted_as = assignment.policy.counted_as if assignment else LeavePolicy.CountedAs.CALENDAR_DAYS
    excluded_dates: set[date] = set()
    if assignment and not assignment.policy.deduct_non_working_holidays:
        excluded_dates = non_working_holiday_dates(assignment.employee, leave_request.date_from, leave_request.date_to)
    if counted_as == LeavePolicy.CountedAs.WORKING_DAYS:
        amount = Decimal(inclusive_working_days(leave_request.date_from, leave_request.date_to, exclude_dates=excluded_dates))
    else:
        amount = Decimal(inclusive_calendar_days(leave_request.date_from, leave_request.date_to, exclude_dates=excluded_dates))
    return money(amount)


def calculated_leave_request_amount(leave_request: LeaveRequest, assignment: EmployeeLeavePolicyAssignment) -> Decimal:
    original = leave_request.amount
    leave_request.amount = None
    try:
        return leave_request_amount(leave_request, assignment)
    finally:
        leave_request.amount = original


def request_balance_delta(amount: Decimal, policy: LeavePolicy) -> Decimal:
    if policy.activity_type == LeavePolicy.ActivityType.NOT_WORKING_UNPAID:
        return amount
    if policy.activity_type == LeavePolicy.ActivityType.WORKING_PAID:
        return ZERO
    return -amount


def employee_on_probation(employee: Employee, on_date: date) -> bool:
    status = (
        EmployeeEmploymentStatus.objects.select_related("probation_policy")
        .filter(employee=employee)
        .filter(Q(effective_from__isnull=True) | Q(effective_from__lte=on_date))
        .order_by("-effective_from", "-id")
        .first()
    )
    policy = getattr(status, "probation_policy", None) if status else None
    if not policy:
        return False
    start = status.effective_from or employee.hired_on
    if not start:
        return True
    return on_date < add_months(start, policy.duration_months)


def is_direct_report(manager: Employee, employee: Employee, on_date: date) -> bool:
    return ManagerAssignment.objects.filter(
        manager=manager,
        employee=employee,
        is_primary=True,
        valid_from__lte=on_date,
    ).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=on_date)).exists()


def validate_leave_request_policy(
    leave_request: LeaveRequest,
    assignment: EmployeeLeavePolicyAssignment | None = None,
    *,
    actor=None,
) -> None:
    assignment = assignment or active_assignment_for_request(leave_request)
    if not assignment:
        return
    policy = assignment.policy
    errors = {}
    amount = leave_request_amount(leave_request, assignment)
    calculated_amount = calculated_leave_request_amount(leave_request, assignment)

    if policy.prevent_overlapping_requests:
        overlap = LeaveRequest.objects.filter(
            employee=leave_request.employee,
            date_from__lte=leave_request.date_to,
            date_to__gte=leave_request.date_from,
        ).exclude(status__in=[LeaveRequest.Status.REJECTED, LeaveRequest.Status.CANCELLED])
        if leave_request.pk:
            overlap = overlap.exclude(pk=leave_request.pk)
        if overlap.exists():
            errors["date_from"] = "Запит перетинається з іншою відсутністю."

    if policy.forbid_probation_requests and employee_on_probation(leave_request.employee, leave_request.date_from):
        errors["date_from"] = "Запити за цією політикою заборонені під час випробувального терміну."

    if policy.direct_reports_only and actor and getattr(actor, "is_authenticated", False) and not getattr(actor, "is_superuser", False):
        actor_employee = getattr(actor, "employee_profile", None)
        if actor_employee and actor_employee != leave_request.employee and not is_direct_report(actor_employee, leave_request.employee, leave_request.date_from):
            errors["employee"] = "За цією політикою менеджер може подавати запити тільки для прямих підлеглих."

    if policy.mandatory_comment and not (leave_request.reason or "").strip():
        errors["reason"] = "Для цієї політики потрібен коментар."

    if policy.forbid_breakdown_edit and leave_request.amount is not None and money(leave_request.amount) != calculated_amount:
        errors["amount"] = "Редагування розбивки заборонено для цієї політики."

    if policy.min_total_amount is not None and amount < policy.min_total_amount:
        errors["amount"] = f"Мінімальна загальна сума для цієї політики: {policy.min_total_amount}."
    if policy.max_total_amount is not None and amount > policy.max_total_amount:
        errors["amount"] = f"Максимальна загальна сума для цієї політики: {policy.max_total_amount}."
    if policy.min_daily_amount is not None:
        minimum_amount = money(policy.min_daily_amount) * calculated_amount
        if amount < minimum_amount:
            errors["amount"] = f"Мінімальна щоденна сума для цієї політики: {policy.min_daily_amount}."
    if policy.allow_on_demand_absence and policy.on_demand_limit is not None and amount > policy.on_demand_limit:
        errors["amount"] = f"Максимальна кількість відсутності на вимогу: {policy.on_demand_limit}."

    notice_days = (leave_request.date_from - timezone.localdate()).days
    if policy.min_notice_days is not None and notice_days < policy.min_notice_days:
        errors["date_from"] = f"Потрібно подати запит щонайменше за {policy.min_notice_days} дн."
    if policy.max_notice_days is not None and notice_days > policy.max_notice_days:
        errors["date_from"] = f"Не можна подати запит раніше ніж за {policy.max_notice_days} дн."

    delta = request_balance_delta(amount, policy)
    if delta < ZERO:
        projected_balance = current_balance(leave_request.employee, leave_request.leave_type, through_date=leave_request.date_from) + delta
        if not policy.allow_negative_balance and projected_balance < ZERO:
            errors["amount"] = "Запит призведе до негативного балансу."
        if policy.allow_negative_balance and policy.limit_negative_balance and policy.max_negative_balance is not None:
            allowed_floor = -money(policy.max_negative_balance)
            if projected_balance < allowed_floor:
                errors["amount"] = f"Максимальний негативний баланс для цієї політики: -{policy.max_negative_balance}."

    if errors:
        raise ValidationError(errors)


def update_balance_cache(assignment: EmployeeLeavePolicyAssignment, *, through_date: date | None = None) -> LeaveBalance:
    balance = current_balance(assignment.employee, assignment.leave_type, through_date=through_date)
    return LeaveBalance.objects.update_or_create(
        employee=assignment.employee,
        leave_type=assignment.leave_type,
        legacy_peopleforce_id=f"assignment:{assignment.id}",
        defaults={
            "effective_on": assignment.effective_on,
            "balance": balance,
            "policy_name": assignment.policy.name,
            "policy_activity_type": assignment.policy.activity_type,
            "policy_counted_as": assignment.policy.counted_as,
            "legacy_payload": {
                "source": "hr_vidnova_assignment",
                "assignment_id": assignment.id,
                "policy_id": assignment.policy_id,
                "policy_type": assignment.policy.policy_type,
            },
        },
    )[0]


@transaction.atomic
def post_ledger_entry(
    *,
    employee: Employee,
    leave_type: LeaveType,
    policy: LeavePolicy | None,
    assignment: EmployeeLeavePolicyAssignment | None,
    kind: str,
    occurred_on: date,
    amount,
    description: str = "",
    idempotency_key: str = "",
    source_model: str = "",
    source_id: str = "",
) -> LeaveLedgerEntry:
    amount = money(amount)
    if idempotency_key:
        existing = LeaveLedgerEntry.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing
    balance_after = current_balance(employee, leave_type) + amount
    entry = LeaveLedgerEntry(
        employee=employee,
        leave_type=leave_type,
        policy=policy,
        assignment=assignment,
        kind=kind,
        occurred_on=occurred_on,
        amount=amount,
        balance_after=balance_after,
        description=description,
        idempotency_key=idempotency_key,
        source_model=source_model,
        source_id=source_id,
    )
    entry.full_clean()
    entry.save()
    return entry


def _due_dates_for(frequency: str, accrual_timing: str, start: date, through_date: date):
    if frequency == LeavePolicyAccrualRule.Frequency.NONE:
        return
    period_start = period_start_containing(start, frequency)
    while True:
        if accrual_timing == LeavePolicyAccrualRule.AccrualTiming.PERIOD_START:
            due = period_start
        else:
            due = add_period(period_start, frequency) - timedelta(days=1)
        if due < start:
            period_start = add_period(period_start, frequency)
            continue
        if due > through_date:
            return
        yield due
        period_start = add_period(period_start, frequency)


def _due_dates(rule: LeavePolicyAccrualRule, start: date, through_date: date):
    yield from _due_dates_for(rule.frequency, rule.accrual_timing, start, through_date)


def _level_value(level: dict, field: str, default=None):
    value = level.get(field, default)
    if value in (None, ""):
        return default
    return value


def _level_money(level: dict, field: str, default=ZERO) -> Decimal:
    return money(_level_value(level, field, default))


def _level_int(level: dict, field: str, default: int = 0) -> int:
    value = _level_value(level, field, default)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return default


def _active_seniority_levels(rule: LeavePolicyAccrualRule) -> list[dict]:
    if not rule.seniority_bonus_enabled or not isinstance(rule.seniority_bonus_levels, list):
        return []
    return [level for level in rule.seniority_bonus_levels if isinstance(level, dict)]


def _assignment_opening_date(assignment: EmployeeLeavePolicyAssignment) -> date | None:
    return (
        LeaveLedgerEntry.objects.filter(assignment=assignment, kind=LeaveLedgerEntry.EntryKind.OPENING)
        .order_by("-occurred_on", "-id")
        .values_list("occurred_on", flat=True)
        .first()
    )


@transaction.atomic
def sync_assignment_balance(
    assignment: EmployeeLeavePolicyAssignment,
    *,
    through_date: date | None = None,
) -> LeaveBalance:
    assignment = (
        EmployeeLeavePolicyAssignment.objects.select_related("employee", "leave_type", "policy")
        .select_for_update()
        .get(pk=assignment.pk)
    )
    through_date = through_date or timezone.localdate()

    rule = getattr(assignment.policy, "accrual_rule", None)
    opening = money(assignment.initial_balance)
    if assignment.policy.policy_type == LeavePolicy.PolicyType.ACCRUAL and rule and rule.enabled:
        opening += money(rule.start_balance)
    opening_date = _assignment_opening_date(assignment)
    if opening and not opening_date:
        post_ledger_entry(
            employee=assignment.employee,
            leave_type=assignment.leave_type,
            policy=assignment.policy,
            assignment=assignment,
            kind=LeaveLedgerEntry.EntryKind.OPENING,
            occurred_on=assignment.effective_on,
            amount=opening,
            description="Початковий баланс політики",
            idempotency_key=f"leave-assignment:{assignment.id}:opening",
            source_model="EmployeeLeavePolicyAssignment",
            source_id=str(assignment.id),
        )

    if assignment.policy.policy_type == LeavePolicy.PolicyType.ACCRUAL and rule and rule.enabled:
        amount = period_amount(rule)
        if amount and rule.first_accrual != LeavePolicyAccrualRule.FirstAccrual.NONE:
            accrual_start = add_delay(assignment.effective_on, rule.start_delay_amount, rule.start_delay_unit)
            for due_on in _due_dates(rule, accrual_start, through_date):
                if opening_date and due_on <= opening_date:
                    continue
                if assignment.ends_on and due_on > assignment.ends_on:
                    break
                amount_to_post = amount
                if rule.max_balance is not None:
                    balance_before = current_balance(assignment.employee, assignment.leave_type)
                    remaining = money(rule.max_balance) - balance_before
                    if remaining <= ZERO:
                        continue
                    amount_to_post = min(amount, remaining)
                if amount_to_post <= ZERO:
                    continue
                post_ledger_entry(
                    employee=assignment.employee,
                    leave_type=assignment.leave_type,
                    policy=assignment.policy,
                    assignment=assignment,
                    kind=LeaveLedgerEntry.EntryKind.ACCRUAL,
                    occurred_on=due_on,
                    amount=amount_to_post,
                    description=f"Нарахування за політикою «{assignment.policy.name}»",
                    idempotency_key=f"leave-assignment:{assignment.id}:accrual:{due_on.isoformat()}",
                    source_model="EmployeeLeavePolicyAssignment",
                    source_id=str(assignment.id),
                )

        for index, level in enumerate(_active_seniority_levels(rule), start=1):
            amount = _level_money(level, "period_amount", _level_money(level, "bonus_amount", ZERO))
            if amount <= ZERO:
                continue
            threshold_years = _level_int(level, "seniority_years", _level_int(level, "years", 0))
            seniority_base = assignment.employee.hired_on or assignment.effective_on
            eligible_on = add_months(seniority_base, threshold_years * 12)
            level_delay_amount = _level_int(level, "start_delay_amount", 0)
            level_delay_unit = str(_level_value(level, "start_delay_unit", rule.start_delay_unit))
            level_start = add_delay(assignment.effective_on, level_delay_amount, level_delay_unit)
            if level_start < eligible_on:
                level_start = eligible_on
            if level_start < assignment.effective_on:
                level_start = assignment.effective_on
            frequency = str(_level_value(level, "frequency", rule.frequency))
            accrual_timing = str(_level_value(level, "accrual_timing", rule.accrual_timing))
            level_id = str(_level_value(level, "id", index))
            max_balance_raw = _level_value(level, "max_balance", rule.max_balance)
            max_balance = money(max_balance_raw) if max_balance_raw not in (None, "") else None
            for due_on in _due_dates_for(frequency, accrual_timing, level_start, through_date):
                if opening_date and due_on <= opening_date:
                    continue
                if assignment.ends_on and due_on > assignment.ends_on:
                    break
                amount_to_post = amount
                if max_balance is not None:
                    balance_before = current_balance(assignment.employee, assignment.leave_type)
                    remaining = max_balance - balance_before
                    if remaining <= ZERO:
                        continue
                    amount_to_post = min(amount, remaining)
                if amount_to_post <= ZERO:
                    continue
                post_ledger_entry(
                    employee=assignment.employee,
                    leave_type=assignment.leave_type,
                    policy=assignment.policy,
                    assignment=assignment,
                    kind=LeaveLedgerEntry.EntryKind.ACCRUAL,
                    occurred_on=due_on,
                    amount=amount_to_post,
                    description=f"Додаткове нарахування за стаж «{assignment.policy.name}»",
                    idempotency_key=f"leave-assignment:{assignment.id}:seniority:{level_id}:{due_on.isoformat()}",
                    source_model="EmployeeLeavePolicyAssignment",
                    source_id=str(assignment.id),
                )

    return update_balance_cache(assignment, through_date=through_date)


@transaction.atomic
def assign_policy_to_employee(
    *,
    employee: Employee,
    policy: LeavePolicy,
    effective_on: date,
    initial_balance=ZERO,
    replace_current: bool = True,
) -> EmployeeLeavePolicyAssignment:
    if replace_current:
        current_qs = EmployeeLeavePolicyAssignment.objects.select_for_update().filter(
            employee=employee,
            leave_type=policy.leave_type,
            is_active=True,
        )
        current_qs = current_qs.filter(Q(ends_on__isnull=True) | Q(ends_on__gte=effective_on))
        for current in current_qs:
            if current.effective_on < effective_on:
                current.ends_on = effective_on - timedelta(days=1)
            current.is_active = False
            current.full_clean()
            current.save(update_fields=["ends_on", "is_active", "updated_at"])

    assignment = EmployeeLeavePolicyAssignment(
        employee=employee,
        leave_type=policy.leave_type,
        policy=policy,
        effective_on=effective_on,
        initial_balance=money(initial_balance),
    )
    assignment.full_clean()
    assignment.save()
    sync_assignment_balance(assignment)
    return assignment


def recalculate_policy_assignments(policy: LeavePolicy, *, through_date: date | None = None) -> int:
    assignments = EmployeeLeavePolicyAssignment.objects.filter(policy=policy, is_active=True)
    count = 0
    for assignment in assignments.iterator():
        sync_assignment_balance(assignment, through_date=through_date)
        count += 1
    return count


@transaction.atomic
def transition_leave_request_status(
    leave_request: LeaveRequest,
    *,
    status: str,
    user=None,
    comment: str = "",
) -> LeaveRequest:
    leave_request = (
        LeaveRequest.objects.select_related("employee", "leave_type")
        .select_for_update()
        .get(pk=leave_request.pk)
    )
    old_status = leave_request.status
    if status == old_status:
        return leave_request
    if status not in LeaveRequest.Status.values:
        raise ValidationError({"status": "Невідомий статус заявки."})

    assignment = active_assignment_for_request(leave_request)
    request_entry = LeaveLedgerEntry.objects.filter(
        source_model="LeaveRequest",
        source_id=str(leave_request.id),
        kind=LeaveLedgerEntry.EntryKind.REQUEST,
        idempotency_key=f"leave-request:{leave_request.id}:approved",
    ).first()

    if status == LeaveRequest.Status.APPROVED:
        if not assignment:
            raise ValidationError({"policy": "Для співробітника не знайдено призначену політику на дату заявки."})
        validate_leave_request_policy(leave_request, assignment, actor=user)
        amount = leave_request_amount(leave_request, assignment)
        if amount <= ZERO:
            raise ValidationError({"amount": "Кількість днів має бути більшою за 0."})
        if leave_request.amount != amount:
            leave_request.amount = amount
            if not leave_request.tracking_time_in:
                leave_request.tracking_time_in = leave_request.leave_type.unit
        delta = request_balance_delta(amount, assignment.policy)
        if delta:
            request_entry = post_ledger_entry(
                employee=leave_request.employee,
                leave_type=leave_request.leave_type,
                policy=assignment.policy,
                assignment=assignment,
                kind=LeaveLedgerEntry.EntryKind.REQUEST,
                occurred_on=leave_request.date_from,
                amount=delta,
                description=f"Запит на відсутність #{leave_request.id}",
                idempotency_key=f"leave-request:{leave_request.id}:approved",
                source_model="LeaveRequest",
                source_id=str(leave_request.id),
            )
        update_balance_cache(assignment)

    if old_status == LeaveRequest.Status.APPROVED and status in {
        LeaveRequest.Status.CANCELLED,
        LeaveRequest.Status.REJECTED,
    }:
        if assignment and request_entry:
            reversal_key = f"leave-request:{leave_request.id}:{status}:reversal"
            post_ledger_entry(
                employee=leave_request.employee,
                leave_type=leave_request.leave_type,
                policy=assignment.policy,
                assignment=assignment,
                kind=LeaveLedgerEntry.EntryKind.ADJUSTMENT,
                occurred_on=timezone.localdate(),
                amount=abs(money(request_entry.amount)),
                description=f"Повернення за заявкою #{leave_request.id}: {leave_request.get_status_display()} -> {status}",
                idempotency_key=reversal_key,
                source_model="LeaveRequest",
                source_id=str(leave_request.id),
            )
            update_balance_cache(assignment)

    leave_request.status = status
    if status in {LeaveRequest.Status.APPROVED, LeaveRequest.Status.REJECTED, LeaveRequest.Status.CANCELLED}:
        leave_request.decided_at = timezone.now()
        if user and getattr(user, "is_authenticated", False):
            leave_request.decided_by = user
    if comment:
        payload = dict(leave_request.legacy_payload or {})
        payload.setdefault("status_comments", []).append(
            {
                "status": status,
                "comment": comment,
                "at": timezone.now().isoformat(),
                "by": getattr(user, "pk", None),
            }
        )
        leave_request.legacy_payload = payload
    leave_request.full_clean()
    leave_request.save()
    return leave_request
