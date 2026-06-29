import tempfile
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.employees.models import Clinic, Department, Employee, Gender, ManagerAssignment
from apps.announcements.audience import resolve_audience
from apps.announcements.models import Announcement, AnnouncementPollVote
from apps.announcements.tasks import announcement_to_telegram, html_to_telegram


class AudienceResolverTests(APITestCase):
    def setUp(self):
        self.clinic = Clinic.objects.create(name="Клініка Львів")
        self.dep = Department.objects.create(name="Стоматологія", clinic=self.clinic)
        self.active_in = Employee.objects.create(first_name="А", last_name="Один", clinic=self.clinic, department=self.dep)
        self.active_out = Employee.objects.create(first_name="Б", last_name="Два", email="two@example.com")
        self.manager = Employee.objects.create(first_name="Г", last_name="Керівник")
        self.dismissed = Employee.objects.create(
            first_name="В", last_name="Три", clinic=self.clinic, status=Employee.Status.DISMISSED
        )
        ManagerAssignment.objects.create(employee=self.active_in, manager=self.manager, valid_from=date(2026, 1, 1))

    def test_all_returns_only_active(self):
        ids = set(resolve_audience("all", []).values_list("id", flat=True))
        self.assertIn(self.active_in.id, ids)
        self.assertIn(self.active_out.id, ids)
        self.assertNotIn(self.dismissed.id, ids)  # звільнені виключені базовою умовою

    def test_condition_is(self):
        qs = resolve_audience("conditions", [{"field": "clinic", "operator": "is", "value": [self.clinic.id]}])
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.active_in.id})

    def test_condition_is_not(self):
        qs = resolve_audience("conditions", [{"field": "clinic", "operator": "is_not", "value": [self.clinic.id]}])
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.active_out.id, self.manager.id})

    def test_condition_is_empty(self):
        qs = resolve_audience("conditions", [{"field": "department", "operator": "is_empty", "value": []}])
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.active_out.id, self.manager.id})

    def test_condition_employee_is(self):
        qs = resolve_audience("conditions", [{"field": "employee", "operator": "is", "value": [self.active_in.id]}])
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.active_in.id})

    def test_condition_employee_is_not_keeps_active_only(self):
        qs = resolve_audience(
            "conditions",
            [{"field": "employee", "operator": "is_not", "value": [self.active_in.id]}],
        )
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.active_out.id, self.manager.id})

    def test_condition_manager_is(self):
        qs = resolve_audience("conditions", [{"field": "manager", "operator": "is", "value": [self.manager.id]}])
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.active_in.id})

    def test_condition_gender_is(self):
        gender = Gender.objects.create(code="female", name="Жінка")
        self.active_in.gender = "female"
        self.active_in.save(update_fields=["gender"])
        qs = resolve_audience("conditions", [{"field": "gender", "operator": "is", "value": [gender.id]}])
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.active_in.id})

    def test_condition_presence_field_not_empty(self):
        qs = resolve_audience("conditions", [{"field": "email", "operator": "is_not_empty", "value": []}])
        ids = set(qs.values_list("id", flat=True))
        self.assertEqual(ids, {self.active_out.id})


class AnnouncementApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr", password="t")
        self.client.force_authenticate(self.user)
        Employee.objects.create(first_name="А", last_name="Активний")

    @patch("apps.announcements.views.send_announcement_telegram.delay")
    def test_create_publishes_and_dispatches(self, mock_delay):
        resp = self.client.post(
            "/api/announcements/announcements/",
            {"title": "Привіт", "body_html": "<p>Текст</p>", "audience_type": "all", "notify_telegram": True},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["status"], "published")
        self.assertEqual(resp.data["recipients_count"], 1)
        self.assertEqual(resp.data["author"], self.user.id)
        mock_delay.assert_called_once()

    @patch("apps.announcements.views.send_announcement_telegram.delay")
    def test_no_dispatch_when_telegram_off(self, mock_delay):
        resp = self.client.post(
            "/api/announcements/announcements/",
            {"title": "Без TG", "audience_type": "all", "notify_telegram": False},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        mock_delay.assert_not_called()

    def test_title_required(self):
        resp = self.client.post(
            "/api/announcements/announcements/", {"title": "   ", "audience_type": "all"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_audience_preview(self):
        resp = self.client.post(
            "/api/announcements/announcements/audience-preview/",
            {"audience_type": "all", "conditions": []}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["count"], 1)
        self.assertIn("sample", resp.data)

    @patch("apps.announcements.views.send_announcement_telegram.delay")
    def test_list_returns_published(self, _mock):
        self.client.post(
            "/api/announcements/announcements/",
            {"title": "Опубліковане", "audience_type": "all"}, format="json",
        )
        resp = self.client.get("/api/announcements/announcements/")
        self.assertEqual(resp.status_code, 200)
        items = resp.data["results"] if isinstance(resp.data, dict) else resp.data
        self.assertGreaterEqual(len(items), 1)

    @patch("apps.announcements.views.send_announcement_telegram.delay")
    def test_create_quick_poll(self, mock_delay):
        resp = self.client.post(
            "/api/announcements/announcements/",
            {
                "kind": "poll",
                "title": "Обрати колір",
                "poll_options": ["Синій", "Зелений", "  "],
                "audience_type": "all",
                "notify_telegram": False,
                "notify_email": True,
                "notify_web": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["kind"], "poll")
        self.assertEqual(resp.data["poll_options"], ["Синій", "Зелений"])
        self.assertEqual(resp.data["poll_results"][0]["votes"], 0)
        self.assertIsNone(resp.data["user_vote"])
        self.assertTrue(resp.data["notify_email"])
        mock_delay.assert_not_called()

    @patch("apps.announcements.views.send_announcement_telegram.delay")
    def test_create_quick_poll_dispatches_telegram_when_enabled(self, mock_delay):
        resp = self.client.post(
            "/api/announcements/announcements/",
            {
                "kind": "poll",
                "title": "Обрати день",
                "poll_options": ["Понеділок", "Вівторок"],
                "audience_type": "all",
                "notify_telegram": True,
                "notify_web": True,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        mock_delay.assert_called_once_with(resp.data["id"])

    def test_poll_requires_two_options(self):
        resp = self.client.post(
            "/api/announcements/announcements/",
            {"kind": "poll", "title": "Один", "poll_options": ["Так"], "audience_type": "all"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_update_poll_options_resets_votes(self):
        poll = Announcement.objects.create(
            title="Кава?",
            kind=Announcement.Kind.POLL,
            poll_options=["Так", "Ні"],
            audience_type="all",
        )
        AnnouncementPollVote.objects.create(announcement=poll, user=self.user, option_index=0)

        resp = self.client.patch(
            f"/api/announcements/announcements/{poll.id}/",
            {"poll_options": ["Чай", "Кава"]},
            format="json",
        )

        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["poll_options"], ["Чай", "Кава"])
        self.assertEqual(resp.data["poll_results"][0]["total_votes"], 0)
        self.assertFalse(AnnouncementPollVote.objects.filter(announcement=poll).exists())


class AnnouncementMediaUploadApiTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp_media = tempfile.TemporaryDirectory()
        cls._override = override_settings(MEDIA_ROOT=cls._tmp_media.name)
        cls._override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._override.disable()
        cls._tmp_media.cleanup()

    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr-media", password="t")
        self.client.force_authenticate(self.user)

    def test_upload_image_media(self):
        upload = SimpleUploadedFile("photo.jpg", b"fake image", content_type="image/jpeg")

        response = self.client.post(
            "/api/announcements/announcements/media-upload/",
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["kind"], "image")
        self.assertEqual(response.data["content_type"], "image/jpeg")
        self.assertTrue(response.data["url"].startswith("/media/announcements/media/"))

    def test_rejects_non_media_upload(self):
        upload = SimpleUploadedFile("note.txt", b"plain text", content_type="text/plain")

        response = self.client.post(
            "/api/announcements/announcements/media-upload/",
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, 415, response.data)


class ReactionCommentApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr", password="t")
        self.client.force_authenticate(self.user)
        self.ann = Announcement.objects.create(title="Пост", audience_type="all", allow_comments=True)

    def test_toggle_reaction(self):
        url = f"/api/announcements/announcements/{self.ann.id}/react/"
        r1 = self.client.post(url, {"emoji": "👍"}, format="json")
        self.assertEqual(r1.status_code, 200, r1.data)
        self.assertEqual(r1.data["reactions"][0]["count"], 1)
        self.assertTrue(r1.data["reactions"][0]["reacted"])
        # Повторний клік прибирає реакцію
        r2 = self.client.post(url, {"emoji": "👍"}, format="json")
        self.assertEqual(r2.data["reactions"], [])

    def test_add_comment(self):
        url = f"/api/announcements/announcements/{self.ann.id}/comments/"
        resp = self.client.post(url, {"body": "Чудово!"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["body"], "Чудово!")
        listing = self.client.get(url)
        self.assertEqual(len(listing.data), 1)

    def test_comment_blocked_when_disabled(self):
        ann = Announcement.objects.create(title="Без коментів", audience_type="all", allow_comments=False)
        resp = self.client.post(f"/api/announcements/announcements/{ann.id}/comments/", {"body": "хм"}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_vote_quick_poll(self):
        poll = Announcement.objects.create(
            title="Кава?",
            kind=Announcement.Kind.POLL,
            poll_options=["Так", "Ні"],
            audience_type="all",
        )

        first = self.client.post(
            f"/api/announcements/announcements/{poll.id}/vote/",
            {"option_index": 0},
            format="json",
        )
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data["user_vote"], 0)
        self.assertEqual(first.data["poll_results"][0]["votes"], 1)
        self.assertEqual(first.data["poll_results"][0]["percentage"], 100)

        second = self.client.post(
            f"/api/announcements/announcements/{poll.id}/vote/",
            {"option_index": 1},
            format="json",
        )
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(second.data["user_vote"], 1)
        self.assertEqual(second.data["poll_results"][0]["votes"], 0)
        self.assertEqual(second.data["poll_results"][1]["votes"], 1)

    def test_vote_rejects_invalid_option(self):
        poll = Announcement.objects.create(
            title="Кава?",
            kind=Announcement.Kind.POLL,
            poll_options=["Так", "Ні"],
            audience_type="all",
        )
        resp = self.client.post(
            f"/api/announcements/announcements/{poll.id}/vote/",
            {"option_index": 9},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)


class HtmlToTelegramTests(APITestCase):
    def test_converts_basic_html(self):
        out = html_to_telegram("<p>Привіт <strong>світ</strong></p><ul><li>один</li><li>два</li></ul>", "Тема")
        self.assertIn("<b>📢 Тема</b>", out)
        self.assertIn("<b>світ</b>", out)
        self.assertIn("• один", out)
        self.assertNotIn("<ul>", out)
        self.assertNotIn("<p>", out)

    def test_strips_disallowed_tags_keeps_links(self):
        out = html_to_telegram('<div>x</div><a href="https://t.me/x">лінк</a>', "T")
        self.assertIn('<a href="https://t.me/x">лінк</a>', out)
        self.assertNotIn("<div>", out)

    def test_poll_telegram_message_points_to_hr(self):
        poll = Announcement(
            title="Обрати день",
            kind=Announcement.Kind.POLL,
            poll_options=["Понеділок", "Вівторок"],
        )
        out = announcement_to_telegram(poll)
        self.assertIn("Нове опитування: Обрати день", out)
        self.assertIn("Голосування доступне в HR Vidnova.", out)
        self.assertIn("• Понеділок", out)
