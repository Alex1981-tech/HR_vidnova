from rest_framework import serializers

from apps.employees.models import Employee
from apps.knowledge.models import KnowledgeCategory, KnowledgeDocument
from apps.leave.models import LeaveRequest, LeaveType
from apps.skud.models import AccessEvent, TimeCorrectionRequest, WorkDaySummary


class SelfEmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    avatar_local_url = serializers.SerializerMethodField()
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    position_name = serializers.CharField(source="position.name", read_only=True)

    def get_avatar_local_url(self, obj):
        if not obj.avatar_file:
            return ""
        try:
            url = obj.avatar_file.url
        except ValueError:
            return ""
        version = getattr(obj, "avatar_downloaded_at", None) or getattr(obj, "updated_at", None)
        if version is not None:
            try:
                return f"{url}?v={int(version.timestamp())}"
            except (AttributeError, ValueError, OSError):
                return url
        return url

    class Meta:
        model = Employee
        fields = (
            "id",
            "full_name",
            "avatar_local_url",
            "first_name",
            "last_name",
            "middle_name",
            "email",
            "phone",
            "phone2",
            "clinic_name",
            "department_name",
            "position_name",
            "status",
            "hired_on",
        )


class SelfWorkDaySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkDaySummary
        fields = (
            "id",
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


class SelfAccessEventSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    class Meta:
        model = AccessEvent
        fields = ("id", "device_name", "occurred_at", "direction", "quality")


class SelfTimeCorrectionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeCorrectionRequest
        fields = (
            "id",
            "date",
            "requested_start_at",
            "requested_end_at",
            "reason",
            "status",
            "submitted_at",
            "decided_at",
            "decision_comment",
            "created_at",
        )
        read_only_fields = ("id", "status", "submitted_at", "decided_at", "decision_comment", "created_at")

    def validate(self, attrs):
        start_at = attrs.get("requested_start_at")
        end_at = attrs.get("requested_end_at")
        work_date = attrs.get("date")

        if start_at and work_date and start_at.date() != work_date:
            raise serializers.ValidationError({"requested_start_at": "Дата начала должна совпадать с датой заявки."})
        if end_at and work_date and end_at.date() != work_date:
            raise serializers.ValidationError({"requested_end_at": "Дата окончания должна совпадать с датой заявки."})
        if start_at and end_at and end_at <= start_at:
            raise serializers.ValidationError({"requested_end_at": "Окончание должно быть позже начала."})
        if not attrs.get("reason", "").strip():
            raise serializers.ValidationError({"reason": "Укажите причину исправления."})
        return attrs

    def create(self, validated_data):
        return TimeCorrectionRequest.objects.create(
            employee=self.context["employee"],
            submitted_at=self.context["submitted_at"],
            status=TimeCorrectionRequest.Status.SUBMITTED,
            **validated_data,
        )


class SelfLeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ("id", "name", "code", "requires_hr_approval")


class SelfLeaveRequestSerializer(serializers.ModelSerializer):
    leave_type = serializers.PrimaryKeyRelatedField(queryset=LeaveType.objects.filter(is_active=True))
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = (
            "id",
            "leave_type",
            "leave_type_name",
            "date_from",
            "date_to",
            "reason",
            "status",
            "submitted_at",
            "decided_at",
            "created_at",
        )
        read_only_fields = ("id", "leave_type_name", "status", "submitted_at", "decided_at", "created_at")

    def validate(self, attrs):
        if attrs["date_to"] < attrs["date_from"]:
            raise serializers.ValidationError({"date_to": "Дата окончания не может быть раньше даты начала."})
        return attrs

    def create(self, validated_data):
        return LeaveRequest.objects.create(
            employee=self.context["employee"],
            submitted_at=self.context["submitted_at"],
            status=LeaveRequest.Status.SUBMITTED,
            **validated_data,
        )


class SelfKnowledgeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeCategory
        fields = ("id", "name", "slug", "parent")


class SelfKnowledgeDocumentSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = KnowledgeDocument
        fields = ("id", "category", "category_name", "title", "slug", "summary", "body", "tags", "published_at", "updated_at")
