from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.employees.models import Employee


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LeaveType(TimestampedModel):
    class TrackingUnit(models.TextChoices):
        DAYS = "days", "У днях"
        HOURS = "hours", "У годинах"

    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=40, unique=True)
    legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    unit = models.CharField(
        max_length=40, choices=TrackingUnit.choices, default=TrackingUnit.DAYS, blank=True,
        help_text="Одиниця відстеження відсутності (days|hours)",
    )
    icon = models.CharField(max_length=40, blank=True, help_text="Ключ іконки (frontend)")
    color = models.CharField(max_length=40, blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)
    legacy_payload = models.JSONField(default=dict, blank=True)
    requires_hr_approval = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return self.name


class LeavePolicy(TimestampedModel):
    class PolicyType(models.TextChoices):
        ACCRUAL = "accrual", "З нарахуванням"
        MANUAL = "manual", "Без нарахування"
        EXTERNAL = "external", "Зовнішній баланс"

    class ActivityType(models.TextChoices):
        NOT_WORKING_PAID = "not_working_paid", "Неробочі, оплачувані"
        NOT_WORKING_UNPAID = "not_working_unpaid", "Неробочі, неоплачувані"
        WORKING_PAID = "working_paid", "Робочі, оплачувані"

    class CountedAs(models.TextChoices):
        WORKING_DAYS = "working_days", "Робочі дні"
        CALENDAR_DAYS = "calendar_days", "Календарні дні"

    class Visibility(models.TextChoices):
        EVERYONE = "everyone", "Для всіх"
        SELF_ONLY = "self_only", "Для себе"

    class RoundingMethod(models.TextChoices):
        NEAREST = "nearest", "До найближчого"
        DOWN = "down", "Вниз"
        UP = "up", "Вгору"

    class RoundingPrecision(models.TextChoices):
        TWO_DECIMALS = "two_decimals", "Два знаки після коми"
        ONE_DECIMAL = "one_decimal", "Один знак після коми"
        INTEGER = "integer", "Ціле число"

    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name="policies")
    name = models.CharField(max_length=180)
    legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    policy_type = models.CharField(max_length=24, choices=PolicyType.choices, default=PolicyType.MANUAL)
    activity_type = models.CharField(
        max_length=32,
        choices=ActivityType.choices,
        default=ActivityType.NOT_WORKING_PAID,
    )
    counted_as = models.CharField(max_length=24, choices=CountedAs.choices, default=CountedAs.WORKING_DAYS)
    visibility = models.CharField(max_length=24, choices=Visibility.choices, default=Visibility.EVERYONE)
    instructions_html = models.TextField(blank=True)
    prevent_overlapping_requests = models.BooleanField(default=True)
    forbid_probation_requests = models.BooleanField(default=False)
    forbid_breakdown_edit = models.BooleanField(default=False)
    restrict_adjustments_for_employees = models.BooleanField(default=False)
    direct_reports_only = models.BooleanField(default=False)
    min_daily_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    min_total_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    max_total_amount = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    min_notice_days = models.PositiveIntegerField(null=True, blank=True)
    max_notice_days = models.PositiveIntegerField(null=True, blank=True)
    approval_enabled = models.BooleanField(default=True)
    skip_unassigned_approvers = models.BooleanField(default=False)
    allow_substitute_approvers = models.BooleanField(default=False)
    approver_steps = models.JSONField(default=list, blank=True)
    rounding_method = models.CharField(max_length=24, choices=RoundingMethod.choices, default=RoundingMethod.NEAREST)
    rounding_precision = models.CharField(
        max_length=24,
        choices=RoundingPrecision.choices,
        default=RoundingPrecision.TWO_DECIMALS,
    )
    allow_withdraw = models.BooleanField(default=True)
    mandatory_comment = models.BooleanField(default=False)
    allow_attachments = models.BooleanField(default=False)
    notify_approver = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    legacy_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["leave_type__order", "leave_type__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["legacy_peopleforce_id"],
                name="uniq_leave_policy_pf",
                condition=~models.Q(legacy_peopleforce_id=""),
            ),
            models.UniqueConstraint(
                fields=["leave_type", "name"],
                name="uniq_active_leave_policy_name",
                condition=models.Q(is_active=True),
            ),
        ]
        indexes = [
            models.Index(fields=["leave_type", "is_active"], name="leave_policy_type_active_idx"),
            models.Index(fields=["policy_type", "is_active"], name="leave_policy_kind_active_idx"),
        ]

    @property
    def is_accrual(self) -> bool:
        return self.policy_type == self.PolicyType.ACCRUAL

    def __str__(self) -> str:
        return f"{self.leave_type}: {self.name}"


class LeavePolicyAccrualRule(TimestampedModel):
    class DelayUnit(models.TextChoices):
        DAYS = "days", "Дні"
        MONTHS = "months", "Місяці"
        YEARS = "years", "Роки"

    class Frequency(models.TextChoices):
        NONE = "none", "Немає"
        MONTHLY = "monthly", "Щомісяця"
        YEARLY = "yearly", "Щороку"
        WEEKLY = "weekly", "Щотижня"

    class AccrualTiming(models.TextChoices):
        PERIOD_START = "period_start", "Початок періоду"
        PERIOD_END = "period_end", "Кінець періоду"

    class FirstAccrual(models.TextChoices):
        PROPORTIONAL = "proportional", "Пропорційна"
        FULL = "full", "Повна"
        NONE = "none", "Не нараховувати"

    class CarryoverMode(models.TextChoices):
        NONE = "none", "Немає"
        ALL = "all", "Усе"
        LIMITED = "limited", "Обмежено"

    policy = models.OneToOneField(LeavePolicy, on_delete=models.CASCADE, related_name="accrual_rule")
    enabled = models.BooleanField(default=False)
    start_delay_amount = models.PositiveIntegerField(default=0)
    start_delay_unit = models.CharField(max_length=12, choices=DelayUnit.choices, default=DelayUnit.MONTHS)
    start_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    annual_allowance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    period_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    frequency = models.CharField(max_length=16, choices=Frequency.choices, default=Frequency.MONTHLY)
    accrual_timing = models.CharField(max_length=16, choices=AccrualTiming.choices, default=AccrualTiming.PERIOD_START)
    first_accrual = models.CharField(max_length=16, choices=FirstAccrual.choices, default=FirstAccrual.PROPORTIONAL)
    max_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    carryover_mode = models.CharField(max_length=12, choices=CarryoverMode.choices, default=CarryoverMode.NONE)
    carryover_limit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    carryover_expire_months = models.PositiveIntegerField(default=0)
    carryover_day = models.PositiveSmallIntegerField(default=1)
    carryover_month = models.PositiveSmallIntegerField(default=1)
    seniority_bonus_enabled = models.BooleanField(default=False)

    class Meta:
        ordering = ["policy__leave_type__order", "policy__name"]

    def clean(self):
        if self.policy_id and self.policy.policy_type != LeavePolicy.PolicyType.ACCRUAL and self.enabled:
            raise ValidationError("Правило нарахування можна вмикати тільки для політик з типом accrual.")
        if self.carryover_day < 1 or self.carryover_day > 31:
            raise ValidationError({"carryover_day": "День перенесення має бути від 1 до 31."})
        if self.carryover_month < 1 or self.carryover_month > 12:
            raise ValidationError({"carryover_month": "Місяць перенесення має бути від 1 до 12."})

    def __str__(self) -> str:
        return f"Нарахування: {self.policy}"


class EmployeeLeavePolicyAssignment(TimestampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_policy_assignments")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="policy_assignments")
    policy = models.ForeignKey(LeavePolicy, on_delete=models.PROTECT, related_name="assignments")
    effective_on = models.DateField()
    ends_on = models.DateField(null=True, blank=True)
    initial_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["employee", "leave_type", "-effective_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["legacy_peopleforce_id"],
                name="uniq_leave_assignment_pf",
                condition=~models.Q(legacy_peopleforce_id=""),
            ),
        ]
        indexes = [
            models.Index(fields=["employee", "leave_type", "is_active"], name="leave_assign_employee_type_idx"),
            models.Index(fields=["policy", "is_active"], name="leave_assign_policy_active_idx"),
        ]

    def clean(self):
        if self.policy_id and self.leave_type_id and self.policy.leave_type_id != self.leave_type_id:
            raise ValidationError({"policy": "Політика має належати вибраному типу відсутності."})
        if self.ends_on and self.ends_on < self.effective_on:
            raise ValidationError({"ends_on": "Дата завершення не може бути раніше дати початку."})

    def __str__(self) -> str:
        return f"{self.employee} -> {self.policy} з {self.effective_on}"


class LeaveLedgerEntry(TimestampedModel):
    class EntryKind(models.TextChoices):
        OPENING = "opening_balance", "Початковий баланс"
        ACCRUAL = "accrual", "Нарахування"
        REQUEST = "request", "Запит"
        ADJUSTMENT = "adjustment", "Коригування"
        CARRYOVER = "carryover", "Перенесення"
        EXPIRATION = "expiration", "Списання"
        IMPORT = "import", "Імпорт"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_ledger_entries")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="ledger_entries")
    policy = models.ForeignKey(LeavePolicy, on_delete=models.PROTECT, null=True, blank=True, related_name="ledger_entries")
    assignment = models.ForeignKey(
        EmployeeLeavePolicyAssignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    kind = models.CharField(max_length=32, choices=EntryKind.choices)
    occurred_on = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=260, blank=True)
    source_model = models.CharField(max_length=80, blank=True)
    source_id = models.CharField(max_length=120, blank=True)
    idempotency_key = models.CharField(max_length=180, blank=True, db_index=True)
    legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)

    class Meta:
        ordering = ["employee", "leave_type", "occurred_on", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["idempotency_key"],
                name="uniq_leave_ledger_idempotency",
                condition=~models.Q(idempotency_key=""),
            ),
            models.UniqueConstraint(
                fields=["legacy_peopleforce_id"],
                name="uniq_leave_ledger_pf",
                condition=~models.Q(legacy_peopleforce_id=""),
            ),
        ]
        indexes = [
            models.Index(fields=["employee", "leave_type", "occurred_on"], name="leave_ledger_employee_date_idx"),
            models.Index(fields=["assignment", "kind"], name="leave_ledger_assign_kind_idx"),
        ]

    def clean(self):
        if self.policy_id and self.leave_type_id and self.policy.leave_type_id != self.leave_type_id:
            raise ValidationError({"policy": "Політика має належати вибраному типу відсутності."})
        if self.assignment_id and self.assignment.employee_id != self.employee_id:
            raise ValidationError({"assignment": "Призначення належить іншому співробітнику."})

    def __str__(self) -> str:
        return f"{self.employee} {self.leave_type} {self.kind}: {self.amount}"


class LeaveRequest(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_requests")
    legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="requests")
    date_from = models.DateField()
    date_to = models.DateField()
    reason = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tracking_time_in = models.CharField(max_length=20, blank=True)
    legacy_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="decided_leave_requests")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employee", "date_from", "date_to"], name="leave_employee_dates_idx"),
            models.Index(fields=["status", "-created_at"], name="leave_status_created_idx"),
            models.Index(fields=["legacy_peopleforce_id"], name="leave_request_pf_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.employee} {self.date_from} - {self.date_to}"


class LeaveApprovalStep(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        SKIPPED = "skipped", "Skipped"

    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="approval_steps")
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="leave_approval_steps")
    order = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    decided_at = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ["leave_request", "order"]
        constraints = [
            models.UniqueConstraint(fields=["leave_request", "order"], name="uniq_leave_step_order"),
        ]

    def __str__(self) -> str:
        return f"{self.leave_request} step {self.order}"


class LeaveBalance(TimestampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leave_balances")
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="balances")
    legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    effective_on = models.DateField(null=True, blank=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    policy_name = models.CharField(max_length=180, blank=True)
    policy_activity_type = models.CharField(max_length=80, blank=True)
    policy_counted_as = models.CharField(max_length=80, blank=True)
    legacy_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["employee", "leave_type", "-effective_on"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "leave_type", "legacy_peopleforce_id"],
                name="uniq_leave_balance_pf",
                condition=~models.Q(legacy_peopleforce_id=""),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.employee} {self.leave_type}: {self.balance}"
