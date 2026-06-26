from django.db.models import Count
from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import ConfiguredReadOnlyOrAuthenticated
from apps.employees.models import Employee
from apps.leave.models import LeaveRequest
from apps.skud.models import IntegrationRun, WorkDaySummary


class OverviewView(APIView):
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]

    def get(self, request):
        employees = Employee.objects.values("status").annotate(count=Count("id"))
        workday_exceptions = WorkDaySummary.objects.exclude(status=WorkDaySummary.Status.OK).count()
        pending_leave = LeaveRequest.objects.filter(status=LeaveRequest.Status.SUBMITTED).count()
        last_runs = [
            {
                "system": run.system.name,
                "job": run.job_name,
                "status": run.status,
                "started_at": run.started_at,
                "rows_inserted": run.rows_inserted,
            }
            for run in IntegrationRun.objects.select_related("system").order_by("-started_at")[:5]
        ]
        return Response(
            {
                "employees_by_status": list(employees),
                "workday_exceptions": workday_exceptions,
                "pending_leave_requests": pending_leave,
                "last_integration_runs": last_runs,
            }
        )
