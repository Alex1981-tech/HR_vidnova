"""Тесты production safety gate (P0)."""

from django.test import SimpleTestCase

from config.safety import DEV_SECRET_FALLBACK, production_safety_problems


class ProductionSafetyGateTests(SimpleTestCase):
    def test_non_production_is_never_blocked(self):
        # В dev любые «небезопасные» значения допустимы — гейт не срабатывает.
        problems = production_safety_problems(
            environment="development",
            debug=True,
            secret_key=DEV_SECRET_FALLBACK,
            public_read=True,
            public_write=True,
        )
        self.assertEqual(problems, [])

    def test_safe_production_passes(self):
        problems = production_safety_problems(
            environment="production",
            debug=False,
            secret_key="a-real-strong-secret",
            public_read=False,
            public_write=False,
        )
        self.assertEqual(problems, [])

    def test_production_debug_blocked(self):
        problems = production_safety_problems(
            environment="production",
            debug=True,
            secret_key="a-real-strong-secret",
            public_read=False,
            public_write=False,
        )
        self.assertTrue(any("DEBUG" in p for p in problems))

    def test_production_fallback_secret_blocked(self):
        problems = production_safety_problems(
            environment="production",
            debug=False,
            secret_key=DEV_SECRET_FALLBACK,
            public_read=False,
            public_write=False,
        )
        self.assertTrue(any("SECRET_KEY" in p for p in problems))

    def test_production_public_api_blocked(self):
        problems = production_safety_problems(
            environment="production",
            debug=False,
            secret_key="a-real-strong-secret",
            public_read=True,
            public_write=True,
        )
        self.assertTrue(any("HR_PUBLIC_READ_API" in p for p in problems))
        self.assertTrue(any("HR_PUBLIC_WRITE_API" in p for p in problems))

    def test_environment_case_insensitive(self):
        problems = production_safety_problems(
            environment="  PRODUCTION ",
            debug=True,
            secret_key="x",
            public_read=False,
            public_write=False,
        )
        self.assertTrue(problems)
