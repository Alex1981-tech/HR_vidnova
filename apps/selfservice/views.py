from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.employees.models import Employee
from apps.knowledge.models import KnowledgeCategory, KnowledgeDocument
from apps.leave.models import LeaveRequest, LeaveType
from apps.skud.models import AccessEvent, TimeCorrectionRequest, WorkDaySummary

from .serializers import (
    SelfAccessEventSerializer,
    SelfEmployeeSerializer,
    SelfKnowledgeCategorySerializer,
    SelfKnowledgeDocumentSerializer,
    SelfLeaveRequestSerializer,
    SelfLeaveTypeSerializer,
    SelfTimeCorrectionRequestSerializer,
    SelfWorkDaySummarySerializer,
    UserPreferenceSerializer,
)
from .models import UserPreference


MAX_ATTENDANCE_RANGE_DAYS = 92


def get_current_employee(request) -> Employee:
    try:
        return request.user.employee_profile
    except Employee.DoesNotExist as exc:
        raise NotFound("К текущему пользователю не привязан профиль сотрудника.") from exc


def parse_bounded_date_range(request):
    today = timezone.localdate()
    default_from = today - timedelta(days=30)
    date_from = parse_date(request.query_params.get("from", "")) or default_from
    date_to = parse_date(request.query_params.get("to", "")) or today

    if date_from > date_to:
        raise ValidationError({"from": "Дата начала не может быть позже даты окончания."})
    if (date_to - date_from).days > MAX_ATTENDANCE_RANGE_DAYS:
        raise ValidationError({"to": f"Период не должен превышать {MAX_ATTENDANCE_RANGE_DAYS + 1} дней."})
    return date_from, date_to


class SelfProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = get_current_employee(request)
        return Response(SelfEmployeeSerializer(employee).data)


class SelfPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request) -> UserPreference:
        preference, _ = UserPreference.objects.get_or_create(user=request.user)
        return preference

    def get(self, request):
        return Response(UserPreferenceSerializer(self.get_object(request)).data)

    def patch(self, request):
        preference = self.get_object(request)
        serializer = UserPreferenceSerializer(preference, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class SelfAttendanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = get_current_employee(request)
        date_from, date_to = parse_bounded_date_range(request)

        workdays = WorkDaySummary.objects.filter(employee=employee, date__range=(date_from, date_to)).order_by("-date")
        events = (
            AccessEvent.objects.select_related("device")
            .filter(employee=employee, occurred_at__date__range=(date_from, date_to))
            .order_by("-occurred_at")[:200]
        )
        correction_requests = TimeCorrectionRequest.objects.filter(employee=employee, date__range=(date_from, date_to)).order_by(
            "-created_at"
        )

        return Response(
            {
                "employee": SelfEmployeeSerializer(employee).data,
                "range": {"from": date_from, "to": date_to},
                "workdays": SelfWorkDaySummarySerializer(workdays, many=True).data,
                "events": SelfAccessEventSerializer(events, many=True).data,
                "correction_requests": SelfTimeCorrectionRequestSerializer(correction_requests, many=True).data,
            }
        )


class SelfTimeCorrectionRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = get_current_employee(request)
        date_from, date_to = parse_bounded_date_range(request)
        queryset = TimeCorrectionRequest.objects.filter(employee=employee, date__range=(date_from, date_to)).order_by("-created_at")
        return Response(SelfTimeCorrectionRequestSerializer(queryset, many=True).data)

    def post(self, request):
        employee = get_current_employee(request)
        serializer = SelfTimeCorrectionRequestSerializer(
            data=request.data,
            context={"employee": employee, "submitted_at": timezone.now()},
        )
        serializer.is_valid(raise_exception=True)
        correction_request = serializer.save()
        return Response(SelfTimeCorrectionRequestSerializer(correction_request).data, status=status.HTTP_201_CREATED)


class SelfLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        employee = get_current_employee(request)
        requests = LeaveRequest.objects.select_related("leave_type").filter(employee=employee).order_by("-created_at")
        leave_types = LeaveType.objects.filter(is_active=True).order_by("name")
        return Response(
            {
                "leave_types": SelfLeaveTypeSerializer(leave_types, many=True).data,
                "requests": SelfLeaveRequestSerializer(requests, many=True).data,
            }
        )

    def post(self, request):
        employee = get_current_employee(request)
        serializer = SelfLeaveRequestSerializer(
            data=request.data,
            context={"employee": employee, "submitted_at": timezone.now()},
        )
        serializer.is_valid(raise_exception=True)
        leave_request = serializer.save()
        return Response(SelfLeaveRequestSerializer(leave_request).data, status=status.HTTP_201_CREATED)


class SelfKnowledgeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        categories = KnowledgeCategory.objects.filter(is_active=True).order_by("name")
        documents = (
            KnowledgeDocument.objects.select_related("category")
            .filter(status=KnowledgeDocument.Status.PUBLISHED, category__is_active=True)
            .order_by("-updated_at")
        )
        category = request.query_params.get("category")
        if category:
            documents = documents.filter(category_id=category)
        search = request.query_params.get("q", "").strip()
        if search:
            documents = documents.filter(Q(title__icontains=search) | Q(summary__icontains=search) | Q(body__icontains=search))

        return Response(
            {
                "categories": SelfKnowledgeCategorySerializer(categories, many=True).data,
                "documents": SelfKnowledgeDocumentSerializer(documents[:100], many=True).data,
            }
        )
