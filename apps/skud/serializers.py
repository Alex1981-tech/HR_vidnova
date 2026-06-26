from rest_framework import serializers

from .models import (
    AccessDevice,
    AccessEvent,
    AccessIdentity,
    AccessSystem,
    IntegrationRun,
    TimeCorrectionRequest,
    WorkDaySummary,
)


class AccessSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessSystem
        fields = ("id", "kind", "name", "is_active", "settings_summary")


class AccessDeviceSerializer(serializers.ModelSerializer):
    system_name = serializers.CharField(source="system.name", read_only=True)

    class Meta:
        model = AccessDevice
        fields = ("id", "system", "system_name", "external_id", "name", "clinic_code", "location", "direction_hint", "is_active")


class AccessIdentitySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    system_name = serializers.CharField(source="system.name", read_only=True)

    class Meta:
        model = AccessIdentity
        fields = (
            "id",
            "employee",
            "employee_name",
            "system",
            "system_name",
            "external_user_id",
            "external_card_code",
            "matched_by",
            "confidence",
            "is_active",
            "valid_from",
            "valid_to",
        )


class AccessEventSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    device_name = serializers.CharField(source="device.name", read_only=True)

    class Meta:
        model = AccessEvent
        fields = ("id", "employee", "employee_name", "device", "device_name", "occurred_at", "direction", "quality")


class WorkDaySummarySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)

    class Meta:
        model = WorkDaySummary
        fields = (
            "id",
            "employee",
            "employee_name",
            "date",
            "planned_minutes",
            "actual_minutes",
            "first_entry_at",
            "last_exit_at",
            "status",
            "exception_count",
            "calculated_at",
            "locked_at",
        )


class TimeCorrectionRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    decided_by_name = serializers.CharField(source="decided_by.get_full_name", read_only=True)

    class Meta:
        model = TimeCorrectionRequest
        fields = (
            "id",
            "employee",
            "employee_name",
            "date",
            "requested_start_at",
            "requested_end_at",
            "reason",
            "status",
            "submitted_at",
            "decided_at",
            "decided_by",
            "decided_by_name",
            "decision_comment",
            "applied_adjustment",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("submitted_at", "decided_at", "created_at", "updated_at")


class IntegrationRunSerializer(serializers.ModelSerializer):
    system_name = serializers.CharField(source="system.name", read_only=True)

    class Meta:
        model = IntegrationRun
        fields = (
            "id",
            "system",
            "system_name",
            "job_name",
            "status",
            "started_at",
            "finished_at",
            "watermark_before",
            "watermark_after",
            "rows_fetched",
            "rows_inserted",
            "rows_ignored",
            "error_summary",
        )
