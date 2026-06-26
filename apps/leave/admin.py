from django.contrib import admin

from .models import LeaveApprovalStep, LeaveBalance, LeaveRequest, LeaveType


class LeaveApprovalStepInline(admin.TabularInline):
    model = LeaveApprovalStep
    extra = 0


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "legacy_peopleforce_id", "unit", "requires_hr_approval", "is_active")
    search_fields = ("name", "code", "legacy_peopleforce_id")
    list_filter = ("requires_hr_approval", "is_active")


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "date_from", "date_to", "status", "legacy_peopleforce_id")
    list_filter = ("status", "leave_type")
    search_fields = ("employee__last_name", "reason", "legacy_peopleforce_id")
    inlines = [LeaveApprovalStepInline]


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "balance", "effective_on", "legacy_peopleforce_id")
    search_fields = ("employee__last_name", "employee__first_name", "leave_type__name", "legacy_peopleforce_id")
    list_filter = ("leave_type",)
