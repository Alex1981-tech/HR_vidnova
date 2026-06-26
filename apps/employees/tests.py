from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.employees.models import (
    Clinic,
    Employee,
    EmployeeEmploymentStatus,
    EmployeeFormTemplate,
    EmploymentType,
    ManagerAssignment,
    WorkingPattern,
)


class EmployeeHireApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr", password="test")
        self.client.force_authenticate(self.user)

    def test_hire_creates_employee_manager_assignment_and_work_status(self):
        manager = Employee.objects.create(first_name="Олена", last_name="Керівник")
        clinic = Clinic.objects.create(name="VIDNOVA Запоріжжя", code="vidnova-zp")
        employment_type = EmploymentType.objects.create(name="Повна зайнятість")
        working_pattern = WorkingPattern.objects.create(
            name="Повна зайнятість Vidnova Clinic Запоріжжя",
            monday_hours=8,
            tuesday_hours=8,
            wednesday_hours=8,
            thursday_hours=8,
            friday_hours=8,
            is_active=True,
        )

        response = self.client.post(
            "/api/employees/employees/hire/",
            {
                "first_name": "Ірина",
                "last_name": "Новенька",
                "personal_email": "iryna@example.com",
                "phone": "+380971111111",
                "clinic": clinic.id,
                "employment_type": employment_type.id,
                "working_pattern": working_pattern.id,
                "manager": manager.id,
                "hired_on": "2026-07-01",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        employee = Employee.objects.get(personal_email="iryna@example.com")
        self.assertEqual(employee.status, Employee.Status.ACTIVE)
        self.assertEqual(employee.clinic, clinic)
        self.assertTrue(
            ManagerAssignment.objects.filter(
                employee=employee,
                manager=manager,
                valid_from=date(2026, 7, 1),
                is_primary=True,
            ).exists()
        )
        status = EmployeeEmploymentStatus.objects.get(employee=employee)
        self.assertEqual(status.employment_type, employment_type)
        self.assertEqual(status.working_pattern_name, working_pattern.name)


class EmployeeFormTemplateApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr-forms", password="test")
        self.client.force_authenticate(self.user)

    def test_create_form_template_and_summary(self):
        response = self.client.post(
            "/api/employees/form-templates/",
            {
                "form_type": EmployeeFormTemplate.FormType.NEW_HIRE,
                "name": "Тестова форма найму",
                "description": "Форма для перевірки створення.",
                "allow_employee_access": True,
                "workflow_name": "Пребординг Запоріжжя",
                "allow_requester_disable_workflow": False,
                "sections": [
                    {
                        "id": "work_details",
                        "name": "Деталі роботи",
                        "fields": [{"id": "position", "name": "Посада", "required": True}],
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["section_count"], 1)
        self.assertTrue(EmployeeFormTemplate.objects.filter(name="Тестова форма найму").exists())

        summary = self.client.get("/api/employees/form-templates/summary/")
        self.assertEqual(summary.status_code, 200)
        counts = {row["form_type"]: row["count"] for row in summary.data}
        self.assertGreaterEqual(counts.get(EmployeeFormTemplate.FormType.NEW_HIRE, 0), 1)

    def test_soft_delete_form_template(self):
        template = EmployeeFormTemplate.objects.create(
            form_type=EmployeeFormTemplate.FormType.CUSTOM_REQUEST,
            name="Архівний кастомний запит",
        )

        response = self.client.delete(f"/api/employees/form-templates/{template.id}/")

        self.assertEqual(response.status_code, 204)
        template.refresh_from_db()
        self.assertFalse(template.is_active)
