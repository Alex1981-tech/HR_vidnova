from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class HolidayPolicy(TimestampedModel):
    name = models.CharField(max_length=180, unique=True)
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    country_code = models.CharField(max_length=8, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active", "name"], name="holiday_policy_active_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class Holiday(TimestampedModel):
    class Recurrence(models.TextChoices):
        NONE = "none", "No recurrence"
        YEARLY = "yearly", "Yearly"

    policy = models.ForeignKey(HolidayPolicy, on_delete=models.PROTECT, related_name="holidays")
    legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    name = models.CharField(max_length=180)
    occurs_on = models.DateField()
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    working = models.BooleanField(default=False)
    compensated_on = models.DateField(null=True, blank=True)
    observed_on = models.DateField(null=True, blank=True)
    recurrence = models.CharField(max_length=20, choices=Recurrence.choices, default=Recurrence.NONE)
    raw_payload = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["occurs_on", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["legacy_peopleforce_id"],
                name="uniq_holiday_peopleforce_id",
                condition=~models.Q(legacy_peopleforce_id=""),
            ),
            models.UniqueConstraint(fields=["policy", "occurs_on", "name"], name="uniq_holiday_policy_date_name"),
        ]
        indexes = [
            models.Index(fields=["policy", "occurs_on"], name="holiday_policy_date_idx"),
            models.Index(fields=["is_active", "occurs_on"], name="holiday_active_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.policy}: {self.name} ({self.occurs_on})"


class Clinic(TimestampedModel):
    name = models.CharField(max_length=160, unique=True)
    code = models.CharField(max_length=40, unique=True)
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    country_code = models.CharField(max_length=8, blank=True)
    address = models.CharField(max_length=260, blank=True)
    holiday_policy_id = models.CharField(max_length=120, blank=True)
    holiday_policy_name = models.CharField(max_length=160, blank=True)
    holiday_policy_ref = models.ForeignKey(
        HolidayPolicy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clinics",
    )
    time_zone = models.CharField(max_length=80, blank=True, default="Kyiv")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class DepartmentLevel(TimestampedModel):
    name = models.CharField(max_length=160, unique=True)
    color = models.CharField(max_length=16, default="#94a3b8")
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Department(TimestampedModel):
    clinic = models.ForeignKey(Clinic, on_delete=models.PROTECT, related_name="departments")
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=60, blank=True)
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="children")
    manager = models.ForeignKey("Employee", on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_departments")
    level = models.ForeignKey(DepartmentLevel, on_delete=models.SET_NULL, null=True, blank=True, related_name="departments")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["clinic__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["clinic", "name"], name="uniq_department_clinic_name"),
        ]
        indexes = [
            models.Index(fields=["clinic", "is_active"], name="department_clinic_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.clinic}: {self.name}"


class Position(TimestampedModel):
    name = models.CharField(max_length=180, unique=True)
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class MedicalSpecialty(TimestampedModel):
    name = models.CharField(max_length=200, unique=True)
    external_fotopacients_id = models.CharField(max_length=120, blank=True, db_index=True)
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "medical specialties"
        indexes = [
            models.Index(fields=["external_fotopacients_id"], name="medical_specialty_ext_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class Division(TimestampedModel):
    name = models.CharField(max_length=180, unique=True)
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class EmploymentType(TimestampedModel):
    name = models.CharField(max_length=160, unique=True)
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class EmployeeFormTemplate(TimestampedModel):
    class FormType(models.TextChoices):
        NEW_HIRE = "new_hire", "New hire"
        PREBOARDING = "preboarding", "Preboarding"
        PEOPLE_DATA_CHANGE = "people_data_change", "People data change"
        SELF_SERVICE = "self_service", "Self service"
        CUSTOM_REQUEST = "custom_request", "Custom request"
        TERMINATION = "termination", "Termination"

    form_type = models.CharField(max_length=40, choices=FormType.choices, db_index=True)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    allow_employee_access = models.BooleanField(default=True)
    workflow_name = models.CharField(max_length=180, blank=True)
    allow_requester_disable_workflow = models.BooleanField(default=False)
    preboarding_form = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hire_form_templates",
    )
    absence_policy_names = models.JSONField(default=list, blank=True)
    sections = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["form_type", "name"]
        indexes = [
            models.Index(fields=["form_type", "is_active"], name="employee_form_type_active_idx"),
            models.Index(fields=["is_active", "name"], name="employee_form_active_name_idx"),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def section_count(self) -> int:
        return len(self.sections or [])


class WorkingPattern(TimestampedModel):
    name = models.CharField(max_length=180, unique=True)
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    monday_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tuesday_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    wednesday_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    thursday_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    friday_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    saturday_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sunday_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    uses_time_range = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    schedule = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active", "name"], name="working_pattern_active_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class ProbationPolicy(TimestampedModel):
    name = models.CharField(max_length=180, unique=True)
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    duration_months = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["is_active", "name"], name="probation_policy_active_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class JobLevel(TimestampedModel):
    name = models.CharField(max_length=160, unique=True)
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name


class Gender(TimestampedModel):
    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=160, unique=True)
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class TerminationReason(TimestampedModel):
    name = models.CharField(max_length=180, unique=True)
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class TerminationType(TimestampedModel):
    name = models.CharField(max_length=180, unique=True)
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Employee(TimestampedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ON_LEAVE = "on_leave", "On leave"
        DISMISSED = "dismissed", "Dismissed"
        SUSPENDED = "suspended", "Suspended"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employee_profile",
    )
    external_baf_id = models.CharField(max_length=120, blank=True, db_index=True)
    external_fotopacients_id = models.CharField(max_length=120, blank=True, db_index=True)
    legacy_peopleforce_id = models.CharField(max_length=80, blank=True, db_index=True)
    employee_number = models.CharField(max_length=80, blank=True, db_index=True)
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    middle_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    personal_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=60, blank=True)
    phone2 = models.CharField(max_length=60, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=40, blank=True)
    avatar_url = models.URLField(blank=True, max_length=1000)
    avatar_file = models.FileField(upload_to="employee_avatars/%Y/%m/", blank=True)
    avatar_source_url = models.CharField(max_length=1000, blank=True)
    avatar_downloaded_at = models.DateTimeField(null=True, blank=True)
    avatar_download_error = models.TextField(blank=True)
    peopleforce_status = models.CharField(max_length=40, blank=True)
    peopleforce_fields = models.JSONField(default=dict, blank=True)
    clinic = models.ForeignKey(Clinic, on_delete=models.PROTECT, null=True, blank=True, related_name="employees")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True, blank=True, related_name="employees")
    position = models.ForeignKey(Position, on_delete=models.PROTECT, null=True, blank=True, related_name="employees")
    division = models.ForeignKey(Division, on_delete=models.PROTECT, null=True, blank=True, related_name="employees")
    employment_type = models.ForeignKey(EmploymentType, on_delete=models.PROTECT, null=True, blank=True, related_name="employees")
    job_level = models.ForeignKey(JobLevel, on_delete=models.PROTECT, null=True, blank=True, related_name="employees")
    medical_specialties = models.ManyToManyField(MedicalSpecialty, blank=True, related_name="employees")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    hired_on = models.DateField(null=True, blank=True)
    dismissed_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["last_name", "first_name", "middle_name"]
        indexes = [
            models.Index(fields=["status", "clinic", "department"], name="employee_scope_status_idx"),
            models.Index(fields=["last_name", "first_name"], name="employee_name_idx"),
            models.Index(fields=["phone"], name="employee_phone_idx"),
            models.Index(fields=["email"], name="employee_email_idx"),
            models.Index(fields=["employee_number"], name="employee_number_idx"),
        ]

    @property
    def full_name(self) -> str:
        return " ".join(part for part in [self.last_name, self.first_name, self.middle_name] if part).strip()

    def __str__(self) -> str:
        return self.full_name


class ManagerAssignment(TimestampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="manager_assignments")
    manager = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="subordinate_assignments")
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)
    is_primary = models.BooleanField(default=True)

    class Meta:
        ordering = ["employee__last_name", "-valid_from"]
        indexes = [
            models.Index(fields=["employee", "valid_from", "valid_to"], name="mgr_employee_period_idx"),
            models.Index(fields=["manager", "valid_from", "valid_to"], name="mgr_manager_period_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.employee} -> {self.manager}"


class EmployeePositionHistory(TimestampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="position_history")
    legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    effective_on = models.DateField(null=True, blank=True)
    position = models.ForeignKey(Position, on_delete=models.PROTECT, null=True, blank=True, related_name="employee_history")
    clinic = models.ForeignKey(Clinic, on_delete=models.PROTECT, null=True, blank=True, related_name="employee_position_history")
    department = models.ForeignKey(Department, on_delete=models.PROTECT, null=True, blank=True, related_name="employee_position_history")
    division = models.ForeignKey(Division, on_delete=models.PROTECT, null=True, blank=True, related_name="employee_position_history")
    job_level = models.ForeignKey(JobLevel, on_delete=models.PROTECT, null=True, blank=True, related_name="employee_position_history")
    manager = models.ForeignKey(Employee, on_delete=models.PROTECT, null=True, blank=True, related_name="managed_position_history")
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["employee", "-effective_on", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "legacy_peopleforce_id"],
                name="uniq_employee_pf_position_history",
                condition=~models.Q(legacy_peopleforce_id=""),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.employee} {self.effective_on or ''} {self.position or ''}".strip()


class EmployeeEmploymentStatus(TimestampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="employment_status_history")
    legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    effective_from = models.DateField(null=True, blank=True)
    employment_type = models.ForeignKey(EmploymentType, on_delete=models.PROTECT, null=True, blank=True, related_name="employee_status_history")
    probation_policy = models.ForeignKey(
        ProbationPolicy,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="employee_status_history",
    )
    working_pattern_name = models.CharField(max_length=180, blank=True)
    probation_policy_name = models.CharField(max_length=180, blank=True)
    comment = models.TextField(blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["employee", "-effective_from", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "legacy_peopleforce_id"],
                name="uniq_employee_pf_employment_status",
                condition=~models.Q(legacy_peopleforce_id=""),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.employee} {self.effective_from or ''} {self.employment_type or ''}".strip()


class Team(TimestampedModel):
    name = models.CharField(max_length=180)
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    description = models.TextField(blank=True)
    lead = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name="led_teams")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["external_peopleforce_id"],
                name="uniq_team_peopleforce_id",
                condition=~models.Q(external_peopleforce_id=""),
            ),
        ]

    def __str__(self) -> str:
        return self.name


class TeamMembership(TimestampedModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="team_memberships")
    external_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["team", "employee"], name="uniq_team_employee_membership"),
        ]

    def __str__(self) -> str:
        return f"{self.team}: {self.employee}"


class EmployeeDocumentFolder(TimestampedModel):
    legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)
    name = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    legacy_payload = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["legacy_peopleforce_id"],
                name="uniq_emp_doc_folder_pf_id",
                condition=~models.Q(legacy_peopleforce_id=""),
            ),
        ]

    def __str__(self) -> str:
        return self.name


class EmployeeDocument(TimestampedModel):
    class DocumentType(models.TextChoices):
        FILE = "file", "File"
        LINK = "link", "Link"
        UNKNOWN = "unknown", "Unknown"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="documents")
    folder = models.ForeignKey(EmployeeDocumentFolder, on_delete=models.SET_NULL, null=True, blank=True, related_name="documents")
    legacy_peopleforce_id = models.CharField(max_length=120, db_index=True)
    name = models.CharField(max_length=240)
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.UNKNOWN)
    source_url = models.URLField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    local_file = models.FileField(upload_to="peopleforce_employee_documents/%Y/%m/", blank=True)
    file_downloaded_at = models.DateTimeField(null=True, blank=True)
    file_download_error = models.TextField(blank=True)
    legacy_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["employee", "name"]
        constraints = [
            models.UniqueConstraint(fields=["employee", "legacy_peopleforce_id"], name="uniq_employee_document_pf_id"),
        ]
        indexes = [
            models.Index(fields=["employee", "document_type"], name="emp_doc_employee_type_idx"),
            models.Index(fields=["folder", "document_type"], name="emp_doc_folder_type_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.employee}: {self.name}"


class ExternalEmployeeLink(TimestampedModel):
    class Source(models.TextChoices):
        BAF = "baf", "BAF"
        FOTOPACIENTS = "fotopacients", "FotoPacients"
        PEOPLEFORCE_LEGACY = "peopleforce_legacy", "PeopleForce legacy"

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="external_links")
    source = models.CharField(max_length=40, choices=Source.choices)
    external_id = models.CharField(max_length=160)
    raw_hash = models.CharField(max_length=128, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["source", "external_id"], name="uniq_external_employee_source_id"),
        ]
        indexes = [
            models.Index(fields=["employee", "source"], name="external_employee_link_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.source}:{self.external_id}"


class EmployeeImportRun(TimestampedModel):
    class Source(models.TextChoices):
        BAF = "baf", "BAF"
        FOTOPACIENTS = "fotopacients", "FotoPacients"
        PEOPLEFORCE_LEGACY = "peopleforce_legacy", "PeopleForce legacy"

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        DRY_RUN = "dry_run", "Dry run"

    source = models.CharField(max_length=40, choices=Source.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    counters = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["source", "status", "-started_at"], name="employee_import_run_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.source} {self.status} {self.started_at:%Y-%m-%d %H:%M}"


class EmployeeImportIssue(TimestampedModel):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"

    run = models.ForeignKey(EmployeeImportRun, on_delete=models.CASCADE, related_name="issues")
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.WARNING)
    external_id = models.CharField(max_length=160, blank=True)
    message = models.CharField(max_length=500)
    raw_fragment = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["run", "severity"], name="employee_import_issue_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.severity}: {self.message}"


class EmployeeFieldGroup(TimestampedModel):
    """Група полів профілю співробітника (напр. Особисте, Контакти) у вкладці."""

    class Tab(models.TextChoices):
        PERSONAL = "personal", "Особисте"
        WORK = "work", "Робота"
        COMPENSATION = "compensation", "Компенсація"

    tab = models.CharField(max_length=20, choices=Tab.choices, default=Tab.PERSONAL, db_index=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=160, blank=True)
    is_system = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["tab", "order", "id"]

    def __str__(self) -> str:
        return f"{self.get_tab_display()}: {self.name}"


class EmployeeField(TimestampedModel):
    """Поле профілю. Системне (мапиться на атрибут Employee через system_key) або
    кастомне (значення зберігається в Employee.custom_fields[str(field.id)])."""

    class FieldType(models.TextChoices):
        SYSTEM = "system", "Система"
        TEXT = "text", "Однорядковий текст"
        TEXTAREA = "textarea", "Текст з багато рядків"
        NUMBER = "number", "Число"
        DATE = "date", "Дата"
        SELECT = "select", "Список"
        EMPLOYEE = "employee", "Вибір співробітника"
        URL = "url", "Посилання"

    group = models.ForeignKey(EmployeeFieldGroup, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=200)
    field_type = models.CharField(max_length=20, choices=FieldType.choices, default=FieldType.TEXT)
    is_system = models.BooleanField(default=False)
    system_key = models.CharField(max_length=80, blank=True, help_text="Атрибут Employee для системних полів")
    is_enabled = models.BooleanField(default=True)
    is_required = models.BooleanField(default=False)
    show_in_summary = models.BooleanField(default=False)
    options = models.JSONField(default=list, blank=True, help_text="Варіанти для типу select")
    help_text = models.CharField(max_length=300, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["group", "order", "id"]

    def __str__(self) -> str:
        return self.name


class EmployeeFieldTable(TimestampedModel):
    """Повторювана таблиця в групі (напр. освіта, сертифікати). Рядки зберігаються
    в Employee.custom_fields['table_<id>'] як список словників по ключах колонок."""

    group = models.ForeignKey(EmployeeFieldGroup, on_delete=models.CASCADE, related_name="tables")
    name = models.CharField(max_length=200)
    columns = models.JSONField(default=list, blank=True, help_text="[{key,label,type}]")
    is_enabled = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["group", "order", "id"]

    def __str__(self) -> str:
        return self.name
