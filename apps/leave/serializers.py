from django.utils.text import slugify
from rest_framework import serializers

from .models import LeaveApprovalStep, LeaveBalance, LeaveRequest, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    # code генерується автоматично з імені, якщо не передано (модалка має лише Ім'я).
    code = serializers.CharField(max_length=40, required=False, allow_blank=True)
    # unit приймає legacy-значення й нормалізується у validate_unit (не ChoiceField).
    unit = serializers.CharField(max_length=40, required=False, allow_blank=True)

    class Meta:
        model = LeaveType
        fields = (
            "id",
            "name",
            "code",
            "legacy_peopleforce_id",
            "unit",
            "icon",
            "color",
            "order",
            "requires_hr_approval",
            "is_active",
        )
        read_only_fields = ("legacy_peopleforce_id", "order")

    def validate_unit(self, value):
        """Нормалізує одиницю відстеження до days|hours; legacy-значення мапляться за префіксом."""
        raw = (value or "").strip().lower()
        if not raw:
            return LeaveType.TrackingUnit.DAYS
        if raw.startswith("hour") or raw.startswith("год"):
            return LeaveType.TrackingUnit.HOURS
        if raw.startswith("day") or raw.startswith("дн") or raw.startswith("ден"):
            return LeaveType.TrackingUnit.DAYS
        raise serializers.ValidationError("Одиниця має бути «days» або «hours».")

    def _unique_code(self, base, instance=None):
        slug = (slugify(base) or "leave")[:36]
        candidate = slug
        suffix = 1
        qs = LeaveType.objects.all()
        if instance is not None:
            qs = qs.exclude(pk=instance.pk)
        while qs.filter(code=candidate).exists():
            suffix += 1
            candidate = f"{slug}-{suffix}"[:40]
        return candidate

    def create(self, validated_data):
        code = (validated_data.get("code") or "").strip()
        if not code:
            validated_data["code"] = self._unique_code(validated_data.get("name", ""))
        if "order" not in validated_data:
            last = LeaveType.objects.order_by("-order").first()
            validated_data["order"] = (last.order + 1) if last else 1
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "code" in validated_data and not (validated_data["code"] or "").strip():
            validated_data.pop("code")
        return super().update(instance, validated_data)


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
