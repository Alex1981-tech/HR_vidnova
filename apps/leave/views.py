from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from config.permissions import ConfiguredReadOnlyOrAuthenticated

from apps.employees.models import Employee

from .models import (
    EmployeeLeavePolicyAssignment,
    LeaveBalance,
    LeaveLedgerEntry,
    LeavePolicy,
    LeavePolicyAccrualRule,
    LeaveRequest,
    LeaveType,
)
from .serializers import (
    EmployeeLeavePolicyAssignmentSerializer,
    LeaveBalanceSerializer,
    LeaveLedgerEntrySerializer,
    LeavePolicySerializer,
    LeaveRequestSerializer,
    LeaveTypeSerializer,
    LeaveTypeWithPoliciesSerializer,
)
from .services import assign_policy_to_employee, recalculate_policy_assignments, sync_assignment_balance, transition_leave_request_status


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

    @action(detail=False, methods=["get"], url_path="with-policies")
    def with_policies(self, request):
        policies = (
            LeavePolicy.objects.filter(is_active=True)
            .select_related("leave_type")
            .prefetch_related("accrual_rule")
            .annotate(employee_count=Count("assignments", filter=Q(assignments__is_active=True), distinct=True))
        )
        queryset = self.get_queryset().prefetch_related(Prefetch("policies", queryset=policies))
        serializer = LeaveTypeWithPoliciesSerializer(queryset, many=True)
        return Response(serializer.data)


class LeavePolicyViewSet(LeaveModelViewSet):
    serializer_class = LeavePolicySerializer

    def get_queryset(self):
        qs = (
            LeavePolicy.objects.select_related("leave_type")
            .prefetch_related("accrual_rule")
            .annotate(employee_count=Count("assignments", filter=Q(assignments__is_active=True), distinct=True))
        )
        leave_type = self.request.query_params.get("leave_type")
        if leave_type:
            qs = qs.filter(leave_type_id=leave_type)
        active = self.request.query_params.get("is_active")
        if active in {"true", "1"}:
            qs = qs.filter(is_active=True)
        if active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        return qs

    @action(detail=True, methods=["post"], url_path="copy")
    def copy(self, request, pk=None):
        source = self.get_object()
        base_name = f"{source.name} копія"
        name = base_name
        index = 2
        while LeavePolicy.objects.filter(leave_type=source.leave_type, name=name, is_active=True).exists():
            name = f"{base_name} {index}"
            index += 1

        policy_data = {}
        skip_fields = {"id", "created_at", "updated_at", "legacy_peopleforce_id"}
        for field in LeavePolicy._meta.fields:
            if field.name in skip_fields:
                continue
            policy_data[field.name] = getattr(source, field.name)
        policy_data["name"] = name
        policy = LeavePolicy.objects.create(**policy_data)

        source_rule = getattr(source, "accrual_rule", None)
        if source_rule:
            rule_data = {}
            for field in [
                "enabled",
                "start_delay_amount",
                "start_delay_unit",
                "start_balance",
                "annual_allowance",
                "period_amount",
                "frequency",
                "accrual_timing",
                "first_accrual",
                "max_balance",
                "carryover_mode",
                "carryover_limit",
                "carryover_expire_months",
                "carryover_day",
                "carryover_month",
                "seniority_bonus_enabled",
            ]:
                rule_data[field] = getattr(source_rule, field)
            LeavePolicyAccrualRule.objects.create(policy=policy, **rule_data)
        serializer = self.get_serializer(policy)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="recalculate")
    def recalculate(self, request, pk=None):
        policy = self.get_object()
        through_date = parse_date(request.data.get("through_date") or "") or timezone.localdate()
        count = recalculate_policy_assignments(policy, through_date=through_date)
        serializer = self.get_serializer(policy)
        return Response({"updated_assignments": count, "policy": serializer.data})

class EmployeeLeavePolicyAssignmentViewSet(LeaveModelViewSet):
    serializer_class = EmployeeLeavePolicyAssignmentSerializer

    def get_queryset(self):
        qs = EmployeeLeavePolicyAssignment.objects.select_related(
            "employee",
            "employee__position",
            "leave_type",
            "policy",
        )
        policy = self.request.query_params.get("policy")
        if policy:
            qs = qs.filter(policy_id=policy)
        leave_type = self.request.query_params.get("leave_type")
        if leave_type:
            qs = qs.filter(leave_type_id=leave_type)
        employee = self.request.query_params.get("employee")
        if employee:
            qs = qs.filter(employee_id=employee)
        active = self.request.query_params.get("is_active")
        if active in {"false", "0"}:
            qs = qs.filter(is_active=False)
        else:
            qs = qs.filter(is_active=True)
        return qs

    @action(detail=False, methods=["post"], url_path="bulk-assign")
    def bulk_assign(self, request):
        policy_id = request.data.get("policy")
        employee_ids = request.data.get("employee_ids")
        effective_on = parse_date(request.data.get("effective_on") or "") or timezone.localdate()
        initial_balance = request.data.get("initial_balance", 0)
        if not policy_id:
            return Response({"detail": "policy is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(employee_ids, list) or not employee_ids:
            return Response({"detail": "employee_ids must be a non-empty list."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            policy = LeavePolicy.objects.select_related("leave_type").get(pk=policy_id, is_active=True)
        except LeavePolicy.DoesNotExist:
            return Response({"detail": "Policy not found."}, status=status.HTTP_404_NOT_FOUND)

        employees = Employee.objects.filter(id__in=employee_ids, status=Employee.Status.ACTIVE)
        employees_by_id = {employee.id: employee for employee in employees}
        assignments = []
        errors = []
        for raw_id in employee_ids:
            try:
                employee_id = int(raw_id)
            except (TypeError, ValueError):
                errors.append({"employee": raw_id, "detail": "Invalid employee id."})
                continue
            employee = employees_by_id.get(employee_id)
            if not employee:
                errors.append({"employee": employee_id, "detail": "Active employee not found."})
                continue
            try:
                assignments.append(
                    assign_policy_to_employee(
                        employee=employee,
                        policy=policy,
                        effective_on=effective_on,
                        initial_balance=initial_balance,
                    )
                )
            except Exception as exc:  # pragma: no cover - serialized for admin UI diagnostics
                errors.append({"employee": employee_id, "detail": str(exc)})

        serializer = self.get_serializer(assignments, many=True)
        code = status.HTTP_207_MULTI_STATUS if errors else status.HTTP_201_CREATED
        return Response({"assignments": serializer.data, "errors": errors}, status=code)

    @action(detail=True, methods=["post"], url_path="recalculate")
    def recalculate(self, request, pk=None):
        assignment = self.get_object()
        through_date = parse_date(request.data.get("through_date") or "") or timezone.localdate()
        sync_assignment_balance(assignment, through_date=through_date)
        serializer = self.get_serializer(assignment)
        return Response(serializer.data)


class LeaveLedgerEntryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LeaveLedgerEntrySerializer
    permission_classes = [ConfiguredReadOnlyOrAuthenticated]

    def get_queryset(self):
        qs = LeaveLedgerEntry.objects.select_related("employee", "leave_type", "policy", "assignment").all()
        employee = self.request.query_params.get("employee")
        if employee:
            qs = qs.filter(employee_id=employee)
        leave_type = self.request.query_params.get("leave_type")
        if leave_type:
            qs = qs.filter(leave_type_id=leave_type)
        policy = self.request.query_params.get("policy")
        if policy:
            qs = qs.filter(policy_id=policy)
        assignment = self.request.query_params.get("assignment")
        if assignment:
            qs = qs.filter(assignment_id=assignment)
        return qs


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

    def _transition(self, request, target_status):
        comment = request.data.get("comment") or ""
        try:
            leave_request = transition_leave_request_status(
                self.get_object(),
                status=target_status,
                user=request.user,
                comment=comment,
            )
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            return Response(detail, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(leave_request)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="approve")
    def approve(self, request, pk=None):
        return self._transition(request, LeaveRequest.Status.APPROVED)

    @action(detail=True, methods=["post"], url_path="reject")
    def reject(self, request, pk=None):
        return self._transition(request, LeaveRequest.Status.REJECTED)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        return self._transition(request, LeaveRequest.Status.CANCELLED)


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
