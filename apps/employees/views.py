from django.db import transaction
from django.db.models import Count, Max, Prefetch, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.permissions import ConfiguredReadOnlyOrAuthenticated

from .models import (
    Clinic,
    Department,
    DepartmentLevel,
    Division,
    Employee,
    EmployeeDocument,
    EmployeeDocumentFolder,
    EmploymentType,
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
from .serializers import (
    ClinicSerializer,
    DepartmentLevelSerializer,
    DepartmentSerializer,
    DivisionSerializer,
    EmployeeDocumentFolderSerializer,
    EmployeeDocumentSerializer,
    EmployeeCompactSerializer,
    EmployeeSerializer,
    EmploymentTypeSerializer,
    GenderSerializer,
    HolidayPolicySerializer,
    HolidaySerializer,
    JobLevelSerializer,
    ManagerAssignmentSerializer,
    MedicalSpecialtySerializer,
    PositionSerializer,
    ProbationPolicySerializer,
    TeamSerializer,
    TerminationReasonSerializer,
    TerminationTypeSerializer,
    WorkingPatternSerializer,
)


class EmployeeApiViewSet(viewsets.ModelViewSet):
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]


class ClinicViewSet(EmployeeApiViewSet):
    serializer_class = ClinicSerializer

    def _replacement_clinic(self, instance):
        return (
            Clinic.objects.exclude(pk=instance.pk)
            .filter(is_active=True)
            .annotate(active_employees=Count("employees", filter=Q(employees__status=Employee.Status.ACTIVE)))
            .order_by("-active_employees", "name")
            .first()
            or Clinic.objects.exclude(pk=instance.pk).order_by("name").first()
        )

    def get_queryset(self):
        qs = Clinic.objects.annotate(
            employee_count=Count("employees", filter=Q(employees__status=Employee.Status.ACTIVE)),
        ).select_related("holiday_policy_ref").order_by("name")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(country_code__icontains=search)
                | Q(address__icontains=search)
                | Q(holiday_policy_name__icontains=search)
            )
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    def perform_destroy(self, instance):
        if instance.code == "peopleforce":
            replacement = self._replacement_clinic(instance)
            if replacement:
                with transaction.atomic():
                    instance.departments.update(clinic=replacement)
                    instance.employee_position_history.update(clinic=replacement)
                    instance.employees.update(clinic=replacement)
                    instance.delete()
                return
        if instance.employees.exists() or instance.departments.exists() or instance.employee_position_history.exists():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
            return
        instance.delete()


class HolidayPolicyViewSet(EmployeeApiViewSet):
    serializer_class = HolidayPolicySerializer

    def get_queryset(self):
        qs = HolidayPolicy.objects.annotate(
            location_count=Count("clinics", filter=Q(clinics__is_active=True), distinct=True),
            holiday_count=Count("holidays", filter=Q(holidays__is_active=True), distinct=True),
        ).order_by("name")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(country_code__icontains=search))
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    def perform_destroy(self, instance):
        if instance.clinics.exists() or instance.holidays.exists():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
            return
        instance.delete()


class HolidayViewSet(EmployeeApiViewSet):
    serializer_class = HolidaySerializer

    def get_queryset(self):
        qs = Holiday.objects.select_related("policy").order_by("occurs_on", "name")
        policy = self.request.query_params.get("policy")
        if policy:
            qs = qs.filter(policy_id=policy)
        year = self.request.query_params.get("year")
        if year and year.isdigit():
            year_value = int(year)
            qs = qs.filter(Q(occurs_on__year=year_value) | Q(recurrence=Holiday.Recurrence.YEARLY))
        starts_on = self.request.query_params.get("starts_on")
        ends_on = self.request.query_params.get("ends_on")
        if starts_on:
            qs = qs.filter(occurs_on__gte=starts_on)
        if ends_on:
            qs = qs.filter(occurs_on__lte=ends_on)
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        is_active = self.request.query_params.get("is_active", "true")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True, policy__is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])


class DepartmentViewSet(EmployeeApiViewSet):
    serializer_class = DepartmentSerializer

    def get_queryset(self):
        qs = (
            Department.objects.select_related("clinic", "parent", "manager", "level")
            .annotate(
                employee_count=Count("employees", filter=Q(employees__status=Employee.Status.ACTIVE), distinct=True),
                children_count=Count("children", filter=Q(children__is_active=True), distinct=True),
            )
            .order_by("name")
        )
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(parent__name__icontains=search)
                | Q(manager__last_name__icontains=search)
                | Q(manager__first_name__icontains=search)
                | Q(level__name__icontains=search)
            )
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    def perform_destroy(self, instance):
        if instance.employees.exists() or instance.children.exists():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
            return
        instance.delete()


class DepartmentLevelViewSet(EmployeeApiViewSet):
    serializer_class = DepartmentLevelSerializer

    def get_queryset(self):
        qs = DepartmentLevel.objects.annotate(
            department_count=Count("departments", filter=Q(departments__is_active=True), distinct=True),
        ).order_by("name")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    def perform_destroy(self, instance):
        if instance.departments.exists():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
            return
        instance.delete()


class PositionViewSet(EmployeeApiViewSet):
    serializer_class = PositionSerializer

    def get_queryset(self):
        qs = Position.objects.annotate(
            employee_count=Count("employees", filter=Q(employees__status=Employee.Status.ACTIVE)),
        ).order_by("name")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    def perform_destroy(self, instance):
        if instance.employees.exists() or instance.employee_history.exists():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
            return
        instance.delete()


class DivisionViewSet(EmployeeApiViewSet):
    serializer_class = DivisionSerializer

    def get_queryset(self):
        qs = Division.objects.annotate(
            employee_count=Count("employees", filter=Q(employees__status=Employee.Status.ACTIVE)),
        ).order_by("name")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    def perform_destroy(self, instance):
        if instance.employees.exists() or instance.employee_position_history.exists():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
            return
        instance.delete()


class EmploymentTypeViewSet(EmployeeApiViewSet):
    serializer_class = EmploymentTypeSerializer

    def get_queryset(self):
        qs = EmploymentType.objects.annotate(
            employee_count=Count("employees", filter=Q(employees__status=Employee.Status.ACTIVE)),
        ).order_by("name")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    def perform_destroy(self, instance):
        if instance.employees.exists() or instance.employee_status_history.exists():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
            return
        instance.delete()


class WorkingPatternViewSet(EmployeeApiViewSet):
    serializer_class = WorkingPatternSerializer

    def get_queryset(self):
        qs = WorkingPattern.objects.all().order_by("name")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs


class ProbationPolicyViewSet(EmployeeApiViewSet):
    serializer_class = ProbationPolicySerializer

    def get_queryset(self):
        qs = ProbationPolicy.objects.annotate(
            employee_count=Count(
                "employee_status_history__employee",
                filter=Q(employee_status_history__employee__status=Employee.Status.ACTIVE),
                distinct=True,
            ),
        ).order_by("name")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    def perform_destroy(self, instance):
        if instance.employee_status_history.exists():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
            return
        instance.delete()


class JobLevelViewSet(EmployeeApiViewSet):
    serializer_class = JobLevelSerializer

    def get_queryset(self):
        qs = JobLevel.objects.annotate(
            employee_count=Count("employees", filter=Q(employees__status=Employee.Status.ACTIVE)),
        ).order_by("sort_order", "name")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    def perform_create(self, serializer):
        sort_order = serializer.validated_data.get("sort_order")
        if sort_order:
            serializer.save()
            return
        last_order = JobLevel.objects.aggregate(value=Max("sort_order"))["value"] or 0
        serializer.save(sort_order=last_order + 10)

    def perform_destroy(self, instance):
        if instance.employees.exists() or instance.employee_position_history.exists():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
            return
        instance.delete()

    @action(detail=False, methods=["post"], url_path="reorder")
    def reorder(self, request):
        ids = request.data.get("ids")
        if not isinstance(ids, list):
            return Response({"detail": "ids must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        normalized_ids = []
        for value in ids:
            try:
                normalized_ids.append(int(value))
            except (TypeError, ValueError):
                return Response({"detail": "ids must contain integers."}, status=status.HTTP_400_BAD_REQUEST)

        levels = {level.id: level for level in JobLevel.objects.filter(id__in=normalized_ids)}
        now = timezone.now()
        to_update = []
        for index, level_id in enumerate(normalized_ids, start=1):
            level = levels.get(level_id)
            if not level:
                continue
            level.sort_order = index * 10
            level.updated_at = now
            to_update.append(level)
        if to_update:
            JobLevel.objects.bulk_update(to_update, ["sort_order", "updated_at"])

        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)


class GenderViewSet(EmployeeApiViewSet):
    serializer_class = GenderSerializer

    def get_queryset(self):
        qs = Gender.objects.all().order_by("name")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    @transaction.atomic
    def perform_update(self, serializer):
        old_code = serializer.instance.code
        instance = serializer.save()
        if instance.code != old_code:
            Employee.objects.filter(gender=old_code).update(gender=instance.code)

    def perform_destroy(self, instance):
        if Employee.objects.filter(gender=instance.code).exists():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
            return
        instance.delete()


class TerminationReasonViewSet(EmployeeApiViewSet):
    serializer_class = TerminationReasonSerializer

    def get_queryset(self):
        qs = TerminationReason.objects.all().order_by("name")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs


class TerminationTypeViewSet(EmployeeApiViewSet):
    serializer_class = TerminationTypeSerializer

    def get_queryset(self):
        qs = TerminationType.objects.all().order_by("name")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs


class MedicalSpecialtyViewSet(EmployeeApiViewSet):
    serializer_class = MedicalSpecialtySerializer

    def get_queryset(self):
        qs = MedicalSpecialty.objects.annotate(
            employee_count=Count("employees", filter=Q(employees__status=Employee.Status.ACTIVE), distinct=True),
        ).order_by("name")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    def perform_destroy(self, instance):
        if instance.employees.exists():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
            return
        instance.delete()


class TeamViewSet(EmployeeApiViewSet):
    serializer_class = TeamSerializer

    def get_queryset(self):
        team_memberships = (
            TeamMembership.objects.filter(is_active=True, employee__status=Employee.Status.ACTIVE)
            .select_related("employee", "employee__clinic", "employee__department", "employee__position", "employee__division")
            .order_by("employee__last_name", "employee__first_name", "employee__middle_name")
        )
        qs = (
            Team.objects.select_related("lead", "lead__clinic", "lead__department", "lead__position", "lead__division")
            .prefetch_related(Prefetch("memberships", queryset=team_memberships))
            .annotate(
                member_count=Count(
                    "memberships",
                    filter=Q(memberships__is_active=True, memberships__employee__status=Employee.Status.ACTIVE),
                    distinct=True,
                )
            )
            .order_by("name")
        )
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    def perform_destroy(self, instance):
        if instance.memberships.filter(is_active=True).exists():
            instance.is_active = False
            instance.save(update_fields=["is_active", "updated_at"])
            return
        instance.delete()


class EmployeeDocumentFolderViewSet(EmployeeApiViewSet):
    queryset = EmployeeDocumentFolder.objects.all()
    serializer_class = EmployeeDocumentFolderSerializer


class EmployeeDocumentViewSet(EmployeeApiViewSet):
    serializer_class = EmployeeDocumentSerializer

    def get_queryset(self):
        qs = EmployeeDocument.objects.select_related("employee", "folder").all()
        employee = self.request.query_params.get("employee")
        if employee:
            qs = qs.filter(employee_id=employee)
        folder = self.request.query_params.get("folder")
        if folder:
            qs = qs.filter(folder_id=folder)
        document_type = self.request.query_params.get("type")
        if document_type:
            qs = qs.filter(document_type=document_type)
        return qs


class EmployeeViewSet(EmployeeApiViewSet):
    serializer_class = EmployeeSerializer

    def get_serializer_class(self):
        if self.request.query_params.get("compact") in {"1", "true", "yes"}:
            return EmployeeCompactSerializer
        return EmployeeSerializer

    def get_queryset(self):
        compact = self.request.query_params.get("compact") in {"1", "true", "yes"}
        today = timezone.localdate()

        def filter_values(name):
            raw_value = self.request.query_params.get(name, "").strip()
            return [value.strip() for value in raw_value.split(",") if value.strip()]

        def apply_nullable_id_filter(queryset, values, field_name):
            empty_markers = {"none", "null", "empty"}
            ids = [value for value in values if value not in empty_markers]
            query = Q()
            if ids:
                query |= Q(**{f"{field_name}__in": ids})
            if any(value in empty_markers for value in values):
                query |= Q(**{field_name.replace("_id", "") + "__isnull": True})
            return queryset.filter(query) if query else queryset

        select_related_fields = [
            "clinic",
            "department",
            "position",
            "division",
            "employment_type",
            "job_level",
            "user",
        ]
        qs = Employee.objects.select_related(*select_related_fields).annotate(
            direct_reports_count=Count(
                "subordinate_assignments",
                filter=Q(
                    subordinate_assignments__is_primary=True,
                    subordinate_assignments__valid_from__lte=today,
                )
                & (Q(subordinate_assignments__valid_to__isnull=True) | Q(subordinate_assignments__valid_to__gte=today)),
                distinct=True,
            )
        )
        if not compact:
            manager_assignments = ManagerAssignment.objects.select_related(
                "manager",
                "manager__clinic",
                "manager__department",
                "manager__position",
                "manager__division",
            )
            qs = qs.prefetch_related(
                "external_links",
                "medical_specialties",
                "documents",
                Prefetch("manager_assignments", queryset=manager_assignments),
            )
        qs = qs.all()
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(
                Q(last_name__icontains=search)
                | Q(first_name__icontains=search)
                | Q(middle_name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
            )
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        clinic_values = filter_values("clinic")
        if clinic_values:
            qs = qs.filter(clinic_id__in=clinic_values)
        department_values = filter_values("department")
        if department_values:
            qs = qs.filter(department_id__in=department_values)
        department_level_values = filter_values("department_level")
        if department_level_values:
            qs = apply_nullable_id_filter(qs, department_level_values, "department__level_id")
        division_values = filter_values("division")
        if division_values:
            qs = apply_nullable_id_filter(qs, division_values, "division_id")
        team_values = filter_values("team")
        if team_values:
            qs = qs.filter(team_memberships__team_id__in=team_values, team_memberships__is_active=True).distinct()
        medical_specialty_values = filter_values("medical_specialty")
        if medical_specialty_values:
            empty_markers = {"none", "null", "empty"}
            specialty_ids = [value for value in medical_specialty_values if value not in empty_markers]
            specialty_query = Q()
            if specialty_ids:
                specialty_query |= Q(medical_specialties__id__in=specialty_ids)
            if any(value in empty_markers for value in medical_specialty_values):
                specialty_query |= Q(medical_specialties__isnull=True)
            qs = qs.filter(specialty_query).distinct()
        job_level_values = filter_values("job_level")
        if job_level_values:
            qs = apply_nullable_id_filter(qs, job_level_values, "job_level_id")
        employment_type_values = filter_values("employment_type")
        if employment_type_values:
            qs = apply_nullable_id_filter(qs, employment_type_values, "employment_type_id")
        probation_policy = self.request.query_params.get("probation_policy")
        if probation_policy in {"none", "null", "empty"}:
            qs = qs.filter(employment_status_history__probation_policy__isnull=True).distinct()
        elif probation_policy:
            qs = qs.filter(employment_status_history__probation_policy_id=probation_policy).distinct()
        position_values = filter_values("position")
        if position_values:
            qs = apply_nullable_id_filter(qs, position_values, "position_id")
        gender = self.request.query_params.get("gender")
        if gender in {"none", "null", "empty"}:
            qs = qs.filter(gender="")
        elif gender:
            qs = qs.filter(gender=gender)
        return qs


class ManagerAssignmentViewSet(EmployeeApiViewSet):
    queryset = ManagerAssignment.objects.select_related("employee", "manager").all()
    serializer_class = ManagerAssignmentSerializer
