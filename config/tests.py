"""Тесты production safety gate (P0)."""

from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, SimpleTestCase, override_settings

from django.http import Http404

from config.media import protected_media
from config.permissions import ConfiguredReadOnlyOrAuthenticated
from config.safety import DEV_SECRET_FALLBACK, production_safety_problems
from config.sanitize import sanitize_rich_html


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


class ConfiguredReadOnlyOrAuthenticatedTests(SimpleTestCase):
    """Smoke: при выключенном public API анонимный запрос не проходит (как в production)."""

    def setUp(self):
        self.factory = RequestFactory()
        self.perm = ConfiguredReadOnlyOrAuthenticated()

    @override_settings(HR_PUBLIC_READ_API=False, HR_PUBLIC_WRITE_API=False)
    def test_anonymous_read_denied_when_public_off(self):
        request = self.factory.get("/api/employees/")
        request.user = AnonymousUser()
        self.assertFalse(self.perm.has_permission(request, view=None))

    @override_settings(HR_PUBLIC_READ_API=False, HR_PUBLIC_WRITE_API=False)
    def test_anonymous_write_denied_when_public_off(self):
        request = self.factory.post("/api/employees/")
        request.user = AnonymousUser()
        self.assertFalse(self.perm.has_permission(request, view=None))

    @override_settings(HR_PUBLIC_READ_API=False, HR_PUBLIC_WRITE_API=False)
    def test_authenticated_read_allowed(self):
        request = self.factory.get("/api/employees/")
        request.user = User(username="u", is_active=True)
        self.assertTrue(self.perm.has_permission(request, view=None))

    @override_settings(HR_PUBLIC_READ_API=True, HR_PUBLIC_WRITE_API=False)
    def test_anonymous_read_allowed_in_dev(self):
        request = self.factory.get("/api/employees/")
        request.user = AnonymousUser()
        self.assertTrue(self.perm.has_permission(request, view=None))


class ProtectedMediaTests(SimpleTestCase):
    """P2: media недоступна анонимно; авторизованный запрос идёт через X-Accel."""

    def setUp(self):
        self.factory = RequestFactory()

    @override_settings(HR_PUBLIC_READ_API=False, HR_MEDIA_X_ACCEL=True)
    def test_anonymous_denied_when_public_off(self):
        request = self.factory.get("/media/employee_avatars/2026/06/x.webp")
        request.user = AnonymousUser()
        response = protected_media(request, "employee_avatars/2026/06/x.webp")
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("X-Accel-Redirect", response)

    @override_settings(HR_PUBLIC_READ_API=False, HR_MEDIA_X_ACCEL=True)
    def test_authenticated_served_via_x_accel(self):
        request = self.factory.get("/media/certificates/2026/06/a.webp")
        request.user = User(username="u", is_active=True)
        response = protected_media(request, "certificates/2026/06/a.webp")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Accel-Redirect"], "/protected-media/certificates/2026/06/a.webp")
        self.assertEqual(response["Content-Type"], "image/webp")

    @override_settings(HR_PUBLIC_READ_API=True, HR_MEDIA_X_ACCEL=True)
    def test_anonymous_allowed_in_dev_public_read(self):
        request = self.factory.get("/media/knowledge/file.pdf")
        request.user = AnonymousUser()
        response = protected_media(request, "knowledge/file.pdf")
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Accel-Redirect", response)

    @override_settings(HR_PUBLIC_READ_API=True, HR_MEDIA_X_ACCEL=True)
    def test_path_traversal_blocked(self):
        request = self.factory.get("/media/x")
        request.user = User(username="u", is_active=True)
        with self.assertRaises(Http404):
            protected_media(request, "../../etc/passwd")


class SanitizeRichHtmlTests(SimpleTestCase):
    """P4: центральный HTML-санитайзер режет XSS, сохраняет легитимный rich-text."""

    def test_empty(self):
        self.assertEqual(sanitize_rich_html(""), "")
        self.assertEqual(sanitize_rich_html(None), "")

    def test_script_removed(self):
        out = sanitize_rich_html("<p>hi</p><script>alert(1)</script>")
        self.assertNotIn("<script", out)
        self.assertIn("<p>hi</p>", out)

    def test_event_handler_removed(self):
        out = sanitize_rich_html('<img src="/media/a.webp" onerror="alert(1)">')
        self.assertNotIn("onerror", out)
        self.assertIn('src="/media/a.webp"', out)

    def test_javascript_href_removed(self):
        out = sanitize_rich_html('<a href="javascript:alert(1)">x</a>')
        self.assertNotIn("javascript:", out)

    def test_safe_href_kept(self):
        out = sanitize_rich_html('<a href="https://example.com">x</a>')
        self.assertIn('href="https://example.com"', out)
        self.assertIn("noopener", out)

    def test_style_attr_removed(self):
        self.assertNotIn("style", sanitize_rich_html('<p style="position:fixed">x</p>'))

    def test_svg_removed(self):
        self.assertEqual(sanitize_rich_html("<svg onload=alert(1)></svg>").strip(), "")

    def test_youtube_iframe_kept(self):
        out = sanitize_rich_html('<iframe src="https://www.youtube.com/embed/abc"></iframe>')
        self.assertIn("https://www.youtube.com/embed/abc", out)

    def test_non_youtube_iframe_src_dropped(self):
        out = sanitize_rich_html('<iframe src="https://evil.com/x"></iframe>')
        self.assertNotIn("evil.com", out)

    def test_gallery_structure_kept(self):
        html = (
            '<div class="announcement-gallery" data-ann-gallery="1">'
            '<button type="button" data-ann-gallery-prev="true" aria-label="Prev">x</button>'
            "</div>"
        )
        out = sanitize_rich_html(html)
        self.assertIn('class="announcement-gallery"', out)
        self.assertIn('data-ann-gallery-prev="true"', out)
        self.assertIn("<button", out)

    def test_video_with_media_src_kept(self):
        out = sanitize_rich_html('<video src="/media/v.mp4" controls preload="none"></video>')
        self.assertIn('src="/media/v.mp4"', out)
        self.assertIn("controls", out)
