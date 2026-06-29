from django.db.models import Count
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from config.permissions import ConfiguredReadOnlyOrAuthenticated

from .models import Project, TimeEntry
from .serializers import (
    ProjectDetailSerializer,
    ProjectListSerializer,
    ProjectWriteSerializer,
    TimeEntrySerializer,
)

TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}


class ProjectViewSet(viewsets.ModelViewSet):
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]

    def get_queryset(self):
        qs = (
            Project.objects.annotate(member_count=Count("members"))
            .prefetch_related("members", "members__position", "members__clinic", "members__department", "members__division")
            .order_by("order", "name")
        )
        archived = self.request.query_params.get("archived")
        if archived is not None:
            raw = archived.strip().lower()
            if raw in TRUE_VALUES:
                qs = qs.filter(is_archived=True)
            elif raw in FALSE_VALUES:
                qs = qs.filter(is_archived=False)
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProjectDetailSerializer
        if self.action in {"create", "update", "partial_update"}:
            return ProjectWriteSerializer
        return ProjectListSerializer

    def _detail_response(self, project, status_code=status.HTTP_200_OK):
        project.member_count = project.members.count()
        return Response(ProjectDetailSerializer(project, context=self.get_serializer_context()).data, status=status_code)

    def _employee_ids(self, request):
        ids = request.data.get("employee_ids")
        if not isinstance(ids, list):
            return None
        normalized = []
        for value in ids:
            try:
                normalized.append(int(value))
            except (TypeError, ValueError):
                return None
        return normalized

    @action(detail=True, methods=["post"], url_path="add-members")
    def add_members(self, request, pk=None):
        ids = self._employee_ids(request)
        if ids is None:
            return Response({"detail": "employee_ids must be a list of integers."}, status=status.HTTP_400_BAD_REQUEST)
        project = self.get_object()
        if ids:
            project.members.add(*ids)
        return self._detail_response(project)

    @action(detail=True, methods=["post"], url_path="remove-members")
    def remove_members(self, request, pk=None):
        ids = self._employee_ids(request)
        if ids is None:
            return Response({"detail": "employee_ids must be a list of integers."}, status=status.HTTP_400_BAD_REQUEST)
        project = self.get_object()
        if ids:
            project.members.remove(*ids)
        return self._detail_response(project)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        project = self.get_object()
        project.is_archived = True
        project.save(update_fields=["is_archived", "updated_at"])
        return self._detail_response(project)

    @action(detail=True, methods=["post"])
    def unarchive(self, request, pk=None):
        project = self.get_object()
        project.is_archived = False
        project.save(update_fields=["is_archived", "updated_at"])
        return self._detail_response(project)


class TimeEntryViewSet(viewsets.ModelViewSet):
    """Відстеження часу поточного користувача (старт/стоп роботи над проєктом)."""

    permission_classes = [IsAuthenticated]
    serializer_class = TimeEntrySerializer

    def _employee(self):
        return getattr(self.request.user, "employee_profile", None)

    def get_queryset(self):
        qs = TimeEntry.objects.select_related("project", "employee").all()
        project = self.request.query_params.get("project")
        employee_param = self.request.query_params.get("employee")
        if project:
            qs = qs.filter(project_id=project)
        elif employee_param:
            qs = qs.filter(employee_id=employee_param)
        else:
            employee = self._employee()
            if employee is None:
                return TimeEntry.objects.none()
            qs = qs.filter(employee=employee)
        if self.request.query_params.get("date") == "today":
            qs = qs.filter(started_at__date=timezone.localdate())
        date_from = self.request.query_params.get("from")
        if date_from:
            qs = qs.filter(started_at__date__gte=date_from)
        date_to = self.request.query_params.get("to")
        if date_to:
            qs = qs.filter(started_at__date__lte=date_to)
        return qs

    @action(detail=False, methods=["get"])
    def active(self, request):
        employee = self._employee()
        entry = TimeEntry.objects.filter(employee=employee, ended_at__isnull=True).select_related("project").first() if employee else None
        return Response(TimeEntrySerializer(entry).data if entry else None)

    @action(detail=False, methods=["post"])
    def start(self, request):
        employee = self._employee()
        if employee is None:
            return Response({"detail": "Профіль співробітника не знайдено."}, status=status.HTTP_400_BAD_REQUEST)
        # Закриваємо попередній активний запис, якщо є.
        TimeEntry.objects.filter(employee=employee, ended_at__isnull=True).update(ended_at=timezone.now())
        project_id = request.data.get("project") or None
        entry = TimeEntry.objects.create(
            employee=employee,
            project_id=project_id,
            comment=(request.data.get("comment") or "").strip(),
            started_at=timezone.now(),
        )
        return Response(TimeEntrySerializer(entry).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        entry = self.get_object()
        if entry.ended_at is None:
            entry.ended_at = timezone.now()
            entry.save(update_fields=["ended_at", "updated_at"])
        return Response(TimeEntrySerializer(entry).data)
