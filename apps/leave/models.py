from django.conf import settings
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
