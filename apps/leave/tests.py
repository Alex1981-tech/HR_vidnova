from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.employees.models import Clinic, Employee, EmployeeEmploymentStatus, Holiday, HolidayPolicy, ManagerAssignment, ProbationPolicy
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

    def test_seniority_bonus_level_accrues_after_threshold(self):
        self.employee.hired_on = date(2025, 1, 1)
        self.employee.save(update_fields=["hired_on"])
        policy = LeavePolicy.objects.create(
            leave_type=self.leave_type,
            name="Відпустка зі стажем",
            policy_type=LeavePolicy.PolicyType.ACCRUAL,
            activity_type=LeavePolicy.ActivityType.NOT_WORKING_PAID,
            counted_as=LeavePolicy.CountedAs.WORKING_DAYS,
        )
        LeavePolicyAccrualRule.objects.create(
            policy=policy,
            enabled=True,
            period_amount=Decimal("2.00"),
            frequency=LeavePolicyAccrualRule.Frequency.MONTHLY,
            accrual_timing=LeavePolicyAccrualRule.AccrualTiming.PERIOD_START,
            seniority_bonus_enabled=True,
            seniority_bonus_levels=[
                {
                    "id": "one-year",
                    "seniority_years": 1,
                    "period_amount": "1.00",
                    "frequency": "monthly",
                    "accrual_timing": "period_start",
                }
            ],
        )
        assignment = EmployeeLeavePolicyAssignment.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            policy=policy,
            effective_on=date(2026, 1, 1),
        )

        sync_assignment_balance(assignment, through_date=date(2026, 2, 28))
        sync_assignment_balance(assignment, through_date=date(2026, 2, 28))

        accruals = LeaveLedgerEntry.objects.filter(assignment=assignment, kind=LeaveLedgerEntry.EntryKind.ACCRUAL)
        self.assertEqual(accruals.count(), 4)
        self.assertEqual(accruals.filter(idempotency_key__contains=":seniority:").count(), 2)
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("6.00"))

    def test_seniority_bonus_level_does_not_accrue_before_threshold(self):
        self.employee.hired_on = date(2026, 1, 1)
        self.employee.save(update_fields=["hired_on"])
        policy = LeavePolicy.objects.create(
            leave_type=self.leave_type,
            name="Відпустка зі стажем пізніше",
            policy_type=LeavePolicy.PolicyType.ACCRUAL,
            activity_type=LeavePolicy.ActivityType.NOT_WORKING_PAID,
            counted_as=LeavePolicy.CountedAs.WORKING_DAYS,
        )
        LeavePolicyAccrualRule.objects.create(
            policy=policy,
            enabled=True,
            period_amount=Decimal("2.00"),
            frequency=LeavePolicyAccrualRule.Frequency.MONTHLY,
            accrual_timing=LeavePolicyAccrualRule.AccrualTiming.PERIOD_START,
            seniority_bonus_enabled=True,
            seniority_bonus_levels=[
                {
                    "id": "one-year",
                    "seniority_years": 1,
                    "period_amount": "1.00",
                    "frequency": "monthly",
                    "accrual_timing": "period_start",
                }
            ],
        )
        assignment = EmployeeLeavePolicyAssignment.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            policy=policy,
            effective_on=date(2026, 1, 1),
        )

        sync_assignment_balance(assignment, through_date=date(2026, 2, 28))

        accruals = LeaveLedgerEntry.objects.filter(assignment=assignment, kind=LeaveLedgerEntry.EntryKind.ACCRUAL)
        self.assertEqual(accruals.count(), 2)
        self.assertEqual(accruals.filter(idempotency_key__contains=":seniority:").count(), 0)
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("4.00"))

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

    def test_policy_api_rejects_invalid_detail_limits(self):
        resp = self.client.post(
            "/api/leave/policies/",
            {
                "leave_type": self.leave_type.id,
                "name": "Некоректний on demand",
                "policy_type": "manual",
                "activity_type": "not_working_paid",
                "counted_as": "calendar_days",
                "allow_on_demand_absence": True,
                "on_demand_limit": "0.00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn("on_demand_limit", resp.data)

        range_resp = self.client.post(
            "/api/leave/policies/",
            {
                "leave_type": self.leave_type.id,
                "name": "Некоректні межі",
                "policy_type": "manual",
                "activity_type": "not_working_paid",
                "counted_as": "calendar_days",
                "min_total_amount": "5.00",
                "max_total_amount": "2.00",
            },
            format="json",
        )
        self.assertEqual(range_resp.status_code, 400, range_resp.data)
        self.assertIn("min_total_amount", range_resp.data)

    def test_policy_api_rejects_invalid_negative_balance_settings(self):
        resp = self.client.post(
            "/api/leave/policies/",
            {
                "leave_type": self.leave_type.id,
                "name": "Некоректний негативний баланс",
                "policy_type": "manual",
                "activity_type": "not_working_paid",
                "counted_as": "calendar_days",
                "allow_negative_balance": True,
                "limit_negative_balance": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn("max_negative_balance", resp.data)

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

    def test_bulk_remove_closes_selected_active_assignment(self):
        policy = LeavePolicy.objects.create(
            leave_type=self.leave_type,
            name="Ручна політика",
            policy_type=LeavePolicy.PolicyType.MANUAL,
            activity_type=LeavePolicy.ActivityType.NOT_WORKING_PAID,
            counted_as=LeavePolicy.CountedAs.WORKING_DAYS,
        )
        assignment = EmployeeLeavePolicyAssignment.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            policy=policy,
            effective_on=date(2026, 1, 1),
        )

        resp = self.client.post(
            "/api/leave/policy-assignments/bulk-remove/",
            {
                "policy": policy.id,
                "employee_ids": [self.employee.id],
                "effective_on": "2026-05-01",
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["updated_assignments"], 1)
        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)
        self.assertEqual(assignment.ends_on, date(2026, 4, 30))

    def test_delete_policy_with_assignments_archives_policy_and_assignments(self):
        policy = LeavePolicy.objects.create(
            leave_type=self.leave_type,
            name="Архівована політика",
            policy_type=LeavePolicy.PolicyType.MANUAL,
            activity_type=LeavePolicy.ActivityType.NOT_WORKING_PAID,
            counted_as=LeavePolicy.CountedAs.WORKING_DAYS,
        )
        assignment = EmployeeLeavePolicyAssignment.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            policy=policy,
            effective_on=date(2026, 1, 1),
        )

        resp = self.client.delete(f"/api/leave/policies/{policy.id}/")

        self.assertEqual(resp.status_code, 204, resp.data)
        policy.refresh_from_db()
        assignment.refresh_from_db()
        self.assertFalse(policy.is_active)
        self.assertFalse(assignment.is_active)
        list_resp = self.client.get("/api/leave/types/with-policies/")
        self.assertEqual(list_resp.status_code, 200, list_resp.data)
        self.assertEqual(list_resp.data[0]["policies"], [])

    def test_delete_leave_type_with_relations_archives_type_policies_and_assignments(self):
        policy = LeavePolicy.objects.create(
            leave_type=self.leave_type,
            name="Політика типу",
            policy_type=LeavePolicy.PolicyType.MANUAL,
            activity_type=LeavePolicy.ActivityType.NOT_WORKING_PAID,
            counted_as=LeavePolicy.CountedAs.WORKING_DAYS,
        )
        assignment = EmployeeLeavePolicyAssignment.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            policy=policy,
            effective_on=date(2026, 1, 1),
        )

        resp = self.client.delete(f"/api/leave/types/{self.leave_type.id}/")

        self.assertEqual(resp.status_code, 204, resp.data)
        self.leave_type.refresh_from_db()
        policy.refresh_from_db()
        assignment.refresh_from_db()
        self.assertFalse(self.leave_type.is_active)
        self.assertFalse(policy.is_active)
        self.assertFalse(assignment.is_active)
        list_resp = self.client.get("/api/leave/types/with-policies/")
        self.assertEqual(list_resp.status_code, 200, list_resp.data)
        self.assertEqual(list_resp.data, [])
        archived_resp = self.client.get("/api/leave/types/?is_active=false")
        self.assertEqual(archived_resp.status_code, 200, archived_resp.data)
        archived_items = archived_resp.data.get("results") if hasattr(archived_resp.data, "get") else archived_resp.data
        self.assertEqual(archived_items[0]["id"], self.leave_type.id)

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

    def test_employee_balance_endpoint_accrues_month_start_after_import_baseline(self):
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
            effective_on=date(2026, 6, 29),
            legacy_peopleforce_id="legacy-balance:month-start",
        )
        LeaveLedgerEntry.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            policy=policy,
            assignment=assignment,
            kind=LeaveLedgerEntry.EntryKind.OPENING,
            occurred_on=date(2026, 6, 29),
            amount=Decimal("7.00"),
            balance_after=Decimal("7.00"),
            idempotency_key="legacy-balance:month-start:opening",
        )

        with patch("apps.leave.services.timezone.localdate", return_value=date(2026, 7, 1)):
            resp = self.client.get(f"/api/leave/balances/?employee={self.employee.id}")

        self.assertEqual(resp.status_code, 200, resp.data)
        accrual = LeaveLedgerEntry.objects.get(assignment=assignment, kind=LeaveLedgerEntry.EntryKind.ACCRUAL)
        self.assertEqual(accrual.occurred_on, date(2026, 7, 1))
        self.assertEqual(accrual.amount, Decimal("2.00"))
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("9.00"))
        balance = LeaveBalance.objects.get(employee=self.employee, leave_type=self.leave_type)
        self.assertEqual(balance.balance, Decimal("9.00"))

    def test_employee_ledger_endpoint_syncs_due_accruals_before_returning(self):
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
            effective_on=date(2026, 6, 29),
            legacy_peopleforce_id="legacy-balance:ledger",
        )
        LeaveLedgerEntry.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            policy=policy,
            assignment=assignment,
            kind=LeaveLedgerEntry.EntryKind.OPENING,
            occurred_on=date(2026, 6, 29),
            amount=Decimal("7.00"),
            balance_after=Decimal("7.00"),
            description="Поточний баланс з PeopleForce на дату імпорту",
            idempotency_key="legacy-balance:ledger:opening",
        )

        with patch("apps.leave.services.timezone.localdate", return_value=date(2026, 7, 1)):
            resp = self.client.get(f"/api/leave/ledger/?employee={self.employee.id}&page_size=1000")

        self.assertEqual(resp.status_code, 200, resp.data)
        items = resp.data.get("results") if hasattr(resp.data, "get") else resp.data
        accruals = [item for item in items if item["kind"] == LeaveLedgerEntry.EntryKind.ACCRUAL]
        self.assertEqual(len(accruals), 1)
        self.assertEqual(accruals[0]["occurred_on"], "2026-07-01")
        self.assertEqual(accruals[0]["amount"], "2.00")
        self.assertEqual(accruals[0]["balance_after"], "9.00")


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

    def test_create_request_respects_policy_total_amount_limits(self):
        self.policy.min_total_amount = Decimal("2.00")
        self.policy.max_total_amount = Decimal("3.00")
        self.policy.save(update_fields=["min_total_amount", "max_total_amount"])

        too_small = self.client.post(
            "/api/leave/requests/",
            {
                "employee": self.employee.id,
                "leave_type": self.leave_type.id,
                "date_from": "2026-07-10",
                "date_to": "2026-07-10",
                "amount": "1.00",
                "status": LeaveRequest.Status.SUBMITTED,
            },
            format="json",
        )
        self.assertEqual(too_small.status_code, 400, too_small.data)
        self.assertIn("amount", too_small.data)

        too_large = self.client.post(
            "/api/leave/requests/",
            {
                "employee": self.employee.id,
                "leave_type": self.leave_type.id,
                "date_from": "2026-07-10",
                "date_to": "2026-07-13",
                "amount": "4.00",
                "status": LeaveRequest.Status.SUBMITTED,
            },
            format="json",
        )
        self.assertEqual(too_large.status_code, 400, too_large.data)
        self.assertIn("amount", too_large.data)

        valid = self.client.post(
            "/api/leave/requests/",
            {
                "employee": self.employee.id,
                "leave_type": self.leave_type.id,
                "date_from": "2026-07-10",
                "date_to": "2026-07-11",
                "amount": "2.00",
                "status": LeaveRequest.Status.SUBMITTED,
            },
            format="json",
        )
        self.assertEqual(valid.status_code, 201, valid.data)

    def test_create_request_respects_policy_min_daily_amount(self):
        self.policy.min_daily_amount = Decimal("1.00")
        self.policy.save(update_fields=["min_daily_amount"])

        resp = self.client.post(
            "/api/leave/requests/",
            {
                "employee": self.employee.id,
                "leave_type": self.leave_type.id,
                "date_from": "2026-07-10",
                "date_to": "2026-07-11",
                "amount": "1.00",
                "status": LeaveRequest.Status.SUBMITTED,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn("amount", resp.data)

    def test_calendar_days_exclude_non_working_holidays_by_default(self):
        holiday_policy = HolidayPolicy.objects.create(name="UA Holidays")
        clinic = Clinic.objects.create(name="Main Clinic", code="main", holiday_policy_ref=holiday_policy)
        self.employee.clinic = clinic
        self.employee.save(update_fields=["clinic"])
        Holiday.objects.create(policy=holiday_policy, name="Свято", occurs_on=date(2026, 7, 11), working=False)
        request = self.make_request(amount=None, date_from=date(2026, 7, 10), date_to=date(2026, 7, 11))

        resp = self.client.post(f"/api/leave/requests/{request.id}/approve/", {}, format="json")

        self.assertEqual(resp.status_code, 200, resp.data)
        request.refresh_from_db()
        self.assertEqual(request.amount, Decimal("1.00"))
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("9.00"))

    def test_calendar_days_can_deduct_non_working_holidays(self):
        holiday_policy = HolidayPolicy.objects.create(name="UA Holidays")
        clinic = Clinic.objects.create(name="Main Clinic", code="main", holiday_policy_ref=holiday_policy)
        self.employee.clinic = clinic
        self.employee.save(update_fields=["clinic"])
        self.policy.deduct_non_working_holidays = True
        self.policy.save(update_fields=["deduct_non_working_holidays"])
        Holiday.objects.create(policy=holiday_policy, name="Свято", occurs_on=date(2026, 7, 11), working=False)
        request = self.make_request(amount=None, date_from=date(2026, 7, 10), date_to=date(2026, 7, 11))

        resp = self.client.post(f"/api/leave/requests/{request.id}/approve/", {}, format="json")

        self.assertEqual(resp.status_code, 200, resp.data)
        request.refresh_from_db()
        self.assertEqual(request.amount, Decimal("2.00"))
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("8.00"))

    def test_negative_balance_can_be_blocked_by_policy(self):
        self.policy.allow_negative_balance = False
        self.policy.save(update_fields=["allow_negative_balance"])

        resp = self.client.post(
            "/api/leave/requests/",
            {
                "employee": self.employee.id,
                "leave_type": self.leave_type.id,
                "date_from": "2026-07-01",
                "date_to": "2026-07-11",
                "status": LeaveRequest.Status.SUBMITTED,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn("amount", resp.data)

    def test_negative_balance_limit_is_enforced(self):
        self.policy.allow_negative_balance = True
        self.policy.limit_negative_balance = True
        self.policy.max_negative_balance = Decimal("2.00")
        self.policy.save(update_fields=["allow_negative_balance", "limit_negative_balance", "max_negative_balance"])

        resp = self.client.post(
            "/api/leave/requests/",
            {
                "employee": self.employee.id,
                "leave_type": self.leave_type.id,
                "date_from": "2026-07-01",
                "date_to": "2026-07-13",
                "status": LeaveRequest.Status.SUBMITTED,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn("amount", resp.data)

    def test_on_demand_limit_is_enforced_when_enabled(self):
        self.policy.allow_on_demand_absence = True
        self.policy.on_demand_limit = Decimal("1.00")
        self.policy.save(update_fields=["allow_on_demand_absence", "on_demand_limit"])

        resp = self.client.post(
            "/api/leave/requests/",
            {
                "employee": self.employee.id,
                "leave_type": self.leave_type.id,
                "date_from": "2026-07-10",
                "date_to": "2026-07-11",
                "status": LeaveRequest.Status.SUBMITTED,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn("amount", resp.data)

    def test_overlapping_requests_are_rejected_when_policy_restricts_them(self):
        self.make_request(date_from=date(2026, 7, 10), date_to=date(2026, 7, 12), status=LeaveRequest.Status.SUBMITTED)

        resp = self.client.post(
            "/api/leave/requests/",
            {
                "employee": self.employee.id,
                "leave_type": self.leave_type.id,
                "date_from": "2026-07-11",
                "date_to": "2026-07-13",
                "status": LeaveRequest.Status.SUBMITTED,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn("date_from", resp.data)

    def test_probation_restriction_is_enforced(self):
        probation = ProbationPolicy.objects.create(name="3 місяці", duration_months=3)
        EmployeeEmploymentStatus.objects.create(
            employee=self.employee,
            effective_from=date(2026, 6, 1),
            probation_policy=probation,
        )
        self.policy.forbid_probation_requests = True
        self.policy.save(update_fields=["forbid_probation_requests"])

        resp = self.client.post(
            "/api/leave/requests/",
            {
                "employee": self.employee.id,
                "leave_type": self.leave_type.id,
                "date_from": "2026-07-10",
                "date_to": "2026-07-10",
                "status": LeaveRequest.Status.SUBMITTED,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn("date_from", resp.data)

    def test_forbid_breakdown_edit_rejects_manual_amount_override(self):
        self.policy.forbid_breakdown_edit = True
        self.policy.save(update_fields=["forbid_breakdown_edit"])

        resp = self.client.post(
            "/api/leave/requests/",
            {
                "employee": self.employee.id,
                "leave_type": self.leave_type.id,
                "date_from": "2026-07-10",
                "date_to": "2026-07-11",
                "amount": "1.00",
                "status": LeaveRequest.Status.SUBMITTED,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, 400, resp.data)
        self.assertIn("amount", resp.data)

    def test_direct_reports_only_restricts_manager_submission_scope(self):
        manager_user = get_user_model().objects.create_user(username="manager", password="test")
        manager = Employee.objects.create(first_name="Іван", last_name="Менеджер", user=manager_user, status=Employee.Status.ACTIVE)
        self.policy.direct_reports_only = True
        self.policy.save(update_fields=["direct_reports_only"])
        self.client.force_authenticate(manager_user)

        denied = self.client.post(
            "/api/leave/requests/",
            {
                "employee": self.employee.id,
                "leave_type": self.leave_type.id,
                "date_from": "2026-07-10",
                "date_to": "2026-07-10",
                "status": LeaveRequest.Status.SUBMITTED,
            },
            format="json",
        )
        self.assertEqual(denied.status_code, 400, denied.data)
        self.assertIn("employee", denied.data)

        ManagerAssignment.objects.create(
            employee=self.employee,
            manager=manager,
            valid_from=date(2026, 1, 1),
            is_primary=True,
        )
        allowed = self.client.post(
            "/api/leave/requests/",
            {
                "employee": self.employee.id,
                "leave_type": self.leave_type.id,
                "date_from": "2026-07-10",
                "date_to": "2026-07-10",
                "status": LeaveRequest.Status.SUBMITTED,
            },
            format="json",
        )
        self.assertEqual(allowed.status_code, 201, allowed.data)

    def test_unpaid_activity_tracks_used_balance_instead_of_available_balance(self):
        self.policy.activity_type = LeavePolicy.ActivityType.NOT_WORKING_UNPAID
        self.policy.save(update_fields=["activity_type"])
        request = self.make_request(amount=None, date_from=date(2026, 7, 10), date_to=date(2026, 7, 11))

        resp = self.client.post(f"/api/leave/requests/{request.id}/approve/", {}, format="json")

        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(current_balance(self.employee, self.leave_type), Decimal("12.00"))

    @override_settings(RBAC_ENFORCE=True)
    def test_delete_request_requires_delete_permission(self):
        request = self.make_request()

        resp = self.client.delete(f"/api/leave/requests/{request.id}/")

        self.assertEqual(resp.status_code, 403)
        self.assertTrue(LeaveRequest.objects.filter(pk=request.id).exists())

    @override_settings(RBAC_ENFORCE=True)
    def test_delete_request_allowed_with_delete_permission(self):
        from apps.access.models import AccessRole, AccessRoleAssignment, AccessRolePermission

        role = AccessRole.objects.create(slug="leave-delete", name="Leave delete")
        AccessRolePermission.objects.create(role=role, permission_code="leave.delete_requests", level="")
        AccessRoleAssignment.objects.create(
            role=role,
            user=self.user,
            scope_type=AccessRoleAssignment.ScopeType.ALL_COMPANY,
        )
        request = self.make_request()

        resp = self.client.delete(f"/api/leave/requests/{request.id}/")

        self.assertEqual(resp.status_code, 204)
        self.assertFalse(LeaveRequest.objects.filter(pk=request.id).exists())
