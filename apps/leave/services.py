from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.employees.models import Employee

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


def inclusive_calendar_days(start: date, end: date) -> int:
    return max(1, (end - start).days + 1)


def inclusive_working_days(start: date, end: date) -> int:
    days = inclusive_calendar_days(start, end)
    return sum(1 for offset in range(days) if (start + timedelta(days=offset)).weekday() < 5)


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


def leave_request_amount(leave_request: LeaveRequest, assignment: EmployeeLeavePolicyAssignment | None = None) -> Decimal:
    if leave_request.amount is not None:
        amount = money(leave_request.amount)
        if amount > ZERO:
            return amount
    counted_as = assignment.policy.counted_as if assignment else LeavePolicy.CountedAs.CALENDAR_DAYS
    if counted_as == LeavePolicy.CountedAs.WORKING_DAYS:
        amount = Decimal(inclusive_working_days(leave_request.date_from, leave_request.date_to))
    else:
        amount = Decimal(inclusive_calendar_days(leave_request.date_from, leave_request.date_to))
    return money(amount)


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


def _due_dates(rule: LeavePolicyAccrualRule, start: date, through_date: date):
    if rule.frequency == LeavePolicyAccrualRule.Frequency.NONE:
        return
    base = start
    while base <= through_date:
        if rule.accrual_timing == LeavePolicyAccrualRule.AccrualTiming.PERIOD_END:
            due = add_period(base, rule.frequency) - timedelta(days=1)
        else:
            due = base
        if due > through_date:
            return
        yield due
        base = add_period(base, rule.frequency)


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
        amount = leave_request_amount(leave_request, assignment)
        if amount <= ZERO:
            raise ValidationError({"amount": "Кількість днів має бути більшою за 0."})
        if leave_request.amount != amount:
            leave_request.amount = amount
            if not leave_request.tracking_time_in:
                leave_request.tracking_time_in = leave_request.leave_type.unit
        request_entry = post_ledger_entry(
            employee=leave_request.employee,
            leave_type=leave_request.leave_type,
            policy=assignment.policy,
            assignment=assignment,
            kind=LeaveLedgerEntry.EntryKind.REQUEST,
            occurred_on=leave_request.date_from,
            amount=-amount,
            description=f"Списання за заявкою #{leave_request.id}",
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
