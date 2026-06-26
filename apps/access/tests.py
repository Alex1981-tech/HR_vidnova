from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from unittest.mock import patch

from apps.access.models import AuthAuditEvent, EmployeeTelegramLink, TelegramLoginCode
from apps.access.services import (
    PhoneMatchStatus,
    find_employee_by_phone,
    hash_login_code,
    login_code_matches,
    normalize_phone,
)
from apps.access.telegram import TelegramSendError, build_login_code_text, send_login_code
from apps.employees.models import Employee


class PhoneNormalizationTests(TestCase):
    def test_empty_phone_returns_empty_string(self):
        self.assertEqual(normalize_phone(""), "")
        self.assertEqual(normalize_phone(None), "")

    def test_ukrainian_phone_formats_normalize_to_same_value(self):
        expected = "+380971234567"

        self.assertEqual(normalize_phone("+38 (097) 123-45-67"), expected)
        self.assertEqual(normalize_phone("380971234567"), expected)
        self.assertEqual(normalize_phone("0971234567"), expected)

    def test_non_ukrainian_number_is_kept_with_plus(self):
        self.assertEqual(normalize_phone("+1 555 123 4567"), "+15551234567")
        self.assertEqual(normalize_phone("15551234567"), "+15551234567")


class EmployeePhoneMatchTests(TestCase):
    def test_active_employee_is_found_by_phone(self):
        employee = Employee.objects.create(first_name="Ірина", last_name="Тестова", phone="+38 (097) 123-45-67")

        result = find_employee_by_phone("0971234567")

        self.assertEqual(result.status, PhoneMatchStatus.MATCHED)
        self.assertEqual(result.employee, employee)
        self.assertEqual(result.phone_normalized, "+380971234567")
        self.assertEqual(result.matches_count, 1)
        self.assertTrue(result.is_matched)

    def test_active_employee_is_found_by_phone2(self):
        employee = Employee.objects.create(first_name="Олег", last_name="Другий", phone2="380501112233")

        result = find_employee_by_phone("+38 (050) 111-22-33")

        self.assertEqual(result.status, PhoneMatchStatus.MATCHED)
        self.assertEqual(result.employee, employee)
        self.assertEqual(result.phone_normalized, "+380501112233")

    def test_missing_phone_returns_not_found(self):
        Employee.objects.create(first_name="Ірина", last_name="Тестова", phone="0971234567")

        result = find_employee_by_phone("0501112233")

        self.assertEqual(result.status, PhoneMatchStatus.NOT_FOUND)
        self.assertIsNone(result.employee)
        self.assertFalse(result.is_matched)

    def test_duplicate_active_employees_return_conflict(self):
        Employee.objects.create(first_name="Ірина", last_name="Перша", phone="+38 (097) 123-45-67")
        Employee.objects.create(first_name="Олег", last_name="Другий", phone2="0971234567")

        result = find_employee_by_phone("380971234567")

        self.assertEqual(result.status, PhoneMatchStatus.CONFLICT)
        self.assertIsNone(result.employee)
        self.assertEqual(result.matches_count, 2)

    def test_non_active_employee_statuses_do_not_match(self):
        blocked_statuses = [Employee.Status.DISMISSED, Employee.Status.SUSPENDED, Employee.Status.ON_LEAVE]
        for status in blocked_statuses:
            with self.subTest(status=status):
                Employee.objects.all().delete()
                Employee.objects.create(first_name="Ірина", last_name="Тестова", phone="0971234567", status=status)

                result = find_employee_by_phone("0971234567")

                self.assertEqual(result.status, PhoneMatchStatus.NOT_FOUND)
                self.assertIsNone(result.employee)

    def test_active_employee_with_inactive_user_does_not_match(self):
        user = get_user_model().objects.create_user(username="inactive-employee", password="pass", is_active=False)
        Employee.objects.create(user=user, first_name="Ірина", last_name="Тестова", phone="0971234567")

        result = find_employee_by_phone("0971234567")

        self.assertEqual(result.status, PhoneMatchStatus.INACTIVE_USER)
        self.assertIsNone(result.employee)
        self.assertEqual(result.matches_count, 1)


class TelegramSenderTests(TestCase):
    @override_settings(TELEGRAM_BOT_TOKEN="", HR_TELEGRAM_SENDER_BACKEND="telegram_bot_api")
    def test_sender_requires_token(self):
        employee = Employee(first_name="Ірина", last_name="Тестова")

        with self.assertRaises(TelegramSendError):
            send_login_code(12345, "123456", employee)

    def test_login_code_text_identifies_hr_vidnova(self):
        employee = Employee(first_name="Ірина", last_name="Тестова")

        text = build_login_code_text("123456", employee)

        self.assertIn("HR Vidnova", text)
        self.assertIn("123456", text)
        self.assertIn("Ірина", text)

    @override_settings(TELEGRAM_BOT_TOKEN="test-token", HR_TELEGRAM_SENDER_BACKEND="telegram_bot_api")
    @patch("apps.access.telegram.urllib.request.urlopen")
    def test_sender_uses_bot_api_backend(self, urlopen_mock):
        employee = Employee(first_name="Ірина", last_name="Тестова")

        send_login_code(12345, "123456", employee)

        urlopen_mock.assert_called_once()


@override_settings(HR_BOT_API_SECRET="test-bot-secret")
class BotLinkByPhoneApiTests(APITestCase):
    def post_link(self, payload: dict, secret: str | None = "test-bot-secret"):
        headers = {}
        if secret is not None:
            headers["HTTP_X_BOT_API_SECRET"] = secret
        return self.client.post(reverse("bot-link-by-phone"), payload, format="json", **headers)

    def test_missing_bot_secret_is_rejected_and_audited(self):
        response = self.post_link({"phone": "0971234567", "telegram_chat_id": 12345}, secret=None)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(EmployeeTelegramLink.objects.exists())
        event = AuthAuditEvent.objects.get()
        self.assertEqual(event.event, AuthAuditEvent.Event.ACCESS_DENIED)
        self.assertEqual(event.result, AuthAuditEvent.Result.DENIED)
        self.assertEqual(event.phone_normalized, "+380971234567")
        self.assertEqual(event.telegram_chat_id, 12345)

    def test_wrong_bot_secret_is_rejected(self):
        response = self.post_link({"phone": "0971234567", "telegram_chat_id": 12345}, secret="wrong")

        self.assertEqual(response.status_code, 403)
        self.assertFalse(EmployeeTelegramLink.objects.exists())

    def test_valid_request_creates_telegram_link_and_audit_event(self):
        employee = Employee.objects.create(first_name="Ірина", last_name="Тестова", phone="+38 (097) 123-45-67")

        response = self.post_link(
            {
                "phone": "0971234567",
                "telegram_chat_id": 12345,
                "telegram_user_id": 54321,
                "telegram_username": "@iryna",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ok"})
        link = EmployeeTelegramLink.objects.get(employee=employee)
        self.assertEqual(link.telegram_chat_id, 12345)
        self.assertEqual(link.telegram_user_id, 54321)
        self.assertEqual(link.telegram_username, "iryna")
        self.assertEqual(link.phone_normalized, "+380971234567")
        event = AuthAuditEvent.objects.get(event=AuthAuditEvent.Event.TELEGRAM_LINKED)
        self.assertEqual(event.result, AuthAuditEvent.Result.OK)
        self.assertEqual(event.employee, employee)
        self.assertEqual(event.telegram_link, link)

    def test_repeated_request_updates_existing_link_without_duplicate(self):
        employee = Employee.objects.create(first_name="Ірина", last_name="Тестова", phone="0971234567")

        first = self.post_link({"phone": "0971234567", "chat_id": 12345, "telegram_username": "old"})
        second = self.post_link({"phone": "0971234567", "chat_id": 12345, "telegram_username": "new"})

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(EmployeeTelegramLink.objects.filter(employee=employee).count(), 1)
        self.assertEqual(EmployeeTelegramLink.objects.get(employee=employee).telegram_username, "new")
        self.assertEqual(AuthAuditEvent.objects.filter(event=AuthAuditEvent.Event.TELEGRAM_LINKED).count(), 2)

    def test_duplicate_active_phone_returns_conflict_without_linking(self):
        Employee.objects.create(first_name="Ірина", last_name="Перша", phone="0971234567")
        Employee.objects.create(first_name="Олег", last_name="Другий", phone2="+38 (097) 123-45-67")

        response = self.post_link({"phone": "380971234567", "telegram_chat_id": 12345})

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data, {"status": "conflict"})
        self.assertFalse(EmployeeTelegramLink.objects.exists())
        event = AuthAuditEvent.objects.get()
        self.assertEqual(event.result, AuthAuditEvent.Result.CONFLICT)
        self.assertEqual(event.metadata["match_status"], PhoneMatchStatus.CONFLICT)

    def test_existing_chat_id_linked_to_other_employee_returns_conflict(self):
        first = Employee.objects.create(first_name="Ірина", last_name="Перша", phone="0971234567")
        second = Employee.objects.create(first_name="Олег", last_name="Другий", phone="0501112233")
        existing = EmployeeTelegramLink.objects.create(
            employee=first,
            telegram_chat_id=12345,
            phone_normalized="+380971234567",
        )

        response = self.post_link({"phone": "0501112233", "telegram_chat_id": 12345})

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data, {"status": "conflict"})
        existing.refresh_from_db()
        self.assertEqual(existing.employee, first)
        self.assertFalse(EmployeeTelegramLink.objects.filter(employee=second).exists())
        event = AuthAuditEvent.objects.get()
        self.assertEqual(event.result, AuthAuditEvent.Result.CONFLICT)
        self.assertEqual(event.metadata["reason"], "telegram_chat_id_already_linked")


@override_settings(
    TELEGRAM_BOT_TOKEN="test-token",
    HR_LOGIN_CODE_TTL_SECONDS=300,
    HR_LOGIN_CODE_MAX_ATTEMPTS=5,
    HR_LOGIN_CODE_REQUEST_LIMIT_PER_MINUTE=5,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class AuthLoginFlowApiTests(APITestCase):
    def setUp(self):
        cache.clear()

    def create_linked_employee(self, phone: str = "0971234567"):
        employee = Employee.objects.create(first_name="Ірина", last_name="Тестова", phone=phone)
        link = EmployeeTelegramLink.objects.create(
            employee=employee,
            telegram_chat_id=12345,
            telegram_user_id=54321,
            telegram_username="iryna",
            phone_normalized=normalize_phone(phone),
        )
        return employee, link

    def request_code(self, phone: str = "0971234567", code: str = "123456"):
        sent_codes = []

        def fake_send(telegram_chat_id, sent_code, employee):
            sent_codes.append(sent_code)

        generate_patch = patch("apps.access.views.generate_login_code", return_value=code)
        send_patch = patch("apps.access.views.send_login_code", side_effect=fake_send)
        with generate_patch, send_patch as send_mock:
            response = self.client.post(reverse("auth-request-code"), {"phone": phone}, format="json")
        return response, sent_codes, send_mock

    def test_request_code_for_unknown_phone_is_neutral_without_code(self):
        with patch("apps.access.views.send_login_code") as send_mock:
            response = self.client.post(reverse("auth-request-code"), {"phone": "0971234567"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "code_sent"})
        self.assertFalse(TelegramLoginCode.objects.exists())
        send_mock.assert_not_called()
        event = AuthAuditEvent.objects.get()
        self.assertEqual(event.event, AuthAuditEvent.Event.LOGIN_CODE_REQUESTED)
        self.assertEqual(event.result, AuthAuditEvent.Result.DENIED)
        self.assertEqual(event.metadata["match_status"], PhoneMatchStatus.NOT_FOUND)

    def test_request_code_without_active_telegram_link_is_neutral_without_code(self):
        Employee.objects.create(first_name="Ірина", last_name="Тестова", phone="0971234567")

        with patch("apps.access.views.send_login_code") as send_mock:
            response = self.client.post(reverse("auth-request-code"), {"phone": "0971234567"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "code_sent"})
        self.assertFalse(TelegramLoginCode.objects.exists())
        send_mock.assert_not_called()
        event = AuthAuditEvent.objects.get()
        self.assertEqual(event.result, AuthAuditEvent.Result.DENIED)
        self.assertEqual(event.metadata["reason"], "no_active_telegram_link")

    def test_request_code_creates_hashed_code_and_sends_telegram(self):
        employee, link = self.create_linked_employee()

        response, sent_codes, send_mock = self.request_code(code="123456")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "code_sent"})
        self.assertEqual(sent_codes, ["123456"])
        send_mock.assert_called_once()
        login_code = TelegramLoginCode.objects.get(employee=employee)
        self.assertNotEqual(login_code.code_hash, "123456")
        self.assertTrue(login_code_matches("123456", login_code.code_hash))
        self.assertEqual(login_code.telegram_link, link)
        self.assertIsNone(login_code.consumed_at)
        event = AuthAuditEvent.objects.get(event=AuthAuditEvent.Event.LOGIN_CODE_SENT)
        self.assertEqual(event.result, AuthAuditEvent.Result.OK)
        self.assertEqual(event.telegram_chat_id, link.telegram_chat_id)

    def test_request_code_send_failure_consumes_code_and_stays_neutral(self):
        employee, _ = self.create_linked_employee()

        with patch("apps.access.views.generate_login_code", return_value="123456"):
            with patch("apps.access.views.send_login_code", side_effect=TelegramSendError("boom")):
                response = self.client.post(reverse("auth-request-code"), {"phone": "0971234567"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "code_sent"})
        login_code = TelegramLoginCode.objects.get(employee=employee)
        self.assertIsNotNone(login_code.consumed_at)
        event = AuthAuditEvent.objects.get(event=AuthAuditEvent.Event.LOGIN_CODE_SENT)
        self.assertEqual(event.result, AuthAuditEvent.Result.FAILED)
        self.assertEqual(event.metadata["reason"], "telegram_send_failed")

    def test_verify_code_creates_user_links_employee_and_creates_session(self):
        employee, _ = self.create_linked_employee()
        self.request_code(code="123456")

        response = self.client.post(
            reverse("auth-verify-code"),
            {"phone": "0971234567", "code": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        employee.refresh_from_db()
        self.assertIsNotNone(employee.user_id)
        self.assertEqual(employee.user.username, f"employee-{employee.id}")
        login_code = TelegramLoginCode.objects.get(employee=employee)
        self.assertIsNotNone(login_code.consumed_at)
        status_response = self.client.get(reverse("auth-status"))
        self.assertEqual(status_response.status_code, 200)
        self.assertTrue(status_response.data["authenticated"])
        self.assertEqual(status_response.data["employee"]["id"], employee.id)
        event = AuthAuditEvent.objects.filter(event=AuthAuditEvent.Event.LOGIN_SUCCEEDED).get()
        self.assertEqual(event.result, AuthAuditEvent.Result.OK)

    def test_wrong_code_increments_attempts(self):
        employee, _ = self.create_linked_employee()
        self.request_code(code="123456")

        response = self.client.post(
            reverse("auth-verify-code"),
            {"phone": "0971234567", "code": "654321"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["attempts_remaining"], 4)
        login_code = TelegramLoginCode.objects.get(employee=employee)
        self.assertEqual(login_code.failed_attempts, 1)
        self.assertIsNone(login_code.consumed_at)

    def test_consumed_code_cannot_be_reused(self):
        self.create_linked_employee()
        self.request_code(code="123456")
        first = self.client.post(reverse("auth-verify-code"), {"phone": "0971234567", "code": "123456"}, format="json")
        second = self.client.post(reverse("auth-verify-code"), {"phone": "0971234567", "code": "123456"}, format="json")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(AuthAuditEvent.objects.filter(event=AuthAuditEvent.Event.LOGIN_SUCCEEDED).count(), 1)

    def test_expired_code_is_rejected(self):
        employee, link = self.create_linked_employee()
        TelegramLoginCode.objects.create(
            employee=employee,
            telegram_link=link,
            code_hash=hash_login_code("123456"),
            expires_at=timezone.now() - timezone.timedelta(seconds=1),
        )

        response = self.client.post(
            reverse("auth-verify-code"),
            {"phone": "0971234567", "code": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["detail"], "Code expired")
        event = AuthAuditEvent.objects.get(event=AuthAuditEvent.Event.LOGIN_FAILED)
        self.assertEqual(event.metadata["reason"], "code_expired")

    def test_logout_ends_session(self):
        self.create_linked_employee()
        self.request_code(code="123456")
        self.client.post(reverse("auth-verify-code"), {"phone": "0971234567", "code": "123456"}, format="json")

        response = self.client.post(reverse("auth-logout"), {}, format="json")
        status_response = self.client.get(reverse("auth-status"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ok"})
        self.assertFalse(status_response.data["authenticated"])
        event = AuthAuditEvent.objects.filter(event=AuthAuditEvent.Event.LOGOUT).get()
        self.assertEqual(event.result, AuthAuditEvent.Result.OK)

    @override_settings(HR_LOGIN_CODE_REQUEST_LIMIT_PER_MINUTE=1)
    def test_request_code_rate_limit_is_per_phone_and_ip(self):
        self.create_linked_employee()
        first, _, _ = self.request_code(code="123456")
        second, _, _ = self.request_code(code="654321")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        event = AuthAuditEvent.objects.filter(event=AuthAuditEvent.Event.LOGIN_CODE_REQUESTED).get()
        self.assertEqual(event.result, AuthAuditEvent.Result.LOCKED)
