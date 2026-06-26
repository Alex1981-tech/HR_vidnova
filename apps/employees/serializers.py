from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Clinic,
    Department,
    DepartmentLevel,
    Division,
    Employee,
    EmployeeDocument,
    EmployeeDocumentFolder,
    EmployeeEmploymentStatus,
    EmployeeFormTemplate,
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


class ClinicSerializer(serializers.ModelSerializer):
    code = serializers.CharField(required=False, allow_blank=True)
    country_name = serializers.SerializerMethodField()
    employee_count = serializers.IntegerField(read_only=True)
    holiday_policy_ref_name = serializers.CharField(source="holiday_policy_ref.name", read_only=True)

    class Meta:
        model = Clinic
        fields = (
            "id",
            "name",
            "code",
            "external_peopleforce_id",
            "country_code",
            "country_name",
            "address",
            "holiday_policy_id",
            "holiday_policy_name",
            "holiday_policy_ref",
            "holiday_policy_ref_name",
            "time_zone",
            "is_active",
            "employee_count",
        )
        extra_kwargs = {
            "holiday_policy_ref": {"required": False, "allow_null": True},
        }

    def create(self, validated_data):
        if not validated_data.get("code"):
            base = "".join(ch.lower() if ch.isalnum() else "-" for ch in validated_data["name"]).strip("-") or "location"
            code = base[:36]
            suffix = 1
            candidate = code
            while Clinic.objects.filter(code=candidate).exists():
                suffix += 1
                candidate = f"{code[:32]}-{suffix}"
            validated_data["code"] = candidate[:40]
        return super().create(validated_data)

    def get_country_name(self, obj):
        if obj.country_code == "UA":
            return "Україна"
        if obj.country_code == "PL":
            return "Польща"
        if obj.country_code == "GB":
            return "Велика Британія"
        if obj.country_code == "US":
            return "США"
        return obj.country_code


class HolidayPolicySerializer(serializers.ModelSerializer):
    country_name = serializers.SerializerMethodField()
    location_count = serializers.IntegerField(read_only=True)
    holiday_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = HolidayPolicy
        fields = (
            "id",
            "name",
            "external_peopleforce_id",
            "country_code",
            "country_name",
            "is_active",
            "location_count",
            "holiday_count",
        )
        extra_kwargs = {
            "external_peopleforce_id": {"required": False, "allow_blank": True},
            "country_code": {"required": False, "allow_blank": True},
        }

    def get_country_name(self, obj):
        country_names = {
            "UA": "Україна",
            "PL": "Польща",
            "GB": "Велика Британія",
            "US": "США",
        }
        return country_names.get(obj.country_code, obj.country_code)


class HolidaySerializer(serializers.ModelSerializer):
    policy_name = serializers.CharField(source="policy.name", read_only=True)

    class Meta:
        model = Holiday
        fields = (
            "id",
            "policy",
            "policy_name",
            "legacy_peopleforce_id",
            "name",
            "occurs_on",
            "starts_on",
            "ends_on",
            "working",
            "compensated_on",
            "observed_on",
            "recurrence",
            "is_active",
        )
        extra_kwargs = {
            "legacy_peopleforce_id": {"required": False, "allow_blank": True},
            "starts_on": {"required": False, "allow_null": True},
            "ends_on": {"required": False, "allow_null": True},
            "compensated_on": {"required": False, "allow_null": True},
            "observed_on": {"required": False, "allow_null": True},
            "recurrence": {"required": False},
        }

    def validate(self, attrs):
        occurs_on = attrs.get("occurs_on", self.instance.occurs_on if self.instance else None)
        starts_on = attrs.get("starts_on", self.instance.starts_on if self.instance else None)
        ends_on = attrs.get("ends_on", self.instance.ends_on if self.instance else None)
        if starts_on and ends_on and ends_on < starts_on:
            raise serializers.ValidationError({"ends_on": "End date cannot be before start date."})
        if not starts_on and occurs_on:
            attrs["starts_on"] = occurs_on
        if not ends_on and (attrs.get("starts_on") or starts_on or occurs_on):
            attrs["ends_on"] = attrs.get("starts_on") or starts_on or occurs_on
        return attrs


class DepartmentSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True)
    level_name = serializers.CharField(source="level.name", read_only=True)
    level_color = serializers.CharField(source="level.color", read_only=True)
    employee_count = serializers.IntegerField(read_only=True)
    children_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = (
            "id",
            "clinic",
            "clinic_name",
            "parent",
            "parent_name",
            "manager",
            "manager_name",
            "level",
            "level_name",
            "level_color",
            "name",
            "code",
            "external_peopleforce_id",
            "is_active",
            "employee_count",
            "children_count",
        )
        extra_kwargs = {
            "clinic": {"required": False, "allow_null": True},
            "code": {"required": False, "allow_blank": True},
            "parent": {"required": False, "allow_null": True},
            "manager": {"required": False, "allow_null": True},
            "level": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        parent = attrs.get("parent", self.instance.parent if self.instance else None)
        if self.instance and parent and parent.pk == self.instance.pk:
            raise serializers.ValidationError({"parent": "Department cannot be its own parent."})
        current = parent
        while self.instance and current:
            if current.parent_id == self.instance.pk:
                raise serializers.ValidationError({"parent": "Department parent would create a cycle."})
            current = current.parent
        return attrs

    def _default_clinic(self):
        clinic = (
            Clinic.objects.exclude(code="peopleforce")
            .filter(is_active=True)
            .annotate(active_employees=Count("employees", filter=Q(employees__status=Employee.Status.ACTIVE)))
            .order_by("-active_employees", "name")
            .first()
        )
        clinic = clinic or Clinic.objects.exclude(code="peopleforce").order_by("name").first()
        if clinic:
            return clinic
        return Clinic.objects.create(code="peopleforce", name="PeopleForce import", is_active=True)

    def _ensure_code(self, validated_data):
        if validated_data.get("code"):
            return
        base = "".join(ch.lower() if ch.isalnum() else "-" for ch in validated_data["name"]).strip("-") or "department"
        code = base[:52]
        suffix = 1
        candidate = code
        clinic = validated_data.get("clinic")
        qs = Department.objects.filter(clinic=clinic)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        while qs.filter(code=candidate).exists():
            suffix += 1
            candidate = f"{code[:48]}-{suffix}"
        validated_data["code"] = candidate[:60]

    def create(self, validated_data):
        if not validated_data.get("clinic"):
            validated_data["clinic"] = self._default_clinic()
        self._ensure_code(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if not validated_data.get("clinic") and instance.clinic_id:
            validated_data["clinic"] = instance.clinic
        self._ensure_code(validated_data)
        return super().update(instance, validated_data)


class DepartmentLevelSerializer(serializers.ModelSerializer):
    department_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = DepartmentLevel
        fields = ("id", "name", "color", "external_peopleforce_id", "is_active", "department_count")
        extra_kwargs = {
            "color": {"required": False},
        }


class PositionSerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Position
        fields = ("id", "name", "external_peopleforce_id", "is_active", "employee_count")


class DivisionSerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Division
        fields = ("id", "name", "external_peopleforce_id", "is_active", "employee_count")


class EmploymentTypeSerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = EmploymentType
        fields = ("id", "name", "external_peopleforce_id", "is_active", "employee_count")


class EmployeeFormTemplateSerializer(serializers.ModelSerializer):
    form_type_label = serializers.CharField(source="get_form_type_display", read_only=True)
    preboarding_form_name = serializers.CharField(source="preboarding_form.name", read_only=True)
    section_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = EmployeeFormTemplate
        fields = (
            "id",
            "form_type",
            "form_type_label",
            "name",
            "description",
            "allow_employee_access",
            "workflow_name",
            "allow_requester_disable_workflow",
            "preboarding_form",
            "preboarding_form_name",
            "absence_policy_names",
            "sections",
            "section_count",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")
        extra_kwargs = {
            "description": {"required": False, "allow_blank": True},
            "workflow_name": {"required": False, "allow_blank": True},
            "absence_policy_names": {"required": False},
            "sections": {"required": False},
            "preboarding_form": {"required": False, "allow_null": True},
        }

    def validate_sections(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Sections must be a list.")
        for index, section in enumerate(value, start=1):
            if not isinstance(section, dict):
                raise serializers.ValidationError(f"Section {index} must be an object.")
            if not str(section.get("name", "")).strip():
                raise serializers.ValidationError(f"Section {index} must have a name.")
            fields = section.get("fields", [])
            if fields is None:
                section["fields"] = []
                continue
            if not isinstance(fields, list):
                raise serializers.ValidationError(f"Section {index} fields must be a list.")
        return value

    def validate_absence_policy_names(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Absence policies must be a list.")
        return [str(item).strip() for item in value if str(item).strip()]

    def validate(self, attrs):
        preboarding_form = attrs.get("preboarding_form")
        if self.instance and preboarding_form and preboarding_form.pk == self.instance.pk:
            raise serializers.ValidationError({"preboarding_form": "Form cannot reference itself."})
        return attrs


class WorkingPatternSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkingPattern
        fields = (
            "id",
            "name",
            "external_peopleforce_id",
            "monday_hours",
            "tuesday_hours",
            "wednesday_hours",
            "thursday_hours",
            "friday_hours",
            "saturday_hours",
            "sunday_hours",
            "uses_time_range",
            "is_default",
            "schedule",
            "is_active",
        )
        extra_kwargs = {
            "schedule": {"required": False},
        }


class ProbationPolicySerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ProbationPolicy
        fields = ("id", "name", "external_peopleforce_id", "duration_months", "is_active", "employee_count")


class JobLevelSerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = JobLevel
        fields = ("id", "name", "external_peopleforce_id", "sort_order", "is_active", "employee_count")


class GenderSerializer(serializers.ModelSerializer):
    code = serializers.CharField(required=False, allow_blank=True)
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Gender
        fields = ("id", "code", "name", "external_peopleforce_id", "is_active", "employee_count")

    def create(self, validated_data):
        if not validated_data.get("code"):
            validated_data["code"] = validated_data["name"].strip()
        return super().create(validated_data)

    def get_employee_count(self, obj):
        return Employee.objects.filter(gender=obj.code, status=Employee.Status.ACTIVE).count()


class TerminationReasonSerializer(serializers.ModelSerializer):
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = TerminationReason
        fields = ("id", "name", "external_peopleforce_id", "is_active", "employee_count")

    def get_employee_count(self, obj):
        return 0


class TerminationTypeSerializer(serializers.ModelSerializer):
    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = TerminationType
        fields = ("id", "name", "external_peopleforce_id", "is_active", "employee_count")

    def get_employee_count(self, obj):
        return 0


class MedicalSpecialtySerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MedicalSpecialty
        fields = ("id", "name", "external_fotopacients_id", "external_peopleforce_id", "is_active", "employee_count")


class ExternalEmployeeLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalEmployeeLink
        fields = ("id", "source", "external_id", "raw_hash", "last_seen_at", "is_active")


class EmployeeDocumentFolderSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDocumentFolder
        fields = ("id", "legacy_peopleforce_id", "name", "description", "is_active")


class EmployeeDocumentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    folder_name = serializers.CharField(source="folder.name", read_only=True)

    class Meta:
        model = EmployeeDocument
        fields = (
            "id",
            "employee",
            "employee_name",
            "folder",
            "folder_name",
            "legacy_peopleforce_id",
            "name",
            "document_type",
            "source_url",
            "expires_at",
            "local_file",
            "file_downloaded_at",
            "file_download_error",
        )
        read_only_fields = ("local_file", "file_downloaded_at", "file_download_error")


class EmployeeCompactSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    avatar_local_url = serializers.SerializerMethodField()
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    position_name = serializers.CharField(source="position.name", read_only=True)
    division_name = serializers.CharField(source="division.name", read_only=True)
    direct_reports_count = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = (
            "id",
            "first_name",
            "last_name",
            "middle_name",
            "full_name",
            "email",
            "personal_email",
            "phone",
            "phone2",
            "avatar_url",
            "avatar_local_url",
            "status",
            "gender",
            "birth_date",
            "clinic_name",
            "department_name",
            "position_name",
            "division_name",
            "direct_reports_count",
        )

    def get_avatar_local_url(self, obj):
        if not obj.avatar_file:
            return ""
        try:
            url = obj.avatar_file.url
        except ValueError:
            return ""
        # Cache-busting version so stale CDN/browser-cached 404s (from before a
        # media sync) are bypassed, and avatar changes invalidate the cache.
        version = getattr(obj, "avatar_downloaded_at", None) or getattr(obj, "updated_at", None)
        if version is not None:
            try:
                return f"{url}?v={int(version.timestamp())}"
            except (AttributeError, ValueError, OSError):
                return url
        return url

    def get_direct_reports_count(self, obj):
        annotated = getattr(obj, "direct_reports_count", None)
        if annotated is not None:
            return annotated
        today = timezone.localdate()
        return obj.subordinate_assignments.filter(
            is_primary=True,
            valid_from__lte=today,
        ).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today)).count()


class TeamSerializer(serializers.ModelSerializer):
    lead_name = serializers.CharField(source="lead.full_name", read_only=True)
    lead_profile = EmployeeCompactSerializer(source="lead", read_only=True)
    member_count = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    member_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "external_peopleforce_id",
            "description",
            "lead",
            "lead_name",
            "lead_profile",
            "member_count",
            "members",
            "member_ids",
            "is_active",
        )
        extra_kwargs = {
            "external_peopleforce_id": {"required": False, "allow_blank": True},
            "description": {"required": False, "allow_blank": True},
            "lead": {"required": False, "allow_null": True},
        }

    def get_members(self, obj):
        memberships = [membership for membership in obj.memberships.all() if membership.is_active]
        employees = [membership.employee for membership in memberships if membership.employee.status == Employee.Status.ACTIVE]
        return EmployeeCompactSerializer(employees, many=True, context=self.context).data

    def get_member_count(self, obj):
        annotated = getattr(obj, "member_count", None)
        if annotated is not None:
            return annotated
        return obj.memberships.filter(is_active=True, employee__status=Employee.Status.ACTIVE).count()

    def _sync_members(self, team, member_ids):
        if member_ids is None:
            return
        active_ids = set(
            Employee.objects.filter(id__in=member_ids, status=Employee.Status.ACTIVE).values_list("id", flat=True)
        )
        TeamMembership.objects.filter(team=team).exclude(employee_id__in=active_ids).update(is_active=False)
        for employee_id in active_ids:
            TeamMembership.objects.update_or_create(
                team=team,
                employee_id=employee_id,
                defaults={"is_active": True},
            )

    def create(self, validated_data):
        member_ids = validated_data.pop("member_ids", None)
        team = super().create(validated_data)
        self._sync_members(team, member_ids)
        return team

    def update(self, instance, validated_data):
        member_ids = validated_data.pop("member_ids", None)
        team = super().update(instance, validated_data)
        self._sync_members(team, member_ids)
        return team


class EmployeeHireSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=120)
    last_name = serializers.CharField(max_length=120)
    middle_name = serializers.CharField(max_length=120, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    personal_email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=60, required=False, allow_blank=True)
    phone2 = serializers.CharField(max_length=60, required=False, allow_blank=True)
    birth_date = serializers.DateField(required=False, allow_null=True)
    gender = serializers.CharField(max_length=40, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Employee.Status.choices, default=Employee.Status.ACTIVE)
    hired_on = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    clinic = serializers.PrimaryKeyRelatedField(queryset=Clinic.objects.all(), required=False, allow_null=True)
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all(), required=False, allow_null=True)
    position = serializers.PrimaryKeyRelatedField(queryset=Position.objects.all(), required=False, allow_null=True)
    division = serializers.PrimaryKeyRelatedField(queryset=Division.objects.all(), required=False, allow_null=True)
    employment_type = serializers.PrimaryKeyRelatedField(queryset=EmploymentType.objects.all(), required=False, allow_null=True)
    job_level = serializers.PrimaryKeyRelatedField(queryset=JobLevel.objects.all(), required=False, allow_null=True)
    medical_specialties = serializers.PrimaryKeyRelatedField(
        queryset=MedicalSpecialty.objects.all(),
        many=True,
        required=False,
    )
    manager = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.filter(status=Employee.Status.ACTIVE),
        required=False,
        allow_null=True,
    )
    working_pattern = serializers.PrimaryKeyRelatedField(
        queryset=WorkingPattern.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    probation_policy = serializers.PrimaryKeyRelatedField(
        queryset=ProbationPolicy.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )

    def validate(self, attrs):
        hired_on = attrs.get("hired_on")
        birth_date = attrs.get("birth_date")
        if hired_on and birth_date and birth_date > hired_on:
            raise serializers.ValidationError({"birth_date": "Birth date cannot be after hire date."})
        return attrs

    def create(self, validated_data):
        manager = validated_data.pop("manager", None)
        working_pattern = validated_data.pop("working_pattern", None)
        probation_policy = validated_data.pop("probation_policy", None)
        medical_specialties = validated_data.pop("medical_specialties", [])
        valid_from = validated_data.get("hired_on") or timezone.localdate()

        with transaction.atomic():
            employee = Employee.objects.create(**validated_data)
            if medical_specialties:
                employee.medical_specialties.set(medical_specialties)
            if manager and manager.pk != employee.pk:
                ManagerAssignment.objects.update_or_create(
                    employee=employee,
                    manager=manager,
                    valid_from=valid_from,
                    defaults={"is_primary": True},
                )
            if employee.employment_type_id or working_pattern or probation_policy:
                EmployeeEmploymentStatus.objects.create(
                    employee=employee,
                    effective_from=valid_from,
                    employment_type=employee.employment_type,
                    probation_policy=probation_policy,
                    working_pattern_name=working_pattern.name if working_pattern else "",
                    probation_policy_name=probation_policy.name if probation_policy else "",
                    raw_payload={"source": "hr_vidnova_new_hire_form"},
                )
        return employee


class EmployeeSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    avatar_local_url = serializers.SerializerMethodField()
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    position_name = serializers.CharField(source="position.name", read_only=True)
    division_name = serializers.CharField(source="division.name", read_only=True)
    employment_type_name = serializers.CharField(source="employment_type.name", read_only=True)
    job_level_name = serializers.CharField(source="job_level.name", read_only=True)
    medical_specialty_names = serializers.SerializerMethodField()
    manager_name = serializers.SerializerMethodField()
    manager_profile = serializers.SerializerMethodField()
    direct_reports_count = serializers.SerializerMethodField()
    external_links = ExternalEmployeeLinkSerializer(many=True, read_only=True)
    documents = EmployeeDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Employee
        fields = (
            "id",
            "user",
            "external_baf_id",
            "external_fotopacients_id",
            "legacy_peopleforce_id",
            "employee_number",
            "first_name",
            "last_name",
            "middle_name",
            "full_name",
            "email",
            "personal_email",
            "phone",
            "phone2",
            "birth_date",
            "gender",
            "avatar_url",
            "avatar_local_url",
            "avatar_downloaded_at",
            "avatar_download_error",
            "peopleforce_status",
            "peopleforce_fields",
            "clinic",
            "clinic_name",
            "department",
            "department_name",
            "position",
            "position_name",
            "division",
            "division_name",
            "employment_type",
            "employment_type_name",
            "job_level",
            "job_level_name",
            "medical_specialties",
            "medical_specialty_names",
            "manager_name",
            "manager_profile",
            "direct_reports_count",
            "status",
            "hired_on",
            "dismissed_on",
            "notes",
            "external_links",
            "documents",
        )

    def get_medical_specialty_names(self, obj):
        return list(obj.medical_specialties.values_list("name", flat=True))

    def get_avatar_local_url(self, obj):
        if not obj.avatar_file:
            return ""
        try:
            url = obj.avatar_file.url
        except ValueError:
            return ""
        # Cache-busting version so stale CDN/browser-cached 404s (from before a
        # media sync) are bypassed, and avatar changes invalidate the cache.
        version = getattr(obj, "avatar_downloaded_at", None) or getattr(obj, "updated_at", None)
        if version is not None:
            try:
                return f"{url}?v={int(version.timestamp())}"
            except (AttributeError, ValueError, OSError):
                return url
        return url

    def _current_manager(self, obj):
        today = timezone.localdate()
        fallback = None
        for assignment in obj.manager_assignments.all():
            if not assignment.manager_id:
                continue
            if assignment.is_primary and assignment.valid_from <= today and (
                assignment.valid_to is None or assignment.valid_to >= today
            ):
                return assignment.manager
            if fallback is None and assignment.is_primary:
                fallback = assignment.manager
        return fallback

    def get_manager_name(self, obj):
        manager = self._current_manager(obj)
        return manager.full_name if manager else ""

    def get_manager_profile(self, obj):
        manager = self._current_manager(obj)
        if not manager:
            return None
        return EmployeeCompactSerializer(manager, context=self.context).data

    def get_direct_reports_count(self, obj):
        annotated = getattr(obj, "direct_reports_count", None)
        if annotated is not None:
            return annotated
        today = timezone.localdate()
        return obj.subordinate_assignments.filter(
            is_primary=True,
            valid_from__lte=today,
        ).filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today)).count()


class ManagerAssignmentSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True)

    class Meta:
        model = ManagerAssignment
        fields = ("id", "employee", "employee_name", "manager", "manager_name", "valid_from", "valid_to", "is_primary")
