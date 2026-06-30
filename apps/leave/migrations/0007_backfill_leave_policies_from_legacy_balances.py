from decimal import Decimal

from django.db import migrations
from django.db.models import Sum


def _clean(value, default=""):
    if value is None:
        return default
    return str(value).strip()


def _choice(value, allowed, default):
    value = _clean(value).lower()
    return value if value in allowed else default


def _decimal(value):
    if value is None or value == "":
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _unique_policy_name(LeavePolicy, leave_type, base_name, legacy_id=""):
    name = _clean(base_name) or f"{leave_type.name} ({legacy_id or 'policy'})"
    if not LeavePolicy.objects.filter(leave_type=leave_type, name=name, is_active=True).exists():
        return name
    if legacy_id:
        candidate = f"{name} ({legacy_id})"
        if not LeavePolicy.objects.filter(leave_type=leave_type, name=candidate, is_active=True).exists():
            return candidate
    suffix = 2
    while True:
        candidate = f"{name} {suffix}"
        if not LeavePolicy.objects.filter(leave_type=leave_type, name=candidate, is_active=True).exists():
            return candidate
        suffix += 1


def _policy_payload_from_balance(balance):
    payload = balance.legacy_payload or {}
    return payload.get("leave_type_policy") or {}


def _baseline_on(balance):
    if balance.updated_at:
        return balance.updated_at.date()
    if balance.created_at:
        return balance.created_at.date()
    return balance.effective_on


def _create_accrual_rule(LeavePolicyAccrualRule, policy, payload):
    policy_type = _choice(payload.get("type"), {"accrual", "manual", "external"}, "manual")
    is_vacation = _clean(policy.name).lower() == "відпустка"
    LeavePolicyAccrualRule.objects.get_or_create(
        policy=policy,
        defaults={
            "enabled": policy_type == "accrual" and is_vacation,
            "annual_allowance": Decimal("24.00") if is_vacation else Decimal("0.00"),
            "period_amount": Decimal("2.00") if is_vacation else Decimal("0.00"),
            "frequency": "monthly",
            "accrual_timing": "period_start",
            "first_accrual": "proportional",
            "max_balance": Decimal("24.00") if is_vacation else None,
        },
    )


def forwards(apps, schema_editor):
    LeaveType = apps.get_model("leave", "LeaveType")
    LeavePolicy = apps.get_model("leave", "LeavePolicy")
    LeavePolicyAccrualRule = apps.get_model("leave", "LeavePolicyAccrualRule")
    LeaveBalance = apps.get_model("leave", "LeaveBalance")
    EmployeeLeavePolicyAssignment = apps.get_model("leave", "EmployeeLeavePolicyAssignment")
    LeaveLedgerEntry = apps.get_model("leave", "LeaveLedgerEntry")
    PeopleForceEntity = apps.get_model("integrations", "PeopleForceEntity")

    leave_types_by_pf = {
        _clean(item.legacy_peopleforce_id): item
        for item in LeaveType.objects.exclude(legacy_peopleforce_id="")
    }
    policies_by_pf = {}

    for entity in PeopleForceEntity.objects.filter(entity_type="leave_policies"):
        payload = entity.payload or {}
        legacy_id = _clean(payload.get("id") or entity.external_id)
        leave_type = leave_types_by_pf.get(_clean(payload.get("leave_type_id")))
        if not legacy_id or not leave_type:
            continue
        defaults = {
            "leave_type": leave_type,
            "name": _unique_policy_name(LeavePolicy, leave_type, payload.get("name"), legacy_id),
            "policy_type": _choice(payload.get("type"), {"accrual", "manual", "external"}, "manual"),
            "activity_type": _choice(
                payload.get("activity_type"),
                {"not_working_paid", "not_working_unpaid", "working_paid"},
                "not_working_paid",
            ),
            "counted_as": _choice(payload.get("counted_as"), {"working_days", "calendar_days"}, "working_days"),
            "visibility": "everyone",
            "legacy_payload": payload,
        }
        policy, created = LeavePolicy.objects.get_or_create(
            legacy_peopleforce_id=legacy_id,
            defaults=defaults,
        )
        if not created:
            changed = False
            for field, value in defaults.items():
                if getattr(policy, field) != value:
                    setattr(policy, field, value)
                    changed = True
            if changed:
                policy.save()
        policies_by_pf[legacy_id] = policy
        _create_accrual_rule(LeavePolicyAccrualRule, policy, payload)

    for balance in LeaveBalance.objects.select_related("leave_type", "employee").exclude(policy_name=""):
        policy_payload = _policy_payload_from_balance(balance)
        legacy_id = _clean(policy_payload.get("id"))
        policy = policies_by_pf.get(legacy_id)
        if not policy:
            policy, _created = LeavePolicy.objects.get_or_create(
                legacy_peopleforce_id=legacy_id,
                defaults={
                    "leave_type": balance.leave_type,
                    "name": _unique_policy_name(LeavePolicy, balance.leave_type, balance.policy_name, legacy_id),
                    "policy_type": _choice(policy_payload.get("type"), {"accrual", "manual", "external"}, "manual"),
                    "activity_type": _choice(
                        balance.policy_activity_type or policy_payload.get("activity_type"),
                        {"not_working_paid", "not_working_unpaid", "working_paid"},
                        "not_working_paid",
                    ),
                    "counted_as": _choice(
                        balance.policy_counted_as or policy_payload.get("counted_as"),
                        {"working_days", "calendar_days"},
                        "working_days",
                    ),
                    "visibility": "everyone",
                    "legacy_payload": policy_payload,
                },
            )
            if legacy_id:
                policies_by_pf[legacy_id] = policy
            _create_accrual_rule(LeavePolicyAccrualRule, policy, policy_payload)

        effective_on = balance.effective_on
        if not effective_on:
            continue
        assignment_key = f"legacy-balance:{balance.id}"
        assignment, _created = EmployeeLeavePolicyAssignment.objects.get_or_create(
            legacy_peopleforce_id=assignment_key,
            defaults={
                "employee": balance.employee,
                "leave_type": balance.leave_type,
                "policy": policy,
                "effective_on": effective_on,
                "initial_balance": balance.balance,
                "is_active": True,
            },
        )
        entry_key = f"{assignment_key}:opening"
        if LeaveLedgerEntry.objects.filter(idempotency_key=entry_key).exists():
            continue
        balance_before = (
            LeaveLedgerEntry.objects.filter(employee=balance.employee, leave_type=balance.leave_type).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )
        amount = _decimal(balance.balance)
        baseline_on = _baseline_on(balance)
        LeaveLedgerEntry.objects.create(
            employee=balance.employee,
            leave_type=balance.leave_type,
            policy=policy,
            assignment=assignment,
            kind="opening_balance",
            occurred_on=baseline_on,
            amount=amount,
            balance_after=(balance_before + amount).quantize(Decimal("0.01")),
            description="Поточний баланс з PeopleForce на дату імпорту",
            source_model="LeaveBalance",
            source_id=str(balance.id),
            idempotency_key=entry_key,
        )


def backwards(apps, schema_editor):
    LeavePolicy = apps.get_model("leave", "LeavePolicy")
    EmployeeLeavePolicyAssignment = apps.get_model("leave", "EmployeeLeavePolicyAssignment")
    LeaveLedgerEntry = apps.get_model("leave", "LeaveLedgerEntry")
    LeaveLedgerEntry.objects.filter(idempotency_key__startswith="legacy-balance:").delete()
    EmployeeLeavePolicyAssignment.objects.filter(legacy_peopleforce_id__startswith="legacy-balance:").delete()
    LeavePolicy.objects.filter(legacy_peopleforce_id__isnull=False).exclude(legacy_peopleforce_id="").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0003_peopleforcewebhookevent"),
        ("leave", "0006_employeeleavepolicyassignment_leavepolicy_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
