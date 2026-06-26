from rest_framework import viewsets

from config.permissions import ConfiguredReadOnlyOrAuthenticated

from .models import LeaveBalance, LeaveRequest, LeaveType
from .serializers import LeaveBalanceSerializer, LeaveRequestSerializer, LeaveTypeSerializer


class LeaveModelViewSet(viewsets.ModelViewSet):
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]


class LeaveTypeViewSet(LeaveModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer


class LeaveRequestViewSet(LeaveModelViewSet):
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        qs = LeaveRequest.objects.select_related("employee", "leave_type", "decided_by").prefetch_related("approval_steps").all()
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        employee = self.request.query_params.get("employee")
        if employee:
            qs = qs.filter(employee_id=employee)
        return qs


class LeaveBalanceViewSet(LeaveModelViewSet):
    serializer_class = LeaveBalanceSerializer

    def get_queryset(self):
        qs = LeaveBalance.objects.select_related("employee", "leave_type").all()
        employee = self.request.query_params.get("employee")
        if employee:
            qs = qs.filter(employee_id=employee)
        leave_type = self.request.query_params.get("leave_type")
        if leave_type:
            qs = qs.filter(leave_type_id=leave_type)
        return qs
