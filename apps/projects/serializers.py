from rest_framework import serializers

from apps.employees.serializers import EmployeeCompactSerializer

from .models import Project, TimeEntry


class ProjectListSerializer(serializers.ModelSerializer):
    # Анотується у ProjectViewSet.get_queryset через Count("members") — без N+1.
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = ("id", "name", "emoji", "is_archived", "order", "member_count")


class ProjectDetailSerializer(ProjectListSerializer):
    members = EmployeeCompactSerializer(many=True, read_only=True)

    class Meta(ProjectListSerializer.Meta):
        fields = ProjectListSerializer.Meta.fields + (
            "members",
            "created_at",
            "updated_at",
        )


class ProjectWriteSerializer(serializers.ModelSerializer):
    emoji = serializers.CharField(max_length=16, required=False, allow_blank=True)

    class Meta:
        model = Project
        fields = ("id", "name", "emoji", "is_archived")

    def validate_emoji(self, value):
        return (value or "").strip() or "📁"

    def create(self, validated_data):
        if not validated_data.get("order"):
            last = Project.objects.order_by("-order").first()
            validated_data["order"] = (last.order + 1) if last else 1
        return super().create(validated_data)

    def to_representation(self, instance):
        # Після create/update повертаємо повне detail-представлення.
        instance.member_count = instance.members.count()
        return ProjectDetailSerializer(instance, context=self.context).data


class TimeEntrySerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True, default="")
    project_emoji = serializers.CharField(source="project.emoji", read_only=True, default="")
    employee = serializers.IntegerField(source="employee_id", read_only=True)
    employee_name = serializers.CharField(source="employee.full_name", read_only=True, default="")
    duration_seconds = serializers.IntegerField(read_only=True)
    is_running = serializers.BooleanField(read_only=True)

    class Meta:
        model = TimeEntry
        fields = (
            "id",
            "project",
            "project_name",
            "project_emoji",
            "employee",
            "employee_name",
            "comment",
            "started_at",
            "ended_at",
            "duration_seconds",
            "is_running",
        )
        read_only_fields = ("started_at", "ended_at")
