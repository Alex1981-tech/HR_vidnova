from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.permissions import ConfiguredReadOnlyOrAuthenticated

from .models import LeaveBalance, LeaveRequest, LeaveType
from .serializers import LeaveBalanceSerializer, LeaveRequestSerializer, LeaveTypeSerializer


class LeaveModelViewSet(viewsets.ModelViewSet):
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]


class LeaveTypeViewSet(LeaveModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer

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
        types = {lt.id: lt for lt in LeaveType.objects.filter(id__in=normalized_ids)}
        now = timezone.now()
        to_update = []
        for index, type_id in enumerate(normalized_ids, start=1):
            lt = types.get(type_id)
            if not lt:
                continue
            lt.order = index
            lt.updated_at = now
            to_update.append(lt)
        if to_update:
            LeaveType.objects.bulk_update(to_update, ["order", "updated_at"])
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)


class LeaveRequestViewSet(LeaveModelViewSet):
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        qs = LeaveRequest.objects.select_related("employee", "employee__position", "leave_type", "decided_by").prefetch_related("approval_steps").all()
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        employee = self.request.query_params.get("employee")
        if employee:
            qs = qs.filter(employee_id=employee)
        date_from = self.request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(date_to__gte=date_from)
        date_to = self.request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(date_from__lte=date_to)
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
