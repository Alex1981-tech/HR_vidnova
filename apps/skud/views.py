import calendar
from collections import defaultdict
from datetime import timedelta

from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Count, Max, Min, Q, Sum
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.dateparse import parse_time
from rest_framework import status
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
from .services import planned_working_time_for_employees
from .services import planned_working_time_by_date_for_employee


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
        planned_fallbacks = planned_working_time_for_employees(employee_ids, date_from, date_to)

        results = []
        for employee in page.object_list:
            summary = summaries.get(employee.id, {})
            period_summary = periods.get(employee.id, {})
            planned_fallback = planned_fallbacks.get(employee.id)
            planned_minutes = summary.get("planned_minutes") or (planned_fallback.minutes if planned_fallback else 0)
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


class EmployeeAttendanceDetailView(APIView):
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]

    def get(self, request, employee_id: int):
        today = timezone.localdate()
        date_from = parse_date(request.query_params.get("from") or "") or today.replace(day=1)
        default_end_day = calendar.monthrange(date_from.year, date_from.month)[1]
        date_to = parse_date(request.query_params.get("to") or "") or date_from.replace(day=default_end_day)
        if date_to < date_from:
            date_to = date_from
        max_days = 62
        if (date_to - date_from).days >= max_days:
            date_to = date_from + timedelta(days=max_days - 1)

        employee = get_object_or_404(
            Employee.objects.select_related("clinic", "department", "position"),
            pk=employee_id,
        )
        summaries = {
            summary.date: summary
            for summary in WorkDaySummary.objects.filter(employee=employee, date__gte=date_from, date__lte=date_to)
        }
        periods_by_date = defaultdict(list)
        periods = AttendancePeriod.objects.filter(employee=employee, date__gte=date_from, date__lte=date_to).order_by(
            "date",
            "start_at",
        )
        for period in periods:
            periods_by_date[period.date].append(period)

        planned_by_date = planned_working_time_by_date_for_employee(employee.id, date_from, date_to)
        days = []
        total_planned = 0
        total_actual = 0
        current_date = date_from
        while current_date <= date_to:
            summary = summaries.get(current_date)
            day_periods = periods_by_date.get(current_date, [])
            planned_fallback = planned_by_date.get(current_date)
            planned_minutes = (summary.planned_minutes if summary and summary.planned_minutes else None) or (
                planned_fallback.minutes if planned_fallback else 0
            )
            period_minutes = sum(period.duration_minutes for period in day_periods)
            actual_minutes = period_minutes or (summary.actual_minutes if summary else 0)
            difference_minutes = actual_minutes - planned_minutes
            total_planned += planned_minutes
            total_actual += actual_minutes
            days.append(
                {
                    "date": current_date,
                    "planned_minutes": planned_minutes,
                    "actual_minutes": actual_minutes,
                    "overtime_minutes": max(difference_minutes, 0),
                    "break_minutes": 0,
                    "paid_absence_minutes": 0,
                    "unpaid_absence_minutes": 0,
                    "total_absence_minutes": max(planned_minutes - actual_minutes, 0),
                    "difference_minutes": difference_minutes,
                    "first_entry_at": day_periods[0].start_at if day_periods else (summary.first_entry_at if summary else None),
                    "last_exit_at": day_periods[-1].end_at if day_periods else (summary.last_exit_at if summary else None),
                    "status": summary.status if summary else "",
                    "exception_count": summary.exception_count if summary else 0,
                    "working_pattern_names": list(planned_fallback.pattern_names) if planned_fallback else [],
                    "periods": [
                        {
                            "id": period.id,
                            "start_at": period.start_at,
                            "end_at": period.end_at,
                            "duration_minutes": period.duration_minutes,
                            "period_type": period.period_type,
                            "comment": period.comment,
                        }
                        for period in day_periods
                    ],
                }
            )
            current_date += timedelta(days=1)

        total_difference = total_actual - total_planned
        return Response(
            {
                "employee": {
                    "id": employee.id,
                    "full_name": employee.full_name,
                    "position_name": employee.position.name if employee.position_id else "",
                    "department_name": employee.department.name if employee.department_id else "",
                    "clinic_name": employee.clinic.name if employee.clinic_id else "",
                    "avatar_url": employee.avatar_url,
                    "avatar_local_url": employee.avatar_file.url if employee.avatar_file else "",
                },
                "range": {"from": date_from, "to": date_to},
                "summary": {
                    "planned_minutes": total_planned,
                    "actual_minutes": total_actual,
                    "overtime_minutes": max(total_difference, 0),
                    "break_minutes": 0,
                    "paid_absence_minutes": 0,
                    "unpaid_absence_minutes": 0,
                    "total_absence_minutes": max(total_planned - total_actual, 0),
                    "difference_minutes": total_difference,
                },
                "days": days,
            }
        )


class EmployeeAttendancePeriodView(APIView):
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]

    def post(self, request, employee_id: int):
        employee = get_object_or_404(Employee, pk=employee_id)
        payload = self._period_payload(request.data)
        if isinstance(payload, Response):
            return payload
        period = AttendancePeriod.objects.create(employee=employee, period_type=AttendancePeriod.PeriodType.MANUAL, **payload)
        return Response(self._serialize_period(period), status=status.HTTP_201_CREATED)

    def patch(self, request, employee_id: int, period_id: int):
        period = get_object_or_404(AttendancePeriod, pk=period_id, employee_id=employee_id)
        payload = self._period_payload(
            {
                "date": request.data.get("date", period.date.isoformat()),
                "start_time": request.data.get("start_time", timezone.localtime(period.start_at).strftime("%H:%M")),
                "end_time": request.data.get("end_time", timezone.localtime(period.end_at).strftime("%H:%M")),
                "comment": request.data.get("comment", period.comment),
            }
        )
        if isinstance(payload, Response):
            return payload
        for field_name, value in payload.items():
            setattr(period, field_name, value)
        period.period_type = AttendancePeriod.PeriodType.MANUAL
        period.save(update_fields=["date", "start_at", "end_at", "duration_minutes", "period_type", "comment", "updated_at"])
        return Response(self._serialize_period(period))

    def delete(self, request, employee_id: int, period_id: int):
        period = get_object_or_404(AttendancePeriod, pk=period_id, employee_id=employee_id)
        period.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _period_payload(self, data):
        work_date = parse_date(str(data.get("date") or ""))
        start_time = parse_time(str(data.get("start_time") or ""))
        end_time = parse_time(str(data.get("end_time") or ""))
        if not work_date or not start_time or not end_time:
            return Response({"detail": "date, start_time and end_time are required."}, status=status.HTTP_400_BAD_REQUEST)

        current_timezone = timezone.get_current_timezone()
        start_at = timezone.make_aware(timezone.datetime.combine(work_date, start_time), current_timezone)
        end_at = timezone.make_aware(timezone.datetime.combine(work_date, end_time), current_timezone)
        if end_at <= start_at:
            return Response({"detail": "end_time must be after start_time."}, status=status.HTTP_400_BAD_REQUEST)

        duration_minutes = max(0, int((end_at - start_at).total_seconds() // 60))
        return {
            "date": work_date,
            "start_at": start_at,
            "end_at": end_at,
            "duration_minutes": duration_minutes,
            "comment": str(data.get("comment") or "").strip(),
        }

    def _serialize_period(self, period: AttendancePeriod):
        return {
            "id": period.id,
            "employee": period.employee_id,
            "date": period.date,
            "start_at": period.start_at,
            "end_at": period.end_at,
            "duration_minutes": period.duration_minutes,
            "period_type": period.period_type,
            "comment": period.comment,
        }


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
