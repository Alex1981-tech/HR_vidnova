from django.conf import settings
from django.db import models

from apps.employees.models import Employee


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AccessSystem(TimestampedModel):
    class Kind(models.TextChoices):
        UPROX = "uprox", "UPROX"
        ZKTECO = "zkteco", "ZKTeco"
        LEGACY_SUNC_V4 = "legacy_sunc_v4", "Legacy sunc_v4"
        UNKNOWN = "unknown", "Unknown"

    kind = models.CharField(max_length=40, choices=Kind.choices, unique=True)
    name = models.CharField(max_length=160)
    is_active = models.BooleanField(default=True)
    settings_summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class AccessDevice(TimestampedModel):
    system = models.ForeignKey(AccessSystem, on_delete=models.PROTECT, related_name="devices")
    external_id = models.CharField(max_length=160)
    name = models.CharField(max_length=200)
    clinic_code = models.CharField(max_length=80, blank=True)
    location = models.CharField(max_length=200, blank=True)
    direction_hint = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["system", "external_id"], name="uniq_access_device_system_external"),
        ]
        indexes = [
            models.Index(fields=["system", "is_active"], name="accdev_system_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.system}: {self.name}"


class AccessIdentity(TimestampedModel):
    class Confidence(models.TextChoices):
        MANUAL = "manual", "Manual"
        EXACT = "exact", "Exact"
        IMPORTED = "imported", "Imported"
        LOW = "low", "Low"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="access_identities")
    system = models.ForeignKey(AccessSystem, on_delete=models.PROTECT, related_name="identities")
    external_user_id = models.CharField(max_length=160)
    external_card_code = models.CharField(max_length=160, blank=True)
    matched_by = models.CharField(max_length=80, blank=True)
    confidence = models.CharField(max_length=20, choices=Confidence.choices, default=Confidence.IMPORTED)
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["system", "external_user_id"], name="uniq_access_identity_system_user"),
        ]
        indexes = [
            models.Index(fields=["employee", "is_active"], name="accid_employee_active_idx"),
            models.Index(fields=["system", "external_card_code"], name="access_identity_card_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.employee} @ {self.system}"


class IntegrationRun(TimestampedModel):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"

    system = models.ForeignKey(AccessSystem, on_delete=models.PROTECT, related_name="runs")
    job_name = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    watermark_before = models.CharField(max_length=160, blank=True)
    watermark_after = models.CharField(max_length=160, blank=True)
    rows_fetched = models.PositiveIntegerField(default=0)
    rows_inserted = models.PositiveIntegerField(default=0)
    rows_ignored = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["system", "job_name", "-started_at"], name="integration_run_lookup_idx"),
            models.Index(fields=["status", "-started_at"], name="integration_run_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.system} {self.job_name} {self.status}"


class AccessEventRaw(TimestampedModel):
    system = models.ForeignKey(AccessSystem, on_delete=models.PROTECT, related_name="raw_events")
    source_event_id = models.CharField(max_length=160)
    occurred_at = models.DateTimeField(null=True, blank=True)
    raw_user_id = models.CharField(max_length=160, blank=True)
    raw_user_name = models.CharField(max_length=200, blank=True)
    raw_device_id = models.CharField(max_length=160, blank=True)
    raw_device_name = models.CharField(max_length=200, blank=True)
    raw_message_code = models.CharField(max_length=80, blank=True)
    raw_message_name = models.CharField(max_length=160, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    ingested_at = models.DateTimeField(auto_now_add=True)
    integration_run = models.ForeignKey(IntegrationRun, on_delete=models.SET_NULL, null=True, blank=True, related_name="raw_events")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["system", "source_event_id"], name="uniq_raw_event_system_source"),
        ]
        indexes = [
            models.Index(fields=["system", "occurred_at"], name="raw_event_system_time_idx"),
            models.Index(fields=["raw_user_id", "occurred_at"], name="raw_event_user_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.system}:{self.source_event_id}"


class AccessEvent(TimestampedModel):
    class Direction(models.TextChoices):
        ENTRY = "entry", "Entry"
        EXIT = "exit", "Exit"
        UNKNOWN = "unknown", "Unknown"

    class Quality(models.TextChoices):
        OK = "ok", "OK"
        DUPLICATE = "duplicate", "Duplicate"
        UNKNOWN_EMPLOYEE = "unknown_employee", "Unknown employee"
        SUSPICIOUS_TIME = "suspicious_time", "Suspicious time"
        IGNORED = "ignored", "Ignored"

    raw_event = models.OneToOneField(AccessEventRaw, on_delete=models.CASCADE, related_name="normalized_event")
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="access_events")
    identity = models.ForeignKey(AccessIdentity, on_delete=models.SET_NULL, null=True, blank=True, related_name="access_events")
    device = models.ForeignKey(AccessDevice, on_delete=models.SET_NULL, null=True, blank=True, related_name="access_events")
    occurred_at = models.DateTimeField()
    direction = models.CharField(max_length=20, choices=Direction.choices, default=Direction.UNKNOWN)
    quality = models.CharField(max_length=30, choices=Quality.choices, default=Quality.OK)

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["employee", "occurred_at"], name="access_event_employee_time_idx"),
            models.Index(fields=["quality", "occurred_at"], name="access_event_quality_time_idx"),
            models.Index(fields=["device", "occurred_at"], name="access_event_device_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.employee_id or 'unknown'} {self.direction} {self.occurred_at}"


class AttendancePeriod(TimestampedModel):
    class PeriodType(models.TextChoices):
        REGULAR = "regular", "Regular"
        NIGHT = "night", "Night"
        MANUAL = "manual", "Manual"
        ERROR = "error", "Error"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="attendance_periods")
    date = models.DateField()
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=0)
    period_type = models.CharField(max_length=20, choices=PeriodType.choices, default=PeriodType.REGULAR)
    source_events = models.ManyToManyField(AccessEvent, blank=True, related_name="attendance_periods")
    comment = models.TextField(blank=True)
    calculation_run = models.ForeignKey(IntegrationRun, on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance_periods")

    class Meta:
        ordering = ["date", "start_at"]
        indexes = [
            models.Index(fields=["employee", "date"], name="attperiod_employee_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.employee} {self.date} {self.start_at} - {self.end_at}"


class WorkDaySummary(TimestampedModel):
    class Status(models.TextChoices):
        OK = "ok", "OK"
        LATE = "late", "Late"
        ABSENT = "absent", "Absent"
        MISSING_ENTRY = "missing_entry", "Missing entry"
        MISSING_EXIT = "missing_exit", "Missing exit"
        MANUAL_REVIEW = "manual_review", "Manual review"
        LOCKED = "locked", "Locked"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="workday_summaries")
    date = models.DateField()
    planned_minutes = models.PositiveIntegerField(default=0)
    actual_minutes = models.PositiveIntegerField(default=0)
    first_entry_at = models.DateTimeField(null=True, blank=True)
    last_exit_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.MANUAL_REVIEW)
    exception_count = models.PositiveIntegerField(default=0)
    calculated_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="locked_workdays")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["employee", "date"], name="uniq_workday_employee_date"),
        ]
        ordering = ["-date", "employee__last_name"]
        indexes = [
            models.Index(fields=["date", "status"], name="workday_date_status_idx"),
            models.Index(fields=["employee", "date"], name="workday_employee_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.employee} {self.date}: {self.status}"


class TimeAdjustment(TimestampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="time_adjustments")
    date = models.DateField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="time_adjustments")
    reason = models.TextField()
    before_summary = models.JSONField(default=dict, blank=True)
    after_summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employee", "date"], name="timeadj_employee_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.employee} {self.date}"


class TimeCorrectionRequest(TimestampedModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        APPLIED = "applied", "Applied"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="time_correction_requests")
    date = models.DateField()
    requested_start_at = models.DateTimeField(null=True, blank=True)
    requested_end_at = models.DateTimeField(null=True, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SUBMITTED)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_time_correction_requests",
    )
    decision_comment = models.TextField(blank=True)
    applied_adjustment = models.ForeignKey(
        TimeAdjustment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="correction_requests",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employee", "date"], name="timecorr_employee_date_idx"),
            models.Index(fields=["status", "-created_at"], name="timecorr_status_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.employee} {self.date}: {self.status}"
