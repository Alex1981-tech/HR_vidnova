from django.contrib import admin

from .models import (
    EmployeeLeavePolicyAssignment,
    LeaveApprovalStep,
    LeaveBalance,
    LeaveLedgerEntry,
    LeavePolicy,
    LeavePolicyAccrualRule,
    LeaveRequest,
    LeaveType,
)


class LeaveApprovalStepInline(admin.TabularInline):
    model = LeaveApprovalStep
    extra = 0


class LeavePolicyAccrualRuleInline(admin.StackedInline):
    model = LeavePolicyAccrualRule
    extra = 0
    max_num = 1


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "legacy_peopleforce_id", "unit", "requires_hr_approval", "is_active")
    search_fields = ("name", "code", "legacy_peopleforce_id")
    list_filter = ("requires_hr_approval", "is_active")


@admin.register(LeavePolicy)
class LeavePolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "leave_type", "policy_type", "activity_type", "counted_as", "is_active")
    list_filter = ("leave_type", "policy_type", "activity_type", "counted_as", "is_active")
    search_fields = ("name", "legacy_peopleforce_id", "leave_type__name")
    inlines = [LeavePolicyAccrualRuleInline]


@admin.register(EmployeeLeavePolicyAssignment)
class EmployeeLeavePolicyAssignmentAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "policy", "effective_on", "ends_on", "initial_balance", "is_active")
    list_filter = ("leave_type", "policy", "is_active")
    search_fields = ("employee__last_name", "employee__first_name", "policy__name", "legacy_peopleforce_id")


@admin.register(LeaveLedgerEntry)
class LeaveLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_type", "policy", "kind", "occurred_on", "amount", "balance_after")
    list_filter = ("leave_type", "policy", "kind")
    search_fields = ("employee__last_name", "employee__first_name", "description", "idempotency_key")
    readonly_fields = ("created_at", "updated_at")


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
