"""Тесты утверждённой матрицы прав ролей (RBAC)."""

from __future__ import annotations

from django.core.management import call_command
from django.test import TestCase

from apps.access import rbac
from apps.access.models import AccessRole
from apps.access.permissions_registry import AccessLevel, get_permission
from apps.access.role_matrix import ROLE_PERMISSIONS
from apps.access.role_seeds import SYSTEM_ROLE_SEEDS


class RoleMatrixValidityTests(TestCase):
    """Матрица должна ссылаться только на существующие коды с корректным уровнем."""

    def test_all_codes_exist_and_levels_valid(self):
        valid_levels = {level.value for level in AccessLevel}
        for slug, grants in ROLE_PERMISSIONS.items():
            seen = set()
            for code, level in grants:
                perm = get_permission(code)
                self.assertIsNotNone(perm, f"{slug}: unknown code {code}")
                self.assertNotIn(code, seen, f"{slug}: duplicate code {code}")
                seen.add(code)
                if perm.is_graded:
                    self.assertIn(level, valid_levels, f"{slug}/{code}: bad level {level!r}")
                else:
                    self.assertEqual(level, "", f"{slug}/{code}: atomic must have empty level")

    def test_admin_not_in_matrix(self):
        # admin — bypass, не должен наполняться через матрицу.
        self.assertNotIn("admin", ROLE_PERMISSIONS)

    def test_matrix_roles_are_seeded(self):
        seeded = {seed["slug"] for seed in SYSTEM_ROLE_SEEDS}
        for slug in ROLE_PERMISSIONS:
            self.assertIn(slug, seeded, f"matrix role {slug} not in seeds")


class SeedRolePermissionsTests(TestCase):
    def setUp(self):
        call_command("seed_access_roles")

    def test_seed_idempotent_and_matches_matrix(self):
        call_command("seed_access_role_permissions")
        for slug, grants in ROLE_PERMISSIONS.items():
            role = AccessRole.objects.get(slug=slug)
            actual = {(p.permission_code, p.level) for p in role.permissions.all()}
            expected = {(code, level) for code, level in grants}
            self.assertEqual(actual, expected, f"{slug} grants mismatch")
        # повторный запуск ничего не меняет
        call_command("seed_access_role_permissions")
        total = sum(len(g) for g in ROLE_PERMISSIONS.values())
        from apps.access.models import AccessRolePermission

        self.assertEqual(AccessRolePermission.objects.count(), total)

    def test_decisions_applied(self):
        call_command("seed_access_role_permissions")
        # #5 компенсация: системные роли (self/manager/all_people) её НЕ видят
        # (HR-доступ к компенсации даётся кастомным ролям, создаются админом).
        self.assertIsNone(self._level("self", "people.field.compensation"))
        self.assertIsNone(self._level("manager", "people.field.compensation"))
        self.assertIsNone(self._level("all_people", "people.field.compensation"))
        # #1 manager attendance присутствует (scope reports — это уже в engine)
        self.assertEqual(self._level("manager", "time.attendance"), "view")
        # #2 roles.manage не выдан ни одной роли матрицы
        for slug in ROLE_PERMISSIONS:
            self.assertIsNone(self._level(slug, "roles.manage"))

    def _level(self, slug, code):
        role = AccessRole.objects.get(slug=slug)
        perm = role.permissions.filter(permission_code=code).first()
        return perm.level if perm else None


class MatrixEnforcementSmokeTests(TestCase):
    """После seed реальные has_perm/scope соответствуют матрице (через движок)."""

    def setUp(self):
        call_command("seed_access_roles")
        call_command("seed_access_role_permissions")
        from django.contrib.auth import get_user_model

        from apps.employees.models import Employee, ManagerAssignment
        from django.utils import timezone

        self.user_model = get_user_model()
        self.mgr = Employee.objects.create(
            first_name="M", last_name="T",
            user=self.user_model.objects.create_user("m"),
        )
        self.report = Employee.objects.create(first_name="R", last_name="T")
        self.outsider = Employee.objects.create(first_name="O", last_name="T")
        ManagerAssignment.objects.create(
            manager=self.mgr, employee=self.report,
            valid_from=timezone.localdate(), is_primary=True,
        )

    def test_manager_sees_report_attendance_not_outsider(self):
        # manager имеет time.attendance (view) в scope подчинённых
        self.assertTrue(rbac.has_perm(self.mgr.user, "time.attendance", employee=self.report))
        self.assertFalse(rbac.has_perm(self.mgr.user, "time.attendance", employee=self.outsider))

    def test_self_cannot_see_compensation(self):
        emp = self.user_model.objects.create_user("s")
        from apps.employees.models import Employee

        Employee.objects.create(first_name="S", last_name="T", user=emp)
        self.assertFalse(rbac.has_perm(emp, "people.field.compensation", level="view"))
