"""Тесты RBAC management API (Этап 6)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.access.models import AccessRole, AccessRoleAssignment, AccessRoleAuditEvent
from apps.access.role_seeds import ADMIN_ROLE_SLUG, SYSTEM_ROLE_SEEDS


class RbacApiTests(APITestCase):
    def setUp(self):
        call_command("seed_access_roles")
        call_command("seed_access_role_permissions")
        self.user_model = get_user_model()
        self.admin = self.user_model.objects.create_superuser("root", "r@r.com", "pass")

    def _as_admin(self):
        self.client.force_authenticate(self.admin)

    # ── доступ ───────────────────────────────────────────────────────────────
    def test_non_admin_denied(self):
        plain = self.user_model.objects.create_user("plain")
        self.client.force_authenticate(plain)
        self.assertEqual(self.client.get("/api/access/roles/").status_code, 403)

    def test_roles_list(self):
        self._as_admin()
        resp = self.client.get("/api/access/roles/")
        self.assertEqual(resp.status_code, 200)
        rows = resp.data["results"] if "results" in resp.data else resp.data
        slugs = {r["slug"] for r in rows}
        self.assertEqual(slugs, {s["slug"] for s in SYSTEM_ROLE_SEEDS})
        self.assertIn("people_count", rows[0])

    def test_permission_catalog(self):
        self._as_admin()
        resp = self.client.get("/api/access/permissions/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("groups", resp.data)
        self.assertTrue(resp.data["groups"])

    # ── роли ─────────────────────────────────────────────────────────────────
    def test_create_custom_role(self):
        self._as_admin()
        resp = self.client.post("/api/access/roles/", {"name": "Аудитори"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["type"], "custom")
        self.assertTrue(resp.data["slug"])

    def test_cannot_delete_system_role(self):
        self._as_admin()
        role = AccessRole.objects.get(slug="hr_admin")
        resp = self.client.delete(f"/api/access/roles/{role.id}/")
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(AccessRole.objects.filter(slug="hr_admin").exists())

    def test_custom_role_deletable(self):
        self._as_admin()
        rid = self.client.post("/api/access/roles/", {"name": "Тимчасова"}, format="json").data["id"]
        self.assertEqual(self.client.delete(f"/api/access/roles/{rid}/").status_code, 204)

    def test_set_permissions_and_audit(self):
        self._as_admin()
        rid = self.client.post("/api/access/roles/", {"name": "Контент"}, format="json").data["id"]
        resp = self.client.post(
            f"/api/access/roles/{rid}/set-permissions/",
            [{"permission_code": "knowledge.read", "level": "view"},
             {"permission_code": "knowledge.manage", "level": ""}],
            format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        codes = {p["permission_code"] for p in resp.data["permissions"]}
        self.assertEqual(codes, {"knowledge.read", "knowledge.manage"})
        self.assertTrue(
            AccessRoleAuditEvent.objects.filter(action=AccessRoleAuditEvent.Action.PERMISSION_GRANTED).exists()
        )

    def test_set_permissions_rejects_unknown_code(self):
        self._as_admin()
        rid = self.client.post("/api/access/roles/", {"name": "X"}, format="json").data["id"]
        resp = self.client.post(
            f"/api/access/roles/{rid}/set-permissions/",
            [{"permission_code": "nope.nope", "level": ""}], format="json",
        )
        self.assertEqual(resp.status_code, 400)

    # ── назначения + last-admin ───────────────────────────────────────────────
    def test_assignment_create_and_last_admin_guard(self):
        self._as_admin()
        admin_role = AccessRole.objects.get(slug=ADMIN_ROLE_SLUG)
        u = self.user_model.objects.create_user("a1")
        created = self.client.post(
            "/api/access/assignments/",
            {"role": admin_role.id, "user": u.id, "scope_type": "all_company"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        # единственное admin-назначение нельзя удалить
        resp = self.client.delete(f"/api/access/assignments/{created.data['id']}/")
        self.assertEqual(resp.status_code, 400)

    def test_assignment_delete_when_not_last_admin(self):
        self._as_admin()
        admin_role = AccessRole.objects.get(slug=ADMIN_ROLE_SLUG)
        a1 = AccessRoleAssignment.objects.create(
            role=admin_role, user=self.user_model.objects.create_user("a1"),
            scope_type="all_company",
        )
        AccessRoleAssignment.objects.create(
            role=admin_role, user=self.user_model.objects.create_user("a2"),
            scope_type="all_company",
        )
        self.assertEqual(self.client.delete(f"/api/access/assignments/{a1.id}/").status_code, 204)

    # ── preview + audit ───────────────────────────────────────────────────────
    def test_effective_preview_all_company(self):
        self._as_admin()
        from apps.employees.models import Employee

        Employee.objects.create(first_name="A", last_name="T")
        Employee.objects.create(first_name="B", last_name="T")
        resp = self.client.post(
            "/api/access/effective-preview/", {"scope_type": "all_company"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data["all_company"])
        self.assertEqual(resp.data["count"], Employee.objects.count())

    def test_audit_list(self):
        self._as_admin()
        self.client.post("/api/access/roles/", {"name": "Z"}, format="json")
        resp = self.client.get("/api/access/audit/")
        self.assertEqual(resp.status_code, 200)
        rows = resp.data["results"] if "results" in resp.data else resp.data
        self.assertTrue(rows)

    # ── AuthStatus.access (Этап 5) ────────────────────────────────────────────
    def test_auth_status_exposes_access(self):
        from apps.employees.models import Employee

        u = self.user_model.objects.create_user("emp")
        Employee.objects.create(first_name="E", last_name="T", user=u)
        self.client.force_authenticate(u)
        resp = self.client.get("/api/auth/status/")
        self.assertEqual(resp.status_code, 200)
        access = resp.data["access"]
        self.assertIn("self", access["roles"])
        self.assertIn("all_people", access["roles"])
        self.assertIn("is_admin", access)
        self.assertIn("permissions", access)
        self.assertFalse(access["enforced"])  # default shadow

    def test_auth_status_admin_flag(self):
        self._as_admin()
        resp = self.client.get("/api/auth/status/")
        self.assertTrue(resp.data["access"]["is_admin"])  # superuser
