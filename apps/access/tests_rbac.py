"""Тесты RBAC моделей и инвариантов (Этап 2)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.access.models import AccessRole, AccessRoleAssignment, AccessRolePermission
from apps.access.rbac_invariants import assert_admin_remains, would_remove_last_admin
from apps.access.role_seeds import ADMIN_ROLE_SLUG, SYSTEM_ROLE_SEEDS


class AccessRoleConstraintTests(TestCase):
    def test_unique_slug(self):
        AccessRole.objects.create(slug="x", name="X")
        with self.assertRaises(IntegrityError), transaction.atomic():
            AccessRole.objects.create(slug="x", name="Y")

    def test_cannot_delete_system_role(self):
        role = AccessRole.objects.create(slug="sys", name="Sys", type=AccessRole.Type.SYSTEM)
        with self.assertRaises(ValidationError):
            role.delete()
        self.assertTrue(AccessRole.objects.filter(slug="sys").exists())

    def test_custom_role_deletable(self):
        role = AccessRole.objects.create(slug="cust", name="Cust", type=AccessRole.Type.CUSTOM)
        role.delete()
        self.assertFalse(AccessRole.objects.filter(slug="cust").exists())


class AccessRolePermissionTests(TestCase):
    def setUp(self):
        self.role = AccessRole.objects.create(slug="r", name="R")

    def test_unknown_permission_code_rejected(self):
        with self.assertRaises(ValidationError):
            AccessRolePermission.objects.create(role=self.role, permission_code="nope.nope")

    def test_graded_requires_valid_level(self):
        with self.assertRaises(ValidationError):
            AccessRolePermission.objects.create(role=self.role, permission_code="people.profile")
        with self.assertRaises(ValidationError):
            AccessRolePermission.objects.create(
                role=self.role, permission_code="people.profile", level="delete"
            )
        ok = AccessRolePermission.objects.create(
            role=self.role, permission_code="people.profile", level="edit"
        )
        self.assertEqual(ok.level, "edit")

    def test_atomic_rejects_level(self):
        with self.assertRaises(ValidationError):
            AccessRolePermission.objects.create(
                role=self.role, permission_code="people.delete", level="view"
            )
        ok = AccessRolePermission.objects.create(role=self.role, permission_code="people.delete")
        self.assertEqual(ok.level, "")

    def test_duplicate_permission_blocked(self):
        AccessRolePermission.objects.create(role=self.role, permission_code="people.delete")
        with self.assertRaises(IntegrityError), transaction.atomic():
            AccessRolePermission.objects.create(role=self.role, permission_code="people.delete")


class LastAdminInvariantTests(TestCase):
    def setUp(self):
        call_command("seed_access_roles")
        self.admin_role = AccessRole.objects.get(slug=ADMIN_ROLE_SLUG)
        self.user_model = get_user_model()

    def _assign(self, role, user):
        return AccessRoleAssignment.objects.create(
            role=role, user=user, scope_type=AccessRoleAssignment.ScopeType.ALL_COMPANY
        )

    def test_single_admin_is_last(self):
        assignment = self._assign(self.admin_role, self.user_model.objects.create_user("a1"))
        self.assertTrue(would_remove_last_admin(assignment))
        with self.assertRaises(ValidationError):
            assert_admin_remains(assignment)

    def test_two_admins_not_last(self):
        first = self._assign(self.admin_role, self.user_model.objects.create_user("a1"))
        self._assign(self.admin_role, self.user_model.objects.create_user("a2"))
        self.assertFalse(would_remove_last_admin(first))
        assert_admin_remains(first)  # не бросает

    def test_non_admin_assignment_not_guarded(self):
        custom = AccessRole.objects.create(slug="hr", name="HR", type=AccessRole.Type.CUSTOM)
        assignment = self._assign(custom, self.user_model.objects.create_user("h1"))
        self.assertFalse(would_remove_last_admin(assignment))

    def test_inactive_admin_does_not_count(self):
        active = self._assign(self.admin_role, self.user_model.objects.create_user("a1"))
        inactive = self._assign(self.admin_role, self.user_model.objects.create_user("a2"))
        inactive.is_active = False
        inactive.save(update_fields=["is_active"])
        self.assertTrue(would_remove_last_admin(active))


class SeedAccessRolesTests(TestCase):
    def test_seed_idempotent_and_empty(self):
        call_command("seed_access_roles")
        count = AccessRole.objects.count()
        self.assertEqual(count, len(SYSTEM_ROLE_SEEDS))
        call_command("seed_access_roles")
        self.assertEqual(AccessRole.objects.count(), count)
        for role in AccessRole.objects.all():
            self.assertEqual(role.type, AccessRole.Type.SYSTEM)
            self.assertEqual(role.permissions.count(), 0, f"{role.slug} must seed empty")
        self.assertTrue(AccessRole.objects.filter(slug=ADMIN_ROLE_SLUG, is_membership_computed=False).exists())
