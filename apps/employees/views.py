import mimetypes
import uuid

from django.db import transaction
from django.db.models import Count, Max, Prefetch, Q
from django.http import FileResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.announcements.audience import resolve_audience
from config.permissions import ConfiguredReadOnlyOrAuthenticated

# Ліміти для ручного завантаження документів (Фаза 7).
MAX_DOCUMENT_FILES = 10
MAX_DOCUMENT_SIZE = 200 * 1024 * 1024  # 200 МБ
PREVIEWABLE_DOCUMENT_MIME_TYPES = {"application/pdf"}
PREVIEWABLE_DOCUMENT_TEXT_MIME_TYPES = {
    "application/json",
    "application/xml",
    "application/xhtml+xml",
}
PREVIEWABLE_DOCUMENT_TEXT_EXTENSIONS = {
    "cfg",
    "conf",
    "csv",
    "css",
    "htm",
    "html",
    "ini",
    "js",
    "json",
    "jsx",
    "log",
    "md",
    "markdown",
    "php",
    "py",
    "sql",
    "ts",
    "tsx",
    "txt",
    "xml",
    "yaml",
    "yml",
}

COMPANY_LINK_AUDIENCE_SAMPLE_SIZE = 6


def _document_extension(name: str) -> str:
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def _is_previewable_content_type(content_type: str) -> bool:
    base = content_type.split(";", 1)[0].strip().lower()
    return (
        base in PREVIEWABLE_DOCUMENT_MIME_TYPES
        or base.startswith("image/")
        or base.startswith("video/")
        or base.startswith("audio/")
        or base.startswith("text/")
    )


def _document_preview_content_type(document: "EmployeeDocument") -> str | None:
    payload = document.legacy_payload if isinstance(document.legacy_payload, dict) else {}
    manual_upload = payload.get("manual_upload") if isinstance(payload.get("manual_upload"), dict) else {}
    stored_type = str(manual_upload.get("content_type") or "").strip().lower()
    guessed_type = (mimetypes.guess_type(document.name)[0] or "").strip().lower()
    if _document_extension(document.name) in PREVIEWABLE_DOCUMENT_TEXT_EXTENSIONS:
        return "text/plain"
    for content_type in (stored_type, guessed_type):
        base = content_type.split(";", 1)[0].strip().lower()
        if base in PREVIEWABLE_DOCUMENT_TEXT_MIME_TYPES or base.startswith("text/"):
            return "text/plain"
        if base == "image/svg+xml":
            continue
        if base and _is_previewable_content_type(base):
            return base
    return None


def _employee_avatar_url(employee: "Employee") -> str:
    if employee.avatar_file:
        try:
            return employee.avatar_file.url
        except ValueError:
            return employee.avatar_url or ""
    return employee.avatar_url or ""


def _audience_sample_payload(qs):
    return [
        {"id": emp.id, "full_name": emp.full_name, "avatar_url": _employee_avatar_url(emp)}
        for emp in qs.order_by("last_name", "first_name")[:COMPANY_LINK_AUDIENCE_SAMPLE_SIZE]
    ]

from .models import (
    EmployeeField,
    EmployeeFieldGroup,
    EmployeeFieldTable,
    Clinic,
    CompanyLink,
    Department,
    DepartmentLevel,
    Division,
    Employee,
    EmployeeDocument,
    EmployeeDocumentFolder,
    EmergencyContact,
    Dependent,
    EmployeeEducation,
    EmployeeCertificate,
    SkillCategory,
    Skill,
    EmployeeSkill,
    EmployeeNote,
    EmployeeFormTemplate,
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
    EmergencyContactSerializer,
    DependentSerializer,
    EmployeeEducationSerializer,
    EmployeeCertificateSerializer,
    SkillCategorySerializer,
    SkillSerializer,
    EmployeeSkillSerializer,
    EmployeeNoteSerializer,
    EmployeeFieldSerializer,
    EmployeeFieldGroupSerializer,
    EmployeeFieldTableSerializer,
    ClinicSerializer,
    CompanyLinkSerializer,
    DepartmentLevelSerializer,
    DepartmentSerializer,
    DivisionSerializer,
    EmployeeDocumentFolderSerializer,
    EmployeeDocumentSerializer,
    EmployeeCompactSerializer,
    EmployeeFormTemplateSerializer,
    EmployeeHireSerializer,
    EmployeeProfileBlockSerializer,
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
from . import work_sync


class EmployeeApiViewSet(viewsets.ModelViewSet):
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]


class CompanyLinkViewSet(EmployeeApiViewSet):
    serializer_class = CompanyLinkSerializer

    def _current_employee(self):
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return None
        return getattr(user, "employee_profile", None)

    @staticmethod
    def _is_visible_for_employee(link, employee):
        if link.audience_type == CompanyLink.Audience.ALL:
            return True
        if not employee:
            return True
        return resolve_audience(link.audience_type, link.conditions).filter(pk=employee.pk).exists()

    def get_queryset(self):
        qs = CompanyLink.objects.order_by("order", "title")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(url__icontains=search))
        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        if self.request.query_params.get("for_me") in {"true", "1"}:
            employee = self._current_employee()
            visible_ids = [item.id for item in qs if self._is_visible_for_employee(item, employee)]
            qs = CompanyLink.objects.filter(id__in=visible_ids).order_by("order", "title")
        return qs

    @action(detail=False, methods=["post"], url_path="audience-preview")
    def audience_preview(self, request):
        audience_type = request.data.get("audience_type") or CompanyLink.Audience.ALL
        if audience_type not in {CompanyLink.Audience.ALL, CompanyLink.Audience.CONDITIONS}:
            return Response({"detail": "Invalid audience_type."}, status=status.HTTP_400_BAD_REQUEST)
        conditions = request.data.get("conditions") or []
        if not isinstance(conditions, list):
            return Response({"detail": "conditions must be a list."}, status=status.HTTP_400_BAD_REQUEST)
        qs = resolve_audience(audience_type, conditions)
        return Response({"count": qs.count(), "sample": _audience_sample_payload(qs)})

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
        links = {item.id: item for item in CompanyLink.objects.filter(id__in=normalized_ids)}
        now = timezone.now()
        to_update = []
        for index, link_id in enumerate(normalized_ids, start=1):
            item = links.get(link_id)
            if not item:
                continue
            item.order = index
            item.updated_at = now
            to_update.append(item)
        if to_update:
            CompanyLink.objects.bulk_update(to_update, ["order", "updated_at"])
        return Response(self.get_serializer(self.get_queryset(), many=True).data)


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


class EmployeeFormTemplateViewSet(EmployeeApiViewSet):
    serializer_class = EmployeeFormTemplateSerializer

    def get_queryset(self):
        qs = EmployeeFormTemplate.objects.select_related("preboarding_form").order_by("form_type", "name")
        form_type = self.request.query_params.get("form_type", "").strip()
        if form_type:
            qs = qs.filter(form_type=form_type)
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        is_active = self.request.query_params.get("is_active", "true")
        if is_active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        elif is_active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        queryset = self.get_queryset()
        rows = queryset.values("form_type").annotate(count=Count("id")).order_by("form_type")
        return Response(list(rows))


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
    serializer_class = EmployeeDocumentFolderSerializer

    def get_queryset(self):
        qs = (
            EmployeeDocumentFolder.objects.select_related("parent")
            .annotate(doc_count=Count("documents"))
            .order_by("name")
        )
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        return qs


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

    @action(detail=False, methods=["post"], url_path="upload", parser_classes=[MultiPartParser, FormParser])
    def upload(self, request):
        """Ручне завантаження документів з ПК (multipart). До 10 файлів, ≤200МБ, будь-які типи."""
        employee_id = request.data.get("employee")
        folder_id = request.data.get("folder")
        files = request.FILES.getlist("files") or request.FILES.getlist("file")
        if not employee_id:
            return Response({"detail": "Не вказано співробітника."}, status=status.HTTP_400_BAD_REQUEST)
        if not files:
            return Response({"detail": "Не вибрано файлів."}, status=status.HTTP_400_BAD_REQUEST)
        if len(files) > MAX_DOCUMENT_FILES:
            return Response(
                {"detail": f"Максимум {MAX_DOCUMENT_FILES} файлів за раз."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            employee = Employee.objects.get(pk=employee_id)
        except (Employee.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "Співробітника не знайдено."}, status=status.HTTP_404_NOT_FOUND)
        folder = None
        if folder_id:
            folder = EmployeeDocumentFolder.objects.filter(pk=folder_id).first()

        created, errors = [], []
        for upload in files:
            if upload.size > MAX_DOCUMENT_SIZE:
                errors.append({"name": upload.name, "error": "Файл більший за 200 МБ."})
                continue
            with transaction.atomic():
                document = EmployeeDocument.objects.create(
                    employee=employee,
                    folder=folder,
                    legacy_peopleforce_id=f"manual:{uuid.uuid4()}",
                    name=upload.name[:240],
                    document_type=EmployeeDocument.DocumentType.FILE,
                    local_file=upload,
                    file_downloaded_at=timezone.now(),
                    legacy_payload={
                        "manual_upload": {
                            "content_type": getattr(upload, "content_type", "") or "",
                            "size": upload.size,
                        }
                    },
                )
            created.append(document)

        data = EmployeeDocumentSerializer(created, many=True, context=self.get_serializer_context()).data
        response_data = {"created": data, "errors": errors}
        if not created and errors:
            response_data["detail"] = "Файли не завантажено: " + "; ".join(
                f"{item['name']}: {item['error']}" for item in errors
            )
        return Response(
            response_data,
            status=status.HTTP_201_CREATED if created else status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["get"], url_path="preview")
    def preview(self, request, pk=None):
        document = self.get_object()
        if not document.local_file:
            return Response({"detail": "Файл відсутній."}, status=status.HTTP_404_NOT_FOUND)
        content_type = _document_preview_content_type(document)
        if not content_type:
            return Response(
                {"detail": "Попередній перегляд для цього типу файлу недоступний."},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )
        try:
            handle = document.local_file.open("rb")
        except (FileNotFoundError, ValueError):
            return Response({"detail": "Файл недоступний."}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(handle, as_attachment=False, filename=document.name, content_type=content_type)

    @action(detail=True, methods=["get"], url_path="download")
    def download(self, request, pk=None):
        document = self.get_object()
        if not document.local_file:
            return Response({"detail": "Файл відсутній."}, status=status.HTTP_404_NOT_FOUND)
        try:
            handle = document.local_file.open("rb")
        except (FileNotFoundError, ValueError):
            return Response({"detail": "Файл недоступний."}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(handle, as_attachment=True, filename=document.name)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Імпортовані з PeopleForce документи не видаляємо фізично; лише ручні (manual:).
        if not str(instance.legacy_peopleforce_id).startswith("manual:"):
            return Response(
                {"detail": "Імпортовані документи видаляти не можна."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class _EmployeeScopedViewSet(EmployeeApiViewSet):
    """Базовий для дочірніх записів профілю (фільтр ?employee=...)."""

    model = None

    def get_queryset(self):
        qs = self.model.objects.all()
        employee = self.request.query_params.get("employee")
        if employee:
            qs = qs.filter(employee_id=employee)
        return qs


class EmergencyContactViewSet(_EmployeeScopedViewSet):
    model = EmergencyContact
    serializer_class = EmergencyContactSerializer


class DependentViewSet(_EmployeeScopedViewSet):
    model = Dependent
    serializer_class = DependentSerializer


class EmployeeEducationViewSet(_EmployeeScopedViewSet):
    model = EmployeeEducation
    serializer_class = EmployeeEducationSerializer


class EmployeeCertificateViewSet(_EmployeeScopedViewSet):
    model = EmployeeCertificate
    serializer_class = EmployeeCertificateSerializer


class SkillCategoryViewSet(EmployeeApiViewSet):
    serializer_class = SkillCategorySerializer

    def get_queryset(self):
        qs = SkillCategory.objects.all().order_by("order", "name")
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        if self.request.query_params.get("is_active") in {"true", "1"}:
            qs = qs.filter(is_active=True)
        return qs


class SkillViewSet(EmployeeApiViewSet):
    serializer_class = SkillSerializer

    def get_queryset(self):
        qs = Skill.objects.select_related("category").all().order_by("name")
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category_id=category)
        search = self.request.query_params.get("q", "").strip()
        if search:
            qs = qs.filter(name__icontains=search)
        if self.request.query_params.get("is_active") in {"true", "1"}:
            qs = qs.filter(is_active=True)
        return qs


class EmployeeSkillViewSet(_EmployeeScopedViewSet):
    model = EmployeeSkill
    serializer_class = EmployeeSkillSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("skill", "skill__category")


class EmployeeNoteViewSet(_EmployeeScopedViewSet):
    model = EmployeeNote
    serializer_class = EmployeeNoteSerializer

    def get_queryset(self):
        return super().get_queryset().select_related("author")

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(author=user if getattr(user, "is_authenticated", False) else None)


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

    @action(detail=False, methods=["post"], url_path="hire")
    def hire(self, request):
        serializer = EmployeeHireSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        employee = serializer.save()
        output = EmployeeSerializer(employee, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path="profile-block")
    def profile_block(self, request, pk=None):
        """Per-block edit профілю: пише лише allowlist системних полів + custom_fields_delta."""
        employee = self.get_object()
        serializer = EmployeeProfileBlockSerializer(
            employee,
            data=request.data,
            partial=True,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        employee.refresh_from_db()
        output = EmployeeSerializer(employee, context=self.get_serializer_context())
        return Response(output.data)

    # --- Atomic row-level API для повторюваних таблиць профілю ---

    @staticmethod
    def _table_storage_key(table_id):
        return f"table_{table_id}"

    def _resolve_table(self, table_id):
        """Повертає EmployeeFieldTable або кидає DRF-помилку 400/404."""
        if not table_id:
            raise ValidationError({"table": "Параметр «table» обов'язковий."})
        try:
            return EmployeeFieldTable.objects.get(pk=table_id)
        except (EmployeeFieldTable.DoesNotExist, ValueError, TypeError):
            raise NotFound("Таблицю не знайдено.")

    @staticmethod
    def _clean_row_values(table, values):
        """Лишає тільки відомі колонки таблиці; ігнорує службові/зайві ключі."""
        if not isinstance(values, dict):
            raise ValidationError({"values": "«values» має бути об'єктом."})
        allowed = {col.get("key") for col in (table.columns or []) if col.get("key")}
        reserved = {"row_id", "created_at", "updated_at"}
        return {k: v for k, v in values.items() if k in allowed and k not in reserved}

    def _rows_with_ids(self, pk, key):
        """Повертає рядки таблиці, ледаче проставляючи row_id legacy-рядкам (міграція-на-читанні)."""
        employee = self.get_queryset().get(pk=pk)
        rows = (employee.custom_fields or {}).get(key, [])
        if not isinstance(rows, list):
            return []
        missing = [r for r in rows if isinstance(r, dict) and not r.get("row_id")]
        if not missing:
            return rows
        now = timezone.now().isoformat()
        with transaction.atomic():
            employee = Employee.objects.select_for_update().get(pk=pk)
            custom = dict(employee.custom_fields or {})
            rows = list(custom.get(key, []) or [])
            for r in rows:
                if isinstance(r, dict) and not r.get("row_id"):
                    r["row_id"] = uuid.uuid4().hex
                    r.setdefault("created_at", now)
                    r.setdefault("updated_at", now)
            custom[key] = rows
            employee.custom_fields = custom
            employee.save(update_fields=["custom_fields", "updated_at"])
        return rows

    @action(detail=True, methods=["get", "post"], url_path="table-rows")
    def table_rows(self, request, pk=None):
        table_id = request.query_params.get("table") or request.data.get("table")
        table = self._resolve_table(table_id)
        key = self._table_storage_key(table.id)

        if request.method == "GET":
            return Response(self._rows_with_ids(pk, key))

        # POST — створення рядка
        values = self._clean_row_values(table, request.data.get("values", request.data))
        now = timezone.now().isoformat()
        with transaction.atomic():
            employee = Employee.objects.select_for_update().get(pk=pk)
            custom = dict(employee.custom_fields or {})
            rows = list(custom.get(key, []) or [])
            row = {**values, "row_id": uuid.uuid4().hex, "created_at": now, "updated_at": now}
            rows.append(row)
            custom[key] = rows
            employee.custom_fields = custom
            employee.save(update_fields=["custom_fields", "updated_at"])
            if table.sync_target:
                work_sync.sync_table(employee, table)
        return Response(row, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch", "delete"], url_path="table-rows/(?P<row_id>[^/.]+)")
    def table_row_detail(self, request, pk=None, row_id=None):
        table_id = request.query_params.get("table") or request.data.get("table")
        table = self._resolve_table(table_id)
        key = self._table_storage_key(table.id)

        with transaction.atomic():
            employee = Employee.objects.select_for_update().get(pk=pk)
            custom = dict(employee.custom_fields or {})
            rows = list(custom.get(key, []) or [])
            index = next((i for i, r in enumerate(rows) if isinstance(r, dict) and r.get("row_id") == row_id), None)
            if index is None:
                raise NotFound("Рядок не знайдено.")

            if request.method == "DELETE":
                rows.pop(index)
                custom[key] = rows
                employee.custom_fields = custom
                employee.save(update_fields=["custom_fields", "updated_at"])
                if table.sync_target:
                    work_sync.sync_table(employee, table)
                return Response(status=status.HTTP_204_NO_CONTENT)

            # PATCH — оновлення значень
            values = self._clean_row_values(table, request.data.get("values", request.data))
            row = dict(rows[index])
            row.update(values)
            row["updated_at"] = timezone.now().isoformat()
            rows[index] = row
            custom[key] = rows
            employee.custom_fields = custom
            employee.save(update_fields=["custom_fields", "updated_at"])
            if table.sync_target:
                work_sync.sync_table(employee, table)
        return Response(row)


class ManagerAssignmentViewSet(EmployeeApiViewSet):
    queryset = ManagerAssignment.objects.select_related("employee", "manager").all()
    serializer_class = ManagerAssignmentSerializer


class EmployeeFieldGroupViewSet(EmployeeApiViewSet):
    serializer_class = EmployeeFieldGroupSerializer

    def get_queryset(self):
        qs = EmployeeFieldGroup.objects.prefetch_related("fields", "tables")
        tab = self.request.query_params.get("tab", "").strip()
        if tab:
            qs = qs.filter(tab=tab)
        return qs

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_system:
            return Response(
                {"detail": "Системну групу не можна видалити."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class EmployeeFieldViewSet(EmployeeApiViewSet):
    serializer_class = EmployeeFieldSerializer
    queryset = EmployeeField.objects.all()

    def perform_create(self, serializer):
        serializer.save(is_system=False, system_key="")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_system:
            return Response(
                {"detail": "Системне поле не можна видалити, лише вимкнути."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)


class EmployeeFieldTableViewSet(EmployeeApiViewSet):
    serializer_class = EmployeeFieldTableSerializer
    queryset = EmployeeFieldTable.objects.all()
