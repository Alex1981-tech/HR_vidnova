from rest_framework import serializers

from .models import LeaveApprovalStep, LeaveBalance, LeaveRequest, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = (
            "id",
            "name",
            "code",
            "legacy_peopleforce_id",
            "unit",
            "color",
            "requires_hr_approval",
            "is_active",
        )


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = (
            "id",
            "employee",
            "employee_name",
            "leave_type",
            "leave_type_name",
            "legacy_peopleforce_id",
            "effective_on",
            "balance",
            "policy_name",
            "policy_activity_type",
            "policy_counted_as",
        )


class LeaveApprovalStepSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(source="approver.get_full_name", read_only=True)

    class Meta:
        model = LeaveApprovalStep
        fields = ("id", "approver", "approver_name", "order", "status", "decided_at", "comment")


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    approval_steps = LeaveApprovalStepSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = (
            "id",
            "employee",
            "legacy_peopleforce_id",
            "employee_name",
            "leave_type",
            "leave_type_name",
            "date_from",
            "date_to",
            "reason",
            "amount",
            "tracking_time_in",
            "status",
            "submitted_at",
            "decided_at",
            "decided_by",
            "approval_steps",
        )
