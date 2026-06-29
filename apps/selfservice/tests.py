from datetime import date

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.employees.models import Clinic, Department, Employee
from apps.knowledge.models import KnowledgeCategory, KnowledgeDocument
from apps.leave.models import LeaveRequest, LeaveType
from apps.skud.models import TimeCorrectionRequest


class SelfServiceApiTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="employee", password="pass")
        self.clinic = Clinic.objects.create(name="Клініка тест", code="test")
        self.department = Department.objects.create(name="Операційний", clinic=self.clinic)
        self.employee = Employee.objects.create(
            user=self.user,
            first_name="Ірина",
            last_name="Тестова",
            clinic=self.clinic,
            department=self.department,
        )
        self.other_employee = Employee.objects.create(first_name="Петро", last_name="Чужий")
        self.leave_type = LeaveType.objects.create(name="Щорічна відпустка", code="annual")
        self.client.force_authenticate(self.user)

    def test_profile_uses_current_employee(self):
        response = self.client.get(reverse("self-profile"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.employee.id)

    def test_preferences_are_current_user_specific(self):
        response = self.client.patch(
            reverse("self-preferences"),
            {"language": "pl", "theme": "dark", "time_zone": "Europe/Warsaw"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["language"], "pl")
        self.assertEqual(response.data["theme"], "dark")
        self.assertEqual(response.data["time_zone"], "Europe/Warsaw")

        other_user = get_user_model().objects.create_user(username="other", password="pass")
        self.client.force_authenticate(other_user)
        other_response = self.client.get(reverse("self-preferences"))

        self.assertEqual(other_response.status_code, 200)
        self.assertEqual(other_response.data["language"], "uk")
        self.assertEqual(other_response.data["theme"], "light")

    def test_time_correction_request_ignores_payload_employee(self):
        response = self.client.post(
            reverse("self-time-corrections"),
            {
                "employee": self.other_employee.id,
                "date": "2026-06-24",
                "reason": "Забув відмітити вихід",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        correction = TimeCorrectionRequest.objects.get()
        self.assertEqual(correction.employee_id, self.employee.id)
        self.assertEqual(correction.status, TimeCorrectionRequest.Status.SUBMITTED)
        self.assertIsNotNone(correction.submitted_at)

    def test_leave_request_uses_current_employee_and_submits(self):
        response = self.client.post(
            reverse("self-leave"),
            {
                "employee": self.other_employee.id,
                "leave_type": self.leave_type.id,
                "date_from": "2026-07-01",
                "date_to": "2026-07-05",
                "reason": "Планова відпустка",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        leave_request = LeaveRequest.objects.get()
        self.assertEqual(leave_request.employee_id, self.employee.id)
        self.assertEqual(leave_request.status, LeaveRequest.Status.SUBMITTED)
        self.assertIsNotNone(leave_request.submitted_at)

    def test_leave_request_rejects_reversed_dates(self):
        response = self.client.post(
            reverse("self-leave"),
            {
                "leave_type": self.leave_type.id,
                "date_from": "2026-07-05",
                "date_to": "2026-07-01",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_attendance_range_is_bounded(self):
        response = self.client.get(
            reverse("self-attendance"),
            {"from": date(2026, 1, 1).isoformat(), "to": date(2026, 6, 24).isoformat()},
        )

        self.assertEqual(response.status_code, 400)

    def test_knowledge_returns_only_visible_categories_and_published_documents(self):
        public_category = KnowledgeCategory.objects.create(name="Для всіх", slug="all")
        direct_category = KnowledgeCategory.objects.create(
            name="За списком",
            slug="direct",
            visibility_mode=KnowledgeCategory.VisibilityMode.SPECIFIC,
            audience_employee_ids=[self.employee.id],
        )
        condition_category = KnowledgeCategory.objects.create(
            name="За умовою",
            slug="condition",
            visibility_mode=KnowledgeCategory.VisibilityMode.SPECIFIC,
            audience_filters={
                "employee_status": "active",
                "conditions": [{"field": "department", "operator": "is", "value": [self.department.id]}],
            },
        )
        hidden_category = KnowledgeCategory.objects.create(
            name="Прихована",
            slug="hidden",
            visibility_mode=KnowledgeCategory.VisibilityMode.SPECIFIC,
            audience_employee_ids=[self.other_employee.id],
        )
        KnowledgeDocument.objects.create(
            category=public_category,
            title="Публічна стаття",
            slug="public-doc",
            status=KnowledgeDocument.Status.PUBLISHED,
        )
        KnowledgeDocument.objects.create(
            category=direct_category,
            title="Стаття за списком",
            slug="direct-doc",
            status=KnowledgeDocument.Status.PUBLISHED,
        )
        KnowledgeDocument.objects.create(
            category=condition_category,
            title="Стаття за умовою",
            slug="condition-doc",
            status=KnowledgeDocument.Status.PUBLISHED,
        )
        KnowledgeDocument.objects.create(
            category=hidden_category,
            title="Прихована стаття",
            slug="hidden-doc",
            status=KnowledgeDocument.Status.PUBLISHED,
        )
        KnowledgeDocument.objects.create(
            category=public_category,
            title="Чернетка",
            slug="draft-doc",
            status=KnowledgeDocument.Status.DRAFT,
        )

        response = self.client.get(reverse("self-knowledge"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {category["id"] for category in response.data["categories"]},
            {public_category.id, direct_category.id, condition_category.id},
        )
        self.assertEqual(
            {document["title"] for document in response.data["documents"]},
            {"Публічна стаття", "Стаття за списком", "Стаття за умовою"},
        )
