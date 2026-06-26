import calendar

from django.core.paginator import Paginator
from django.db.models import Count, Max, Min, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import ConfiguredReadOnlyOrAuthenticated
from apps.employees.models import Employee

from .models import (
    AccessDevice,
    AccessEvent,
    AccessIdentity,
    AccessSystem,
    AttendancePeriod,
    IntegrationRun,
    TimeCorrectionRequest,
    WorkDaySummary,
)
from .serializers import (
    AccessDeviceSerializer,
    AccessEventSerializer,
    AccessIdentitySerializer,
    AccessSystemSerializer,
    IntegrationRunSerializer,
    TimeCorrectionRequestSerializer,
    WorkDaySummarySerializer,
)


class SkudModelViewSet(viewsets.ModelViewSet):
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]


class SkudReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]


class CompanyAttendanceSummaryView(APIView):
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        date_from = parse_date(request.query_params.get("from") or "") or today.replace(day=1)
        default_end_day = calendar.monthrange(date_from.year, date_from.month)[1]
        date_to = parse_date(request.query_params.get("to") or "") or date_from.replace(day=default_end_day)
        page_number = request.query_params.get("page", "1")
        page_size = min(max(int(request.query_params.get("page_size", "50")), 1), 100)

        employees = Employee.objects.select_related("clinic", "department", "position").order_by(
            "last_name",
            "first_name",
            "middle_name",
        )
        employee_status = request.query_params.get("employee_status", Employee.Status.ACTIVE)
        if employee_status != "all":
            employees = employees.filter(status=employee_status)

        search = request.query_params.get("q", "").strip()
        if search:
            employees = employees.filter(
                Q(last_name__icontains=search)
                | Q(first_name__icontains=search)
                | Q(middle_name__icontains=search)
                | Q(email__icontains=search)
                | Q(phone__icontains=search)
            )

        paginator = Paginator(employees, page_size)
        page = paginator.get_page(page_number)
        employee_ids = [employee.id for employee in page.object_list]
        summaries = {
            row["employee_id"]: row
            for row in WorkDaySummary.objects.filter(employee_id__in=employee_ids, date__gte=date_from, date__lte=date_to)
            .values("employee_id")
            .annotate(
                planned_minutes=Sum("planned_minutes"),
                actual_minutes=Sum("actual_minutes"),
                first_entry_at=Min("first_entry_at"),
                last_exit_at=Max("last_exit_at"),
                exception_count=Sum("exception_count"),
                summary_count=Count("id"),
            )
        }
        periods = {
            row["employee_id"]: row
            for row in AttendancePeriod.objects.filter(employee_id__in=employee_ids, date__gte=date_from, date__lte=date_to)
            .values("employee_id")
            .annotate(
                actual_minutes=Sum("duration_minutes"),
                first_entry_at=Min("start_at"),
                last_exit_at=Max("end_at"),
                period_count=Count("id"),
            )
        }

        results = []
        for employee in page.object_list:
            summary = summaries.get(employee.id, {})
            period_summary = periods.get(employee.id, {})
            planned_minutes = summary.get("planned_minutes") or 0
            actual_minutes = period_summary.get("actual_minutes") or summary.get("actual_minutes") or 0
            difference_minutes = actual_minutes - planned_minutes
            results.append(
                {
                    "id": employee.id,
                    "employee": employee.id,
                    "employee_name": employee.full_name,
                    "position_name": employee.position.name if employee.position_id else "",
                    "department_name": employee.department.name if employee.department_id else "",
                    "clinic_name": employee.clinic.name if employee.clinic_id else "",
                    "planned_minutes": planned_minutes,
                    "actual_minutes": actual_minutes,
                    "overtime_minutes": max(difference_minutes, 0),
                    "break_minutes": 0,
                    "paid_absence_minutes": 0,
                    "unpaid_absence_minutes": 0,
                    "total_absence_minutes": max(planned_minutes - actual_minutes, 0),
                    "difference_minutes": difference_minutes,
                    "first_entry_at": period_summary.get("first_entry_at") or summary.get("first_entry_at"),
                    "last_exit_at": period_summary.get("last_exit_at") or summary.get("last_exit_at"),
                    "exception_count": summary.get("exception_count") or 0,
                    "summary_count": period_summary.get("period_count") or summary.get("summary_count") or 0,
                }
            )

        return Response(
            {
                "count": paginator.count,
                "next": page.next_page_number() if page.has_next() else None,
                "previous": page.previous_page_number() if page.has_previous() else None,
                "results": results,
                "range": {"from": date_from, "to": date_to},
            }
        )


class AccessSystemViewSet(SkudModelViewSet):
    queryset = AccessSystem.objects.all()
    serializer_class = AccessSystemSerializer


class AccessDeviceViewSet(SkudModelViewSet):
    queryset = AccessDevice.objects.select_related("system").all()
    serializer_class = AccessDeviceSerializer


class AccessIdentityViewSet(SkudModelViewSet):
    queryset = AccessIdentity.objects.select_related("employee", "system").all()
    serializer_class = AccessIdentitySerializer


class AccessEventViewSet(SkudReadOnlyViewSet):
    serializer_class = AccessEventSerializer

    def get_queryset(self):
        qs = AccessEvent.objects.select_related("employee", "device", "raw_event").all()
        employee = self.request.query_params.get("employee")
        if employee:
            qs = qs.filter(employee_id=employee)
        date = self.request.query_params.get("date")
        if date:
            qs = qs.filter(occurred_at__date=date)
        quality = self.request.query_params.get("quality")
        if quality:
            qs = qs.filter(quality=quality)
        return qs


class WorkDaySummaryViewSet(SkudReadOnlyViewSet):
    serializer_class = WorkDaySummarySerializer

    def get_queryset(self):
        qs = WorkDaySummary.objects.select_related("employee").all()
        employee = self.request.query_params.get("employee")
        if employee:
            qs = qs.filter(employee_id=employee)
        date_from = self.request.query_params.get("from")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        date_to = self.request.query_params.get("to")
        if date_to:
            qs = qs.filter(date__lte=date_to)
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs


class TimeCorrectionRequestViewSet(SkudModelViewSet):
    serializer_class = TimeCorrectionRequestSerializer

    def get_queryset(self):
        qs = TimeCorrectionRequest.objects.select_related("employee", "decided_by", "applied_adjustment").all()
        employee = self.request.query_params.get("employee")
        if employee:
            qs = qs.filter(employee_id=employee)
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        date_from = self.request.query_params.get("from")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        date_to = self.request.query_params.get("to")
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs


class IntegrationRunViewSet(SkudReadOnlyViewSet):
    queryset = IntegrationRun.objects.select_related("system").all()
    serializer_class = IntegrationRunSerializer
