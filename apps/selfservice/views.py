from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.announcements.audience import resolve_audience
from apps.employees.models import Employee
from apps.knowledge.models import KnowledgeCategory, KnowledgeDocument
from apps.leave.models import LeaveBalance, LeaveRequest, LeaveType
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


def knowledge_category_conditions(category: KnowledgeCategory) -> list[dict]:
    filters = category.audience_filters if isinstance(category.audience_filters, dict) else {}
    conditions = filters.get("conditions")
    return conditions if isinstance(conditions, list) else []


def knowledge_category_visible_for_employee(category: KnowledgeCategory, employee: Employee) -> bool:
    if category.visibility_mode == KnowledgeCategory.VisibilityMode.ALL:
        return True
    employee_ids = category.audience_employee_ids if isinstance(category.audience_employee_ids, list) else []
    if employee_ids:
        try:
            return employee.pk in {int(value) for value in employee_ids}
        except (TypeError, ValueError):
            return False
    conditions = knowledge_category_conditions(category)
    if not conditions:
        return False
    return resolve_audience("conditions", conditions).filter(pk=employee.pk).exists()


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
        # Лише типи, призначені співробітнику (через нараховані баланси PeopleForce-політик).
        assigned_type_ids = list(
            LeaveBalance.objects.filter(employee=employee).values_list("leave_type_id", flat=True).distinct()
        )
        leave_types = LeaveType.objects.filter(is_active=True, id__in=assigned_type_ids).order_by("name")

        # Найсвіжіший баланс на кожен тип (за effective_on).
        balance_by_type = {}
        for bal in LeaveBalance.objects.filter(
            employee=employee, leave_type_id__in=assigned_type_ids
        ).order_by("leave_type_id", "-effective_on", "-id"):
            balance_by_type.setdefault(bal.leave_type_id, bal.balance)

        return Response(
            {
                "leave_types": SelfLeaveTypeSerializer(
                    leave_types, many=True, context={"balances": balance_by_type}
                ).data,
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
        employee = get_current_employee(request)
        categories = list(KnowledgeCategory.objects.filter(is_active=True).order_by("name"))
        visible_category_ids = {
            category.pk
            for category in categories
            if knowledge_category_visible_for_employee(category, employee)
        }
        categories = [category for category in categories if category.pk in visible_category_ids]
        documents = (
            KnowledgeDocument.objects.select_related("category")
            .filter(
                status=KnowledgeDocument.Status.PUBLISHED,
                category__is_active=True,
                category_id__in=visible_category_ids,
            )
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


class SelfSecurityLogView(APIView):
    """Події безпеки поточного користувача (вхід/вихід/сесія) з телеметрією."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.access.models import AuthAuditEvent

        events = AuthAuditEvent.objects.filter(user=request.user).order_by("-created_at")[:100]
        return Response(
            {
                "items": [
                    {
                        "id": e.id,
                        "event": e.event,
                        "event_label": e.get_event_display(),
                        "result": e.result,
                        "ip_address": e.ip_address,
                        "user_agent": e.user_agent,
                        "created_at": e.created_at.isoformat(),
                    }
                    for e in events
                ]
            }
        )
