"""Negative authorization tests для PII-доступа (P1, шаг 1: тесты до реализации).

Бизнес-правило (целевое): обычный аутентифицированный сотрудник НЕ должен
читать чужие PII (профиль, документы, заметки, экстренные контакты, иждивенцы,
отсутствия, посещаемость). Сейчас RBAC/object-scoping НЕ реализован — все
эндпоинты используют только `ConfiguredReadOnlyOrAuthenticated`, поэтому любой
залогиненный видит чужие данные.

Поэтому тесты помечены @expectedFailure:
- СЕЙЧАС они «падают» (доступ ошибочно разрешён) → unittest засчитывает это как
  expected failure, CI остаётся зелёным.
- КОГДА появится scoped queryset / object-level permission и доступ закроется,
  тест начнёт проходить → Django репортит "unexpected success" как провал suite.
  Это forcing-function: снять @expectedFailure в момент реализации RBAC.

Целевой код ответа на detail: 403 или 404 (скрывать существование чужого объекта
допустимо). Для list: чужая запись не должна присутствовать в результатах.

ВНИМАНИЕ при реализации P1: role matrix (кто из HR/manager всё-таки видит чужие
данные) — продуктовое решение Alex. Эти тесты описывают сценарий «обычный
сотрудник vs чужие данные», который запрещён при любой матрице.
"""

from __future__ import annotations

from datetime import date
from unittest import expectedFailure

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.employees.models import (
    Dependent,
    EmergencyContact,
    Employee,
    EmployeeDocument,
    EmployeeNote,
)
from apps.leave.models import LeaveRequest, LeaveType

FORBIDDEN_OR_NOT_FOUND = (403, 404)


def _result_ids(response):
    data = response.data
    rows = data["results"] if isinstance(data, dict) and "results" in data else data
    return {row["id"] for row in rows}


class EmployeePiiAuthzTests(APITestCase):
    """Обычный сотрудник не должен иметь доступ к PII другого сотрудника."""

    def setUp(self):
        user_model = get_user_model()
        # Обычный сотрудник (без HR-роли), привязан к Employee через employee_profile.
        self.user = user_model.objects.create_user(username="employee", password="pass")
        self.me = Employee.objects.create(first_name="Self", last_name="User", user=self.user)
        # Чужой сотрудник, чьи PII должны быть недоступны.
        self.other = Employee.objects.create(first_name="Other", last_name="Person")

        self.other_note = EmployeeNote.objects.create(
            employee=self.other, body_html="<p>конфіденційно</p>"
        )
        self.other_contact = EmergencyContact.objects.create(
            employee=self.other, name="ICE Other"
        )
        self.other_dependent = Dependent.objects.create(employee=self.other, name="Child Other")
        self.other_document = EmployeeDocument.objects.create(
            employee=self.other, name="Паспорт Other"
        )
        leave_type = LeaveType.objects.create(name="Відпустка", code="VAC", unit="days")
        self.other_leave = LeaveRequest.objects.create(
            employee=self.other,
            leave_type=leave_type,
            date_from=date(2026, 6, 1),
            date_to=date(2026, 6, 5),
        )

        self.client.force_authenticate(self.user)

    # ── detail: получить чужой объект по pk ──────────────────────────────────
    @expectedFailure
    def test_cannot_retrieve_other_employee_profile(self):
        resp = self.client.get(reverse("employee-detail", kwargs={"pk": self.other.id}))
        self.assertIn(resp.status_code, FORBIDDEN_OR_NOT_FOUND)

    @expectedFailure
    def test_cannot_retrieve_other_note(self):
        resp = self.client.get(reverse("employee-note-detail", kwargs={"pk": self.other_note.id}))
        self.assertIn(resp.status_code, FORBIDDEN_OR_NOT_FOUND)

    @expectedFailure
    def test_cannot_retrieve_other_emergency_contact(self):
        resp = self.client.get(
            reverse("emergency-contact-detail", kwargs={"pk": self.other_contact.id})
        )
        self.assertIn(resp.status_code, FORBIDDEN_OR_NOT_FOUND)

    @expectedFailure
    def test_cannot_retrieve_other_dependent(self):
        resp = self.client.get(reverse("dependent-detail", kwargs={"pk": self.other_dependent.id}))
        self.assertIn(resp.status_code, FORBIDDEN_OR_NOT_FOUND)

    @expectedFailure
    def test_cannot_retrieve_other_document(self):
        resp = self.client.get(
            reverse("employee-document-detail", kwargs={"pk": self.other_document.id})
        )
        self.assertIn(resp.status_code, FORBIDDEN_OR_NOT_FOUND)

    # (download проверяется через retrieve+list document authz; отдельный
    # download-тест без файлового фикстура давал 404 «файл відсутній», т.е.
    # проходил по неверной причине — поэтому исключён.)

    @expectedFailure
    def test_cannot_retrieve_other_leave_request(self):
        resp = self.client.get(reverse("leave-request-detail", kwargs={"pk": self.other_leave.id}))
        self.assertIn(resp.status_code, FORBIDDEN_OR_NOT_FOUND)

    @expectedFailure
    def test_cannot_view_other_attendance(self):
        resp = self.client.get(
            reverse("employee-attendance-detail", kwargs={"employee_id": self.other.id})
        )
        self.assertIn(resp.status_code, FORBIDDEN_OR_NOT_FOUND)

    # ── list: чужая запись не должна попадать в выдачу ───────────────────────
    @expectedFailure
    def test_list_notes_excludes_other(self):
        resp = self.client.get(reverse("employee-note-list"))
        self.assertNotIn(self.other_note.id, _result_ids(resp))

    @expectedFailure
    def test_list_emergency_contacts_excludes_other(self):
        resp = self.client.get(reverse("emergency-contact-list"))
        self.assertNotIn(self.other_contact.id, _result_ids(resp))

    @expectedFailure
    def test_list_dependents_excludes_other(self):
        resp = self.client.get(reverse("dependent-list"))
        self.assertNotIn(self.other_dependent.id, _result_ids(resp))

    @expectedFailure
    def test_list_documents_excludes_other(self):
        resp = self.client.get(reverse("employee-document-list"))
        self.assertNotIn(self.other_document.id, _result_ids(resp))

    @expectedFailure
    def test_list_leave_requests_excludes_other(self):
        resp = self.client.get(reverse("leave-request-list"))
        self.assertNotIn(self.other_leave.id, _result_ids(resp))
