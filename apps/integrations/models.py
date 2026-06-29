from django.db import models

from apps.employees.models import Employee
from apps.skud.models import AttendancePeriod


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PeopleForceImportRun(TimestampedModel):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        DRY_RUN = "dry_run", "Dry run"

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    counters = models.JSONField(default=dict, blank=True)
    options = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["status", "-started_at"], name="pf_import_run_status_idx"),
        ]

    def __str__(self) -> str:
        return f"PeopleForce {self.status} {self.started_at:%Y-%m-%d %H:%M}"


class PeopleForceImportIssue(TimestampedModel):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    run = models.ForeignKey(PeopleForceImportRun, on_delete=models.CASCADE, related_name="issues")
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.WARNING)
    entity_type = models.CharField(max_length=80)
    external_id = models.CharField(max_length=160, blank=True)
    message = models.CharField(max_length=500)
    raw_fragment = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["run", "severity"], name="pf_import_issue_run_idx"),
            models.Index(fields=["entity_type", "external_id"], name="pf_import_issue_entity_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.severity} {self.entity_type}:{self.external_id}"


class PeopleForceEntity(TimestampedModel):
    class MappingStatus(models.TextChoices):
        RAW_ONLY = "raw_only", "Raw only"
        MAPPED = "mapped", "Mapped"
        SKIPPED = "skipped", "Skipped"
        ERROR = "error", "Error"

    entity_type = models.CharField(max_length=80)
    external_id = models.CharField(max_length=160)
    endpoint = models.CharField(max_length=240, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    payload_hash = models.CharField(max_length=128, blank=True)
    fetched_at = models.DateTimeField()
    mapping_status = models.CharField(max_length=20, choices=MappingStatus.choices, default=MappingStatus.RAW_ONLY)
    hr_model = models.CharField(max_length=120, blank=True)
    hr_object_id = models.CharField(max_length=120, blank=True)
    last_run = models.ForeignKey(PeopleForceImportRun, on_delete=models.SET_NULL, null=True, blank=True, related_name="entities")

    class Meta:
        ordering = ["entity_type", "external_id"]
        constraints = [
            models.UniqueConstraint(fields=["entity_type", "external_id"], name="uniq_pf_entity_type_external"),
        ]
        indexes = [
            models.Index(fields=["entity_type", "mapping_status"], name="pf_entity_type_status_idx"),
            models.Index(fields=["hr_model", "hr_object_id"], name="pf_entity_hr_object_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.entity_type}:{self.external_id}"


class PeopleForceCompatRequest(TimestampedModel):
    class ProcessedStatus(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"

    method = models.CharField(max_length=12)
    path = models.CharField(max_length=260)
    query_params = models.JSONField(default=dict, blank=True)
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    status_code = models.PositiveSmallIntegerField(default=0)
    processed_status = models.CharField(max_length=20, choices=ProcessedStatus.choices, default=ProcessedStatus.RECEIVED)
    error_message = models.TextField(blank=True)
    payload_hash = models.CharField(max_length=128, blank=True)
    remote_addr = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["method", "path", "-created_at"], name="pfcompat_req_lookup_idx"),
            models.Index(fields=["processed_status", "-created_at"], name="pfcompat_req_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.method} {self.path} {self.status_code}"


class PeopleForceCompatTimesheetEntry(TimestampedModel):
    class Status(models.TextChoices):
        UNSUBMITTED = "unsubmitted", "Unsubmitted"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="peopleforce_compat_timesheet_entries")
    legacy_peopleforce_entry_id = models.CharField(max_length=120, blank=True, db_index=True)
    legacy_peopleforce_employee_id = models.CharField(max_length=120, db_index=True)
    attendance_period = models.OneToOneField(
        AttendancePeriod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="peopleforce_compat_entry",
    )
    request = models.ForeignKey(
        PeopleForceCompatRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timesheet_entries",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    date = models.DateField()
    minutes = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNSUBMITTED)
    entry_type = models.CharField(max_length=40, default="working")
    comment = models.TextField(blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-starts_at", "legacy_peopleforce_employee_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["legacy_peopleforce_employee_id", "starts_at", "ends_at"],
                name="uniq_pfcompat_active_ts_entry",
                condition=models.Q(deleted_at__isnull=True),
            ),
            models.UniqueConstraint(
                fields=["legacy_peopleforce_entry_id"],
                name="uniq_pfcompat_pf_entry_id",
                condition=~models.Q(legacy_peopleforce_entry_id=""),
            ),
        ]
        indexes = [
            models.Index(fields=["legacy_peopleforce_employee_id", "date"], name="pfcompat_ts_emp_date_idx"),
            models.Index(fields=["employee", "date"], name="pfcompat_ts_hr_emp_date_idx"),
            models.Index(fields=["status", "date"], name="pfcompat_ts_status_date_idx"),
            models.Index(fields=["deleted_at"], name="pfcompat_ts_deleted_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.legacy_peopleforce_employee_id} {self.starts_at} - {self.ends_at}"


class PeopleForceWebhookEvent(TimestampedModel):
    """Подія, отримана від PeopleForce через вебхук (push). Лог + диспетчеризація.

    Вебхук слугує тригером: фактичне застосування даних робить
    PeopleForce-importer (light sync), щоб не дублювати мапінг і не залежати
    від точного формату payload.
    """

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        QUEUED = "queued", "Queued"
        SKIPPED = "skipped", "Skipped"
        FAILED = "failed", "Failed"

    topic = models.CharField(max_length=120, blank=True, db_index=True)
    event_id = models.CharField(max_length=120, blank=True, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    headers = models.JSONField(default=dict, blank=True)
    signature_valid = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    error = models.TextField(blank=True)
    remote_addr = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["topic", "-created_at"], name="pfwebhook_topic_time_idx"),
            models.Index(fields=["status", "-created_at"], name="pfwebhook_status_time_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.topic or 'unknown'} @ {self.created_at:%Y-%m-%d %H:%M}"
