"""Тесты DRF enforcement RBAC в deny-режиме (RBAC_ENFORCE=True)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.access.models import AccessRole, AccessRoleAssignment
from apps.employees.models import EmergencyContact, Employee


@override_settings(RBAC_ENFORCE=True)
class DrfEnforcementTests(APITestCase):
    def setUp(self):
        call_command("seed_access_roles")
        call_command("seed_access_role_permissions")
        self.user_model = get_user_model()
        self.empA = Employee.objects.create(
            first_name="A", last_name="T", user=self.user_model.objects.create_user("a")
        )
        self.empB = Employee.objects.create(first_name="B", last_name="T")
        self.ecA = EmergencyContact.objects.create(employee=self.empA, name="ICE A")
        self.ecB = EmergencyContact.objects.create(employee=self.empB, name="ICE B")

    def _ids(self, resp):
        data = resp.data
        rows = data["results"] if isinstance(data, dict) and "results" in data else data
        return {r["id"] for r in rows}

    def test_self_sees_only_own_emergency_contacts(self):
        self.client.force_authenticate(self.empA.user)
        resp = self.client.get("/api/employees/emergency-contacts/")
        self.assertEqual(resp.status_code, 200)
        ids = self._ids(resp)
        self.assertIn(self.ecA.id, ids)
        self.assertNotIn(self.ecB.id, ids)

    def test_self_cannot_retrieve_other_emergency_contact(self):
        self.client.force_authenticate(self.empA.user)
        resp = self.client.get(f"/api/employees/emergency-contacts/{self.ecB.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_plain_employee_denied_hr_only_notes(self):
        # people.notes — HR-only; self его не имеет -> 403
        self.client.force_authenticate(self.empA.user)
        resp = self.client.get("/api/employees/employee-notes/")
        self.assertEqual(resp.status_code, 403)

    def test_plain_employee_denied_attendance(self):
        # time.attendance не выдан self -> 403
        self.client.force_authenticate(self.empA.user)
        resp = self.client.get("/api/skud/workdays/")
        self.assertEqual(resp.status_code, 403)

    def test_hr_admin_sees_all_emergency_contacts(self):
        hr_user = self.user_model.objects.create_user("hr")
        Employee.objects.create(first_name="H", last_name="R", user=hr_user)
        AccessRoleAssignment.objects.create(
            role=AccessRole.objects.get(slug="hr_admin"), user=hr_user,
            scope_type=AccessRoleAssignment.ScopeType.ALL_COMPANY,
        )
        self.client.force_authenticate(hr_user)
        resp = self.client.get("/api/employees/emergency-contacts/")
        ids = self._ids(resp)
        self.assertIn(self.ecA.id, ids)
        self.assertIn(self.ecB.id, ids)

    def test_directory_visible_to_all(self):
        # EmployeeViewSet gated на people.directory (all_people=all_company) — каталог не ломается
        self.client.force_authenticate(self.empA.user)
        resp = self.client.get("/api/employees/employees/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.empB.id, self._ids(resp))

    def test_anonymous_denied_when_enforced(self):
        # без public flags аноним не проходит (здесь явно выключим public read)
        with override_settings(HR_PUBLIC_READ_API=False):
            resp = self.client.get("/api/employees/emergency-contacts/")
            self.assertIn(resp.status_code, (401, 403))
