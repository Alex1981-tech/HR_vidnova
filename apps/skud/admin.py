from django.contrib import admin

from .models import (
    AccessDevice,
    AccessEvent,
    AccessEventRaw,
    AccessIdentity,
    AccessSystem,
    AttendancePeriod,
    IntegrationRun,
    TimeAdjustment,
    TimeCorrectionRequest,
    WorkDaySummary,
)


@admin.register(AccessSystem)
class AccessSystemAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "is_active")
    list_filter = ("kind", "is_active")


@admin.register(AccessDevice)
class AccessDeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "system", "external_id", "clinic_code", "is_active")
    list_filter = ("system", "is_active", "clinic_code")
    search_fields = ("name", "external_id")


@admin.register(AccessIdentity)
class AccessIdentityAdmin(admin.ModelAdmin):
    list_display = ("employee", "system", "external_user_id", "confidence", "is_active")
    list_filter = ("system", "confidence", "is_active")
    search_fields = ("employee__last_name", "external_user_id", "external_card_code")


@admin.register(AccessEventRaw)
class AccessEventRawAdmin(admin.ModelAdmin):
    list_display = ("system", "source_event_id", "occurred_at", "raw_user_id", "raw_device_name")
    list_filter = ("system",)
    search_fields = ("source_event_id", "raw_user_id", "raw_user_name", "raw_device_name")


@admin.register(AccessEvent)
class AccessEventAdmin(admin.ModelAdmin):
    list_display = ("employee", "occurred_at", "direction", "quality", "device")
    list_filter = ("direction", "quality", "device")
    search_fields = ("employee__last_name", "raw_event__source_event_id")


@admin.register(IntegrationRun)
class IntegrationRunAdmin(admin.ModelAdmin):
    list_display = ("system", "job_name", "status", "started_at", "finished_at", "rows_inserted", "rows_ignored")
    list_filter = ("system", "job_name", "status")


@admin.register(AttendancePeriod)
class AttendancePeriodAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "start_at", "end_at", "duration_minutes", "period_type")
    list_filter = ("date", "period_type")
    search_fields = ("employee__last_name",)


@admin.register(WorkDaySummary)
class WorkDaySummaryAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "status", "actual_minutes", "exception_count")
    list_filter = ("date", "status")
    search_fields = ("employee__last_name",)


@admin.register(TimeAdjustment)
class TimeAdjustmentAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "author", "created_at")
    search_fields = ("employee__last_name", "reason")


@admin.register(TimeCorrectionRequest)
class TimeCorrectionRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "date", "status", "submitted_at", "decided_at", "decided_by")
    list_filter = ("status", "date")
    search_fields = ("employee__last_name", "employee__first_name", "reason", "decision_comment")
