"""Тесты permission registry (RBAC, Этап 1)."""

from django.test import SimpleTestCase

from apps.access.permissions_registry import (
    CODE_RE,
    PERMISSIONS,
    PERMISSIONS_BY_CODE,
    REQUIRED_MODULES,
    AccessLevel,
    RiskLevel,
    all_codes,
    field_permission_code,
    get_permission,
    parse_field_permission_code,
    permissions_for_module,
)


class PermissionRegistryTests(SimpleTestCase):
    def test_codes_unique(self):
        codes = all_codes()
        self.assertEqual(len(codes), len(set(codes)), "permission codes must be unique")
        self.assertEqual(len(PERMISSIONS_BY_CODE), len(PERMISSIONS))

    def test_metadata_complete(self):
        for perm in PERMISSIONS:
            self.assertTrue(perm.code, "code required")
            self.assertTrue(perm.module, f"module required for {perm.code}")
            self.assertTrue(perm.group, f"group required for {perm.code}")
            self.assertTrue(perm.action, f"action required for {perm.code}")
            self.assertTrue(perm.label.strip(), f"label required for {perm.code}")
            self.assertTrue(perm.description.strip(), f"description required for {perm.code}")
            self.assertIsInstance(perm.risk, RiskLevel, f"risk required for {perm.code}")

    def test_section_present(self):
        for perm in PERMISSIONS:
            self.assertTrue(perm.section.strip(), f"section required for {perm.code}")

    def test_company_catalog_shape(self):
        from apps.access.permissions_registry import company_catalog

        cats = company_catalog()
        self.assertTrue(cats)
        for cat in cats:
            self.assertIn("key", cat)
            self.assertIn("sections", cat)
            self.assertNotEqual(cat["key"], "self")  # self-группа не на вкладке «Компанія»
            for sec in cat["sections"]:
                self.assertTrue(sec["permissions"])
                for p in sec["permissions"]:
                    self.assertIn(p["kind"], {"bool", "graded"})

    def test_code_format(self):
        for perm in PERMISSIONS:
            self.assertRegex(perm.code, CODE_RE, f"bad code format: {perm.code}")

    def test_code_starts_with_module(self):
        for perm in PERMISSIONS:
            self.assertTrue(
                perm.code == perm.module or perm.code.startswith(perm.module + "."),
                f"code {perm.code} must be under module {perm.module}",
            )

    def test_levels_valid(self):
        for perm in PERMISSIONS:
            for level in perm.levels:
                self.assertIsInstance(level, AccessLevel)
            if perm.levels:
                # graded -> всегда содержит VIEW; EDIT только вместе с VIEW.
                self.assertIn(AccessLevel.VIEW, perm.levels, f"{perm.code}: graded must allow view")
                if AccessLevel.EDIT in perm.levels:
                    self.assertEqual(perm.levels, (AccessLevel.VIEW, AccessLevel.EDIT), perm.code)

    def test_required_namespaces_present(self):
        modules = {p.module for p in PERMISSIONS}
        missing = REQUIRED_MODULES - modules
        self.assertFalse(missing, f"missing required namespaces: {missing}")

    def test_field_namespace_present(self):
        # people.field.* должен присутствовать (системные поля профиля).
        self.assertTrue(any(p.code.startswith("people.field.") for p in PERMISSIONS))

    def test_lookup_helpers(self):
        self.assertIsNone(get_permission("does.not.exist"))
        self.assertEqual(get_permission("roles.manage").module, "roles")
        self.assertTrue(permissions_for_module("leave"))
        self.assertEqual(permissions_for_module("nope"), [])

    def test_field_permission_code_roundtrip(self):
        code = field_permission_code("personal", "birth_date")
        self.assertEqual(code, "people.field.personal.birth_date")
        self.assertEqual(parse_field_permission_code(code), ("personal", "birth_date"))

    def test_field_permission_code_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            field_permission_code("personal", "bad slug!")
        with self.assertRaises(ValueError):
            field_permission_code("", "x")

    def test_parse_field_permission_code_rejects_non_field(self):
        self.assertIsNone(parse_field_permission_code("roles.manage"))
        self.assertIsNone(parse_field_permission_code("people.field.personal"))  # area, not a field
        self.assertIsNone(parse_field_permission_code("people.field.a.b.c"))
