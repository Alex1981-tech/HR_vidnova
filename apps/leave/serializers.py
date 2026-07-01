from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.text import slugify
from rest_framework import serializers

from apps.employees.models import Employee

from .models import (
    EmployeeLeavePolicyAssignment,
    LeaveApprovalStep,
    LeaveBalance,
    LeaveLedgerEntry,
    LeavePolicy,
    LeavePolicyAccrualRule,
    LeaveRequest,
    LeaveType,
)
from .services import assign_policy_to_employee, current_balance, transition_leave_request_status, validate_leave_request_policy


class LeaveTypeSerializer(serializers.ModelSerializer):
    # code генерується автоматично з імені, якщо не передано (модалка має лише Ім'я).
    code = serializers.CharField(max_length=40, required=False, allow_blank=True)
    # unit приймає legacy-значення й нормалізується у validate_unit (не ChoiceField).
    unit = serializers.CharField(max_length=40, required=False, allow_blank=True)

    class Meta:
        model = LeaveType
        fields = (
            "id",
            "name",
            "code",
            "legacy_peopleforce_id",
            "unit",
            "icon",
            "color",
            "order",
            "requires_hr_approval",
            "is_active",
        )
        read_only_fields = ("legacy_peopleforce_id", "order")

    def validate_unit(self, value):
        """Нормалізує одиницю відстеження до days|hours; legacy-значення мапляться за префіксом."""
        raw = (value or "").strip().lower()
        if not raw:
            return LeaveType.TrackingUnit.DAYS
        if raw.startswith("hour") or raw.startswith("год"):
            return LeaveType.TrackingUnit.HOURS
        if raw.startswith("day") or raw.startswith("дн") or raw.startswith("ден"):
            return LeaveType.TrackingUnit.DAYS
        raise serializers.ValidationError("Одиниця має бути «days» або «hours».")

    def _unique_code(self, base, instance=None):
        slug = (slugify(base) or "leave")[:36]
        candidate = slug
        suffix = 1
        qs = LeaveType.objects.all()
        if instance is not None:
            qs = qs.exclude(pk=instance.pk)
        while qs.filter(code=candidate).exists():
            suffix += 1
            candidate = f"{slug}-{suffix}"[:40]
        return candidate

    def create(self, validated_data):
        code = (validated_data.get("code") or "").strip()
        if not code:
            validated_data["code"] = self._unique_code(validated_data.get("name", ""))
        if "order" not in validated_data:
            last = LeaveType.objects.order_by("-order").first()
            validated_data["order"] = (last.order + 1) if last else 1
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "code" in validated_data and not (validated_data["code"] or "").strip():
            validated_data.pop("code")
        return super().update(instance, validated_data)


class LeavePolicyAccrualRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicyAccrualRule
        fields = (
            "id",
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
            "seniority_bonus_levels",
        )
        read_only_fields = ("id",)


class LeavePolicySerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    employee_count = serializers.SerializerMethodField()
    accrual_rule = LeavePolicyAccrualRuleSerializer(required=False)
    type = serializers.CharField(source="policy_type", read_only=True)

    class Meta:
        model = LeavePolicy
        fields = (
            "id",
            "leave_type",
            "leave_type_name",
            "name",
            "legacy_peopleforce_id",
            "policy_type",
            "type",
            "activity_type",
            "counted_as",
            "visibility",
            "instructions_html",
            "deduct_non_working_holidays",
            "allow_on_demand_absence",
            "on_demand_limit",
            "prevent_overlapping_requests",
            "forbid_probation_requests",
            "forbid_breakdown_edit",
            "restrict_adjustments_for_employees",
            "direct_reports_only",
            "min_daily_amount",
            "min_total_amount",
            "max_total_amount",
            "min_notice_days",
            "max_notice_days",
            "approval_enabled",
            "skip_unassigned_approvers",
            "allow_substitute_approvers",
            "approver_steps",
            "allow_negative_balance",
            "limit_negative_balance",
            "max_negative_balance",
            "rounding_method",
            "rounding_precision",
            "allow_withdraw",
            "mandatory_comment",
            "allow_attachments",
            "notify_approver",
            "is_active",
            "employee_count",
            "accrual_rule",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("legacy_peopleforce_id", "created_at", "updated_at", "employee_count")

    def _save_accrual_rule(self, policy, accrual_data):
        rule, _created = LeavePolicyAccrualRule.objects.get_or_create(policy=policy)
        for field, value in accrual_data.items():
            setattr(rule, field, value)
        if policy.policy_type != LeavePolicy.PolicyType.ACCRUAL:
            rule.enabled = False
        self._full_clean(rule)
        rule.save()
        return rule

    def _full_clean(self, instance):
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)

    def get_employee_count(self, obj):
        annotated = getattr(obj, "employee_count", None)
        if annotated is not None:
            return annotated
        return obj.assignments.filter(is_active=True).count()

    def create(self, validated_data):
        accrual_data = validated_data.pop("accrual_rule", {})
        policy = LeavePolicy(**validated_data)
        self._full_clean(policy)
        policy.save()
        self._save_accrual_rule(policy, accrual_data)
        return policy

    def update(self, instance, validated_data):
        accrual_data = validated_data.pop("accrual_rule", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        self._full_clean(instance)
        instance.save()
        if accrual_data is not None:
            self._save_accrual_rule(instance, accrual_data)
        return instance


class LeaveTypeWithPoliciesSerializer(LeaveTypeSerializer):
    policies = LeavePolicySerializer(many=True, read_only=True)

    class Meta(LeaveTypeSerializer.Meta):
        fields = LeaveTypeSerializer.Meta.fields + ("policies",)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = (
            "id",
            "employee",
            "employee_name",
            "leave_type",
            "leave_type_name",
            "legacy_peopleforce_id",
            "effective_on",
            "balance",
            "policy_name",
            "policy_activity_type",
            "policy_counted_as",
        )


class EmployeeLeavePolicyAssignmentSerializer(serializers.ModelSerializer):
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    leave_type = serializers.PrimaryKeyRelatedField(queryset=LeaveType.objects.all(), required=False)
    policy = serializers.PrimaryKeyRelatedField(queryset=LeavePolicy.objects.filter(is_active=True))
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_avatar_url = serializers.CharField(source="employee.avatar_url", read_only=True)
    employee_avatar_local_url = serializers.SerializerMethodField()
    employee_position_name = serializers.CharField(source="employee.position.name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    policy_name = serializers.CharField(source="policy.name", read_only=True)
    policy_type = serializers.CharField(source="policy.policy_type", read_only=True)
    balance = serializers.SerializerMethodField()

    class Meta:
        model = EmployeeLeavePolicyAssignment
        fields = (
            "id",
            "employee",
            "employee_name",
            "employee_avatar_url",
            "employee_avatar_local_url",
            "employee_position_name",
            "leave_type",
            "leave_type_name",
            "policy",
            "policy_name",
            "policy_type",
            "effective_on",
            "ends_on",
            "initial_balance",
            "balance",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at", "balance")

    def get_employee_avatar_local_url(self, obj):
        avatar_file = getattr(obj.employee, "avatar_file", None)
        if not avatar_file:
            return ""
        try:
            return avatar_file.url
        except ValueError:
            return ""

    def get_balance(self, obj):
        return str(current_balance(obj.employee, obj.leave_type))

    def validate(self, attrs):
        policy = attrs.get("policy") or getattr(self.instance, "policy", None)
        leave_type = attrs.get("leave_type") or getattr(self.instance, "leave_type", None)
        if policy and leave_type and policy.leave_type_id != leave_type.id:
            raise serializers.ValidationError({"policy": "Політика має належати вибраному типу відсутності."})
        if policy and not leave_type:
            attrs["leave_type"] = policy.leave_type
        return attrs

    def create(self, validated_data):
        policy = validated_data["policy"]
        return assign_policy_to_employee(
            employee=validated_data["employee"],
            policy=policy,
            effective_on=validated_data["effective_on"],
            initial_balance=validated_data.get("initial_balance", 0),
        )


class LeaveLedgerEntrySerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    policy_name = serializers.CharField(source="policy.name", read_only=True)

    class Meta:
        model = LeaveLedgerEntry
        fields = (
            "id",
            "employee",
            "employee_name",
            "leave_type",
            "leave_type_name",
            "policy",
            "policy_name",
            "assignment",
            "kind",
            "occurred_on",
            "amount",
            "balance_after",
            "description",
            "source_model",
            "source_id",
            "created_at",
        )
        read_only_fields = fields


class LeaveApprovalStepSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(source="approver.get_full_name", read_only=True)

    class Meta:
        model = LeaveApprovalStep
        fields = ("id", "approver", "approver_name", "order", "status", "decided_at", "comment")


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.full_name", read_only=True)
    employee_avatar_url = serializers.CharField(source="employee.avatar_url", read_only=True)
    employee_avatar_local_url = serializers.SerializerMethodField()
    employee_position_name = serializers.CharField(source="employee.position.name", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    approval_steps = LeaveApprovalStepSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = (
            "id",
            "employee",
            "legacy_peopleforce_id",
            "employee_name",
            "employee_avatar_url",
            "employee_avatar_local_url",
            "employee_position_name",
            "leave_type",
            "leave_type_name",
            "date_from",
            "date_to",
            "reason",
            "amount",
            "tracking_time_in",
            "status",
            "submitted_at",
            "decided_at",
            "decided_by",
            "approval_steps",
            "created_at",
        )

    def get_employee_avatar_local_url(self, obj):
        avatar_file = getattr(obj.employee, "avatar_file", None)
        if not avatar_file:
            return ""
        try:
            return avatar_file.url
        except ValueError:
            return ""

    def _request_for_attrs(self, attrs):
        employee = attrs.get("employee") or getattr(self.instance, "employee", None)
        leave_type = attrs.get("leave_type") or getattr(self.instance, "leave_type", None)
        date_from = attrs.get("date_from") or getattr(self.instance, "date_from", None)
        date_to = attrs.get("date_to") or getattr(self.instance, "date_to", None)
        if not employee or not leave_type or not date_from or not date_to:
            return None
        leave_request = LeaveRequest(
            employee=employee,
            leave_type=leave_type,
            date_from=date_from,
            date_to=date_to,
            amount=attrs.get("amount", getattr(self.instance, "amount", None)),
            reason=attrs.get("reason", getattr(self.instance, "reason", "")),
            status=attrs.get("status", getattr(self.instance, "status", LeaveRequest.Status.SUBMITTED)),
        )
        if self.instance:
            leave_request.pk = self.instance.pk
        return leave_request

    def validate(self, attrs):
        date_from = attrs.get("date_from") or getattr(self.instance, "date_from", None)
        date_to = attrs.get("date_to") or getattr(self.instance, "date_to", None)
        if date_from and date_to and date_to < date_from:
            raise serializers.ValidationError({"date_to": "Дата завершення не може бути раніше дати початку."})
        leave_request = self._request_for_attrs(attrs)
        if leave_request:
            request = self.context.get("request")
            try:
                validate_leave_request_policy(leave_request, actor=getattr(request, "user", None))
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        return attrs

    def update(self, instance, validated_data):
        target_status = validated_data.pop("status", None)
        changed_fields = []
        for field, value in validated_data.items():
            setattr(instance, field, value)
            changed_fields.append(field)
        if changed_fields:
            instance.full_clean()
            instance.save(update_fields=changed_fields + ["updated_at"])
        if target_status and target_status != instance.status:
            request = self.context.get("request")
            try:
                return transition_leave_request_status(
                    instance,
                    status=target_status,
                    user=getattr(request, "user", None),
                )
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        return instance
