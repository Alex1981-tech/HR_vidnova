"""Тесты permission service + scope engine (RBAC, Этап 3)."""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.access import rbac
from apps.access.models import AccessRole, AccessRoleAssignment, AccessRolePermission
from apps.access.role_seeds import ADMIN_ROLE_SLUG
from apps.employees.models import (
    Employee,
    EmployeeField,
    EmployeeFieldGroup,
    ManagerAssignment,
    Team,
    TeamMembership,
)


def _grant(role_slug, code, level=""):
    role = AccessRole.objects.get(slug=role_slug)
    return AccessRolePermission.objects.create(role=role, permission_code=code, level=level)


class ScopeEngineTests(TestCase):
    def setUp(self):
        call_command("seed_access_roles")
        self.today = timezone.localdate()
        self.user_model = get_user_model()

    def _emp(self, name, *, user=False, status=Employee.Status.ACTIVE):
        u = self.user_model.objects.create_user(name) if user else None
        return Employee.objects.create(first_name=name, last_name="T", status=status, user=u)

    def _manage(self, manager, report):
        ManagerAssignment.objects.create(
            manager=manager, employee=report,
            valid_from=self.today - timedelta(days=10), is_primary=True,
        )

    # ── computed roles ───────────────────────────────────────────────────────
    def test_self_role_scope_only_self(self):
        emp = self._emp("self", user=True)
        other = self._emp("other")
        _grant("self", "people.field.personal", "edit")
        qs = rbac.employee_scope_queryset(emp.user, "people.field.personal")
        self.assertEqual(set(qs.values_list("id", flat=True)), {emp.id})
        self.assertNotIn(other.id, set(qs.values_list("id", flat=True)))

    def test_manager_scope_direct_and_indirect(self):
        mgr = self._emp("mgr", user=True)
        r1 = self._emp("r1")
        r2 = self._emp("r2")
        r11 = self._emp("r11")
        sibling = self._emp("sibling")
        self._manage(mgr, r1)
        self._manage(mgr, r2)
        self._manage(r1, r11)
        _grant("manager", "people.profile", "view")
        qs = rbac.employee_scope_queryset(mgr.user, "people.profile")
        self.assertEqual(set(qs.values_list("id", flat=True)), {r1.id, r2.id, r11.id})
        self.assertNotIn(sibling.id, set(qs.values_list("id", flat=True)))
        self.assertNotIn(mgr.id, set(qs.values_list("id", flat=True)))

    def test_manager_cycle_terminates(self):
        a = self._emp("a", user=True)
        b = self._emp("b")
        self._manage(a, b)
        self._manage(b, a)  # цикл
        reports = rbac.all_report_ids(a.id)
        self.assertEqual(reports, {b.id})  # без бесконечного цикла

    def test_team_lead_scope_active_members_only(self):
        lead = self._emp("lead", user=True)
        m1 = self._emp("m1")
        m2 = self._emp("m2")
        team = Team.objects.create(name="T", lead=lead, is_active=True)
        TeamMembership.objects.create(team=team, employee=m1, is_active=True)
        TeamMembership.objects.create(team=team, employee=m2, is_active=False)
        _grant("team_lead", "people.profile", "view")
        qs = rbac.employee_scope_queryset(lead.user, "people.profile")
        self.assertEqual(set(qs.values_list("id", flat=True)), {m1.id})

    def test_admin_scope_all_company(self):
        admin_emp = self._emp("admin", user=True)
        self._emp("x")
        self._emp("y")
        AccessRoleAssignment.objects.create(
            role=AccessRole.objects.get(slug=ADMIN_ROLE_SLUG), user=admin_emp.user,
            scope_type=AccessRoleAssignment.ScopeType.ALL_COMPANY,
        )
        _grant(ADMIN_ROLE_SLUG, "people.profile", "view")
        qs = rbac.employee_scope_queryset(admin_emp.user, "people.profile")
        self.assertEqual(qs.count(), Employee.objects.count())

    def test_empty_scope_for_ungranted_code(self):
        emp = self._emp("plain", user=True)
        qs = rbac.employee_scope_queryset(emp.user, "people.profile")
        self.assertEqual(qs.count(), 0)

    # ── roles / permissions ──────────────────────────────────────────────────
    def test_inactive_employee_no_all_people_role(self):
        emp = self._emp("inact", user=True, status=Employee.Status.DISMISSED)
        roles = rbac.get_effective_roles(emp.user)
        self.assertIn("self", roles)
        self.assertNotIn("all_people", roles)

    def test_active_employee_has_self_and_all_people(self):
        emp = self._emp("act", user=True)
        roles = rbac.get_effective_roles(emp.user)
        self.assertIn("self", roles)
        self.assertIn("all_people", roles)

    def test_has_perm_level_expansion(self):
        emp = self._emp("ed", user=True)
        _grant("self", "people.field.personal", "edit")
        self.assertTrue(rbac.has_perm(emp.user, "people.field.personal", level="edit"))
        self.assertTrue(rbac.has_perm(emp.user, "people.field.personal", level="view"))  # edit -> view
        self.assertFalse(rbac.has_perm(emp.user, "people.profile"))

    def test_has_perm_object_level(self):
        mgr = self._emp("m", user=True)
        report = self._emp("rep")
        outsider = self._emp("out")
        self._manage(mgr, report)
        _grant("manager", "people.profile", "view")
        self.assertTrue(rbac.has_perm(mgr.user, "people.profile", employee=report))
        self.assertFalse(rbac.has_perm(mgr.user, "people.profile", employee=outsider))

    def test_anonymous_has_nothing(self):
        from django.contrib.auth.models import AnonymousUser

        anon = AnonymousUser()
        self.assertEqual(rbac.get_effective_roles(anon), set())
        self.assertFalse(rbac.has_perm(anon, "people.profile"))
        self.assertEqual(rbac.employee_scope_queryset(anon, "people.profile").count(), 0)


class FieldAccessTests(TestCase):
    def setUp(self):
        call_command("seed_access_roles")
        self.user_model = get_user_model()
        self.group_personal = EmployeeFieldGroup.objects.create(
            tab=EmployeeFieldGroup.Tab.PERSONAL, name="Особисте", is_system=True
        )
        self.field = EmployeeField.objects.create(
            group=self.group_personal, name="Дата народження", is_system=True, is_enabled=True
        )

    def _emp(self, name, *, user=False):
        u = self.user_model.objects.create_user(name) if user else None
        return Employee.objects.create(first_name=name, last_name="T", user=u)

    def test_self_edit_on_own_personal_field(self):
        emp = self._emp("self", user=True)
        _grant("self", "people.field.personal", "edit")
        self.assertEqual(rbac.field_access(emp.user, emp, self.field), "edit")

    def test_no_access_on_other_employee_field(self):
        emp = self._emp("self", user=True)
        other = self._emp("other")
        _grant("self", "people.field.personal", "edit")
        self.assertEqual(rbac.field_access(emp.user, other, self.field), "none")

    def test_disabled_field_hidden(self):
        emp = self._emp("self", user=True)
        _grant("self", "people.field.personal", "view")
        self.field.is_enabled = False
        self.field.save(update_fields=["is_enabled"])
        self.assertEqual(rbac.field_access(emp.user, emp, self.field), "none")
