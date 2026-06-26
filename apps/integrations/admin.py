from django.contrib import admin

from .models import (
    PeopleForceCompatRequest,
    PeopleForceCompatTimesheetEntry,
    PeopleForceEntity,
    PeopleForceImportIssue,
    PeopleForceImportRun,
)


class PeopleForceImportIssueInline(admin.TabularInline):
    model = PeopleForceImportIssue
    extra = 0
    readonly_fields = ("severity", "entity_type", "external_id", "message", "raw_fragment", "created_at")
    can_delete = False


@admin.register(PeopleForceImportRun)
class PeopleForceImportRunAdmin(admin.ModelAdmin):
    list_display = ("status", "started_at", "finished_at")
    list_filter = ("status",)
    readonly_fields = ("status", "started_at", "finished_at", "counters", "options", "error_message")
    inlines = [PeopleForceImportIssueInline]


@admin.register(PeopleForceEntity)
class PeopleForceEntityAdmin(admin.ModelAdmin):
    list_display = ("entity_type", "external_id", "mapping_status", "hr_model", "hr_object_id", "fetched_at")
    list_filter = ("entity_type", "mapping_status")
    search_fields = ("entity_type", "external_id", "hr_model", "hr_object_id", "endpoint")
    readonly_fields = ("payload", "payload_hash", "fetched_at", "created_at", "updated_at")


@admin.register(PeopleForceCompatRequest)
class PeopleForceCompatRequestAdmin(admin.ModelAdmin):
    list_display = ("method", "path", "status_code", "processed_status", "created_at")
    list_filter = ("method", "processed_status", "status_code")
    search_fields = ("path", "error_message", "payload_hash")
    readonly_fields = (
        "method",
        "path",
        "query_params",
        "request_payload",
        "response_payload",
        "status_code",
        "processed_status",
        "error_message",
        "payload_hash",
        "remote_addr",
        "user_agent",
        "created_at",
        "updated_at",
    )


@admin.register(PeopleForceCompatTimesheetEntry)
class PeopleForceCompatTimesheetEntryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "legacy_peopleforce_entry_id",
        "legacy_peopleforce_employee_id",
        "employee",
        "date",
        "starts_at",
        "ends_at",
        "minutes",
        "status",
        "deleted_at",
    )
    list_filter = ("status", "entry_type", "date", "deleted_at")
    search_fields = (
        "legacy_peopleforce_employee_id",
        "legacy_peopleforce_entry_id",
        "employee__last_name",
        "employee__first_name",
        "comment",
    )
    readonly_fields = ("raw_payload", "created_at", "updated_at")
