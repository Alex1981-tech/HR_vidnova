from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.employees.models import Employee
from apps.leave.models import (
    EmployeeLeavePolicyAssignment,
    LeaveBalance,
    LeaveLedgerEntry,
    LeavePolicy,
    LeavePolicyAccrualRule,
    LeaveRequest,
    LeaveType,
)
from apps.leave.services import current_balance, sync_assignment_balance


class LeaveTypeUnitApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr", password="test")
        self.client.force_authenticate(self.user)

    def test_create_defaults_to_days(self):
        resp = self.client.post("/api/leave/types/", {"name": "Відпустка"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["unit"], "days")

    def test_hours_accepted(self):
        resp = self.client.post(
            "/api/leave/types/", {"name": "Лікарняний", "unit": "hours"}, format="json"
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["unit"], "hours")

    def test_legacy_unit_normalized(self):
        resp = self.client.post(
            "/api/leave/types/", {"name": "Декрет", "unit": "Day"}, format="json"
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["unit"], "days")

    def test_invalid_unit_rejected(self):
        resp = self.client.post(
            "/api/leave/types/", {"name": "Інше", "unit": "тижні"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)


class LeavePolicyAccrualTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr-policy", password="test")
        self.client.force_authenticate(self.user)
        self.employee = Employee.objects.create(first_name="Олена", last_name="Коваль", status=Employee.Status.ACTIVE)
        self.leave_type = LeaveType.objects.create(name="Відпустка", code="vacation", unit=LeaveType.TrackingUnit.DAYS)

    def test_monthly_accrual_posts_idempotent_ledger_entries(self):
        policy = LeavePolicy.objects.create(
            leave_type=self.leave_type,
            name="24 дні на рік",
            policy_type=LeavePolicy.PolicyType.ACCRUAL,
            activity_type=LeavePolicy.ActivityType.NOT_WORKING_PAID,
            counted_as=LeavePolicy.CountedAs.WORKING_DAYS,
        )
        LeavePolicyAccrualRule.objects.create(
            policy=policy,
            enabled=True,
            annual_allowance=Decimal("24.00"),
            period_amount=Decimal("2.00"),
            frequency=LeavePolicyAccrualRule.Frequency.MONTHLY,
            accrual_timing=LeavePolicyAccrualRule.AccrualTiming.PERIOD_START,
        )
        assignment = EmployeeLeavePolicyAssignment.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            policy=policy,
            effective_on=date(2026, 1, 1),
        )

        sync_assignment_balance(assignment, through_date=date(2026, 3, 31))
        sync_assignment_balance(assignment, through_date=date(2026, 3, 31))

        accruals = LeaveLedgerEntry.objects.filter(assignment=assignment, kind=LeaveLedgerEntry.EntryKind.ACCRUAL)
        self.assertEqual(accruals.count(), 3)
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("6.00"))
        balance = LeaveBalance.objects.get(employee=self.employee, leave_type=self.leave_type, legacy_peopleforce_id=f"assignment:{assignment.id}")
        self.assertEqual(balance.balance, Decimal("6.00"))
        self.assertEqual(balance.policy_name, "24 дні на рік")

    def test_policy_api_exposes_type_with_nested_policies(self):
        resp = self.client.post(
            "/api/leave/policies/",
            {
                "leave_type": self.leave_type.id,
                "name": "Щорічна відпустка",
                "policy_type": "accrual",
                "activity_type": "not_working_paid",
                "counted_as": "working_days",
                "accrual_rule": {
                    "enabled": True,
                    "annual_allowance": "24.00",
                    "period_amount": "2.00",
                    "frequency": "monthly",
                    "accrual_timing": "period_start",
                },
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["policy_type"], "accrual")
        self.assertEqual(resp.data["accrual_rule"]["period_amount"], "2.00")

        list_resp = self.client.get("/api/leave/types/with-policies/")
        self.assertEqual(list_resp.status_code, 200, list_resp.data)
        self.assertEqual(list_resp.data[0]["policies"][0]["name"], "Щорічна відпустка")
        self.assertEqual(list_resp.data[0]["policies"][0]["employee_count"], 0)

    def test_bulk_assign_creates_assignment_and_balance_cache(self):
        policy = LeavePolicy.objects.create(
            leave_type=self.leave_type,
            name="Без нарахування",
            policy_type=LeavePolicy.PolicyType.MANUAL,
            activity_type=LeavePolicy.ActivityType.NOT_WORKING_PAID,
            counted_as=LeavePolicy.CountedAs.WORKING_DAYS,
        )
        resp = self.client.post(
            "/api/leave/policy-assignments/bulk-assign/",
            {
                "policy": policy.id,
                "employee_ids": [self.employee.id],
                "effective_on": "2026-01-01",
                "initial_balance": "3.00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(len(resp.data["assignments"]), 1)
        assignment = EmployeeLeavePolicyAssignment.objects.get(policy=policy, employee=self.employee)
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("3.00"))
        self.assertEqual(str(assignment.initial_balance), "3.00")

    def test_legacy_import_opening_is_used_as_accrual_baseline(self):
        policy = LeavePolicy.objects.create(
            leave_type=self.leave_type,
            name="Імпортована відпустка",
            policy_type=LeavePolicy.PolicyType.ACCRUAL,
            activity_type=LeavePolicy.ActivityType.NOT_WORKING_PAID,
            counted_as=LeavePolicy.CountedAs.CALENDAR_DAYS,
        )
        LeavePolicyAccrualRule.objects.create(
            policy=policy,
            enabled=True,
            annual_allowance=Decimal("24.00"),
            period_amount=Decimal("2.00"),
            frequency=LeavePolicyAccrualRule.Frequency.MONTHLY,
            accrual_timing=LeavePolicyAccrualRule.AccrualTiming.PERIOD_START,
        )
        assignment = EmployeeLeavePolicyAssignment.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            policy=policy,
            effective_on=date(2026, 1, 1),
            initial_balance=Decimal("12.00"),
            legacy_peopleforce_id="legacy-balance:1",
        )
        LeaveLedgerEntry.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            policy=policy,
            assignment=assignment,
            kind=LeaveLedgerEntry.EntryKind.OPENING,
            occurred_on=date(2026, 6, 30),
            amount=Decimal("12.00"),
            balance_after=Decimal("12.00"),
            idempotency_key="legacy-balance:1:opening",
        )

        sync_assignment_balance(assignment, through_date=date(2026, 6, 30))
        self.assertEqual(LeaveLedgerEntry.objects.filter(assignment=assignment, kind=LeaveLedgerEntry.EntryKind.OPENING).count(), 1)
        self.assertEqual(LeaveLedgerEntry.objects.filter(assignment=assignment, kind=LeaveLedgerEntry.EntryKind.ACCRUAL).count(), 0)
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("12.00"))

        sync_assignment_balance(assignment, through_date=date(2026, 7, 31))
        self.assertEqual(LeaveLedgerEntry.objects.filter(assignment=assignment, kind=LeaveLedgerEntry.EntryKind.ACCRUAL).count(), 1)
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("14.00"))


class LeaveRequestLedgerLifecycleTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr-requests", password="test")
        self.client.force_authenticate(self.user)
        self.employee = Employee.objects.create(first_name="Марія", last_name="Шевченко", status=Employee.Status.ACTIVE)
        self.leave_type = LeaveType.objects.create(name="Відпустка", code="request-vacation", unit=LeaveType.TrackingUnit.DAYS)
        self.policy = LeavePolicy.objects.create(
            leave_type=self.leave_type,
            name="Ручний баланс",
            policy_type=LeavePolicy.PolicyType.MANUAL,
            activity_type=LeavePolicy.ActivityType.NOT_WORKING_PAID,
            counted_as=LeavePolicy.CountedAs.CALENDAR_DAYS,
        )
        self.assignment = EmployeeLeavePolicyAssignment.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            policy=self.policy,
            effective_on=date(2026, 1, 1),
            initial_balance=Decimal("10.00"),
        )
        sync_assignment_balance(self.assignment, through_date=date(2026, 6, 30))

    def make_request(self, **overrides):
        values = {
            "employee": self.employee,
            "leave_type": self.leave_type,
            "date_from": date(2026, 7, 1),
            "date_to": date(2026, 7, 2),
            "amount": Decimal("2.00"),
            "status": LeaveRequest.Status.SUBMITTED,
        }
        values.update(overrides)
        return LeaveRequest.objects.create(**values)

    def test_approve_posts_request_ledger_and_updates_balance(self):
        request = self.make_request()

        resp = self.client.post(f"/api/leave/requests/{request.id}/approve/", {}, format="json")

        self.assertEqual(resp.status_code, 200, resp.data)
        request.refresh_from_db()
        self.assertEqual(request.status, LeaveRequest.Status.APPROVED)
        self.assertEqual(request.decided_by, self.user)
        entries = LeaveLedgerEntry.objects.filter(
            source_model="LeaveRequest",
            source_id=str(request.id),
            kind=LeaveLedgerEntry.EntryKind.REQUEST,
        )
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.get().amount, Decimal("-2.00"))
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("8.00"))
        balance = LeaveBalance.objects.get(
            employee=self.employee,
            leave_type=self.leave_type,
            legacy_peopleforce_id=f"assignment:{self.assignment.id}",
        )
        self.assertEqual(balance.balance, Decimal("8.00"))

        second = self.client.post(f"/api/leave/requests/{request.id}/approve/", {}, format="json")
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(entries.count(), 1)
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("8.00"))

    def test_cancel_after_approval_returns_balance_once(self):
        request = self.make_request()
        self.client.post(f"/api/leave/requests/{request.id}/approve/", {}, format="json")

        resp = self.client.post(f"/api/leave/requests/{request.id}/cancel/", {"comment": "помилка"}, format="json")

        self.assertEqual(resp.status_code, 200, resp.data)
        request.refresh_from_db()
        self.assertEqual(request.status, LeaveRequest.Status.CANCELLED)
        adjustment = LeaveLedgerEntry.objects.get(
            source_model="LeaveRequest",
            source_id=str(request.id),
            kind=LeaveLedgerEntry.EntryKind.ADJUSTMENT,
        )
        self.assertEqual(adjustment.amount, Decimal("2.00"))
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("10.00"))

        second = self.client.post(f"/api/leave/requests/{request.id}/cancel/", {}, format="json")
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(
            LeaveLedgerEntry.objects.filter(
                source_model="LeaveRequest",
                source_id=str(request.id),
                kind=LeaveLedgerEntry.EntryKind.ADJUSTMENT,
            ).count(),
            1,
        )
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("10.00"))

    def test_reject_submitted_request_does_not_touch_balance(self):
        request = self.make_request()

        resp = self.client.post(f"/api/leave/requests/{request.id}/reject/", {}, format="json")

        self.assertEqual(resp.status_code, 200, resp.data)
        request.refresh_from_db()
        self.assertEqual(request.status, LeaveRequest.Status.REJECTED)
        self.assertFalse(
            LeaveLedgerEntry.objects.filter(source_model="LeaveRequest", source_id=str(request.id)).exists()
        )
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("10.00"))

    def test_patch_status_uses_same_ledger_lifecycle(self):
        request = self.make_request(amount=None, date_from=date(2026, 7, 6), date_to=date(2026, 7, 8))

        resp = self.client.patch(f"/api/leave/requests/{request.id}/", {"status": "approved"}, format="json")

        self.assertEqual(resp.status_code, 200, resp.data)
        request.refresh_from_db()
        self.assertEqual(request.status, LeaveRequest.Status.APPROVED)
        self.assertEqual(request.amount, Decimal("3.00"))
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("7.00"))

    def test_approve_without_assigned_policy_is_rejected(self):
        EmployeeLeavePolicyAssignment.objects.all().delete()
        request = self.make_request()

        resp = self.client.post(f"/api/leave/requests/{request.id}/approve/", {}, format="json")

        self.assertEqual(resp.status_code, 400, resp.data)
        request.refresh_from_db()
        self.assertEqual(request.status, LeaveRequest.Status.SUBMITTED)
        self.assertFalse(
            LeaveLedgerEntry.objects.filter(source_model="LeaveRequest", source_id=str(request.id)).exists()
        )
