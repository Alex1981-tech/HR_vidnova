from django.contrib import admin

from .models import (
    Clinic,
    Department,
    DepartmentLevel,
    Division,
    Employee,
    EmployeeDocument,
    EmployeeDocumentFolder,
    EmployeeEmploymentStatus,
    EmployeeImportIssue,
    EmployeeImportRun,
    EmployeePositionHistory,
    EmploymentType,
    ExternalEmployeeLink,
    Gender,
    Holiday,
    HolidayPolicy,
    JobLevel,
    ManagerAssignment,
    MedicalSpecialty,
    Position,
    ProbationPolicy,
    Team,
    TeamMembership,
    TerminationReason,
    TerminationType,
    WorkingPattern,
)


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "country_code", "holiday_policy_name", "holiday_policy_ref", "time_zone", "is_active")
    search_fields = ("name", "code", "country_code", "address", "holiday_policy_name")
    list_filter = ("country_code", "holiday_policy_name", "holiday_policy_ref", "time_zone", "is_active")


@admin.register(HolidayPolicy)
class HolidayPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "country_code", "external_peopleforce_id", "is_active")
    search_fields = ("name", "country_code", "external_peopleforce_id")
    list_filter = ("country_code", "is_active")


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ("name", "policy", "occurs_on", "working", "recurrence", "is_active")
    search_fields = ("name", "policy__name", "legacy_peopleforce_id")
    list_filter = ("policy", "working", "recurrence", "is_active")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "clinic", "parent", "manager", "level", "is_active")
    search_fields = ("name", "code", "clinic__name", "manager__last_name", "manager__first_name", "level__name")
    list_filter = ("clinic", "level", "is_active")


@admin.register(DepartmentLevel)
class DepartmentLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "color", "external_peopleforce_id", "is_active")
    search_fields = ("name", "external_peopleforce_id")
    list_filter = ("is_active",)


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ("name", "external_peopleforce_id", "is_active")
    search_fields = ("name", "external_peopleforce_id")
    list_filter = ("is_active",)


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ("name", "external_peopleforce_id", "is_active")
    search_fields = ("name", "external_peopleforce_id")
    list_filter = ("is_active",)


@admin.register(EmploymentType)
class EmploymentTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "external_peopleforce_id", "is_active")
    search_fields = ("name", "external_peopleforce_id")
    list_filter = ("is_active",)


@admin.register(WorkingPattern)
class WorkingPatternAdmin(admin.ModelAdmin):
    list_display = ("name", "external_peopleforce_id", "is_default", "is_active")
    search_fields = ("name", "external_peopleforce_id")
    list_filter = ("is_default", "is_active")


@admin.register(ProbationPolicy)
class ProbationPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_months", "external_peopleforce_id", "is_active")
    search_fields = ("name", "external_peopleforce_id")
    list_filter = ("is_active",)


@admin.register(JobLevel)
class JobLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "external_peopleforce_id", "is_active")
    search_fields = ("name", "external_peopleforce_id")
    list_filter = ("is_active",)


@admin.register(Gender)
class GenderAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "external_peopleforce_id", "is_active")
    search_fields = ("name", "code", "external_peopleforce_id")
    list_filter = ("is_active",)


@admin.register(TerminationReason)
class TerminationReasonAdmin(admin.ModelAdmin):
    list_display = ("name", "external_peopleforce_id", "is_active")
    search_fields = ("name", "external_peopleforce_id")
    list_filter = ("is_active",)


@admin.register(TerminationType)
class TerminationTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "external_peopleforce_id", "is_active")
    search_fields = ("name", "external_peopleforce_id")
    list_filter = ("is_active",)


@admin.register(MedicalSpecialty)
class MedicalSpecialtyAdmin(admin.ModelAdmin):
    list_display = ("name", "external_fotopacients_id", "external_peopleforce_id", "is_active")
    search_fields = ("name", "external_fotopacients_id", "external_peopleforce_id")
    list_filter = ("is_active",)


class ExternalEmployeeLinkInline(admin.TabularInline):
    model = ExternalEmployeeLink
    extra = 0


class EmployeePositionHistoryInline(admin.TabularInline):
    model = EmployeePositionHistory
    fk_name = "employee"
    extra = 0


class EmployeeEmploymentStatusInline(admin.TabularInline):
    model = EmployeeEmploymentStatus
    extra = 0


class EmployeeDocumentInline(admin.TabularInline):
    model = EmployeeDocument
    extra = 0
    fields = ("name", "folder", "document_type", "source_url", "local_file", "expires_at", "file_downloaded_at")
    readonly_fields = ("source_url", "local_file", "expires_at", "file_downloaded_at")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("full_name", "status", "clinic", "department", "position", "email", "phone", "avatar_downloaded_at")
    search_fields = (
        "last_name",
        "first_name",
        "middle_name",
        "email",
        "personal_email",
        "phone",
        "employee_number",
        "external_baf_id",
        "external_fotopacients_id",
        "legacy_peopleforce_id",
    )
    list_filter = ("status", "clinic", "department", "position", "division", "employment_type", "job_level", "medical_specialties")
    filter_horizontal = ("medical_specialties",)
    readonly_fields = ("avatar_file", "avatar_source_url", "avatar_downloaded_at", "avatar_download_error")
    inlines = [ExternalEmployeeLinkInline, EmployeePositionHistoryInline, EmployeeEmploymentStatusInline, EmployeeDocumentInline]


@admin.register(ManagerAssignment)
class ManagerAssignmentAdmin(admin.ModelAdmin):
    list_display = ("employee", "manager", "valid_from", "valid_to", "is_primary")
    search_fields = ("employee__last_name", "manager__last_name")
    list_filter = ("is_primary",)


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "external_peopleforce_id", "lead", "is_active")
    search_fields = ("name", "external_peopleforce_id", "lead__last_name", "lead__first_name")
    list_filter = ("is_active",)
    inlines = [TeamMembershipInline]


@admin.register(EmployeeDocumentFolder)
class EmployeeDocumentFolderAdmin(admin.ModelAdmin):
    list_display = ("name", "legacy_peopleforce_id", "is_active")
    search_fields = ("name", "legacy_peopleforce_id")
    list_filter = ("is_active",)
    readonly_fields = ("legacy_payload", "created_at", "updated_at")


@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ("employee", "name", "document_type", "folder", "expires_at", "file_downloaded_at")
    search_fields = ("employee__last_name", "employee__first_name", "name", "legacy_peopleforce_id")
    list_filter = ("document_type", "folder", "file_downloaded_at")
    readonly_fields = ("source_url", "local_file", "file_downloaded_at", "file_download_error", "legacy_payload", "created_at", "updated_at")


class EmployeeImportIssueInline(admin.TabularInline):
    model = EmployeeImportIssue
    extra = 0
    readonly_fields = ("severity", "external_id", "message", "raw_fragment", "created_at")
    can_delete = False


@admin.register(EmployeeImportRun)
class EmployeeImportRunAdmin(admin.ModelAdmin):
    list_display = ("source", "status", "started_at", "finished_at")
    search_fields = ("source", "status", "error_message")
    list_filter = ("source", "status")
    readonly_fields = ("source", "status", "started_at", "finished_at", "counters", "error_message")
    inlines = [EmployeeImportIssueInline]
