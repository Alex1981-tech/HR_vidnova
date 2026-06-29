from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.employees.models import (
    Clinic,
    Department,
    Division,
    Employee,
    EmployeeEmploymentStatus,
    EmployeeField,
    EmployeeFieldGroup,
    EmployeeFieldTable,
    EmployeePositionHistory,
    EmployeeFormTemplate,
    EmploymentType,
    JobLevel,
    ManagerAssignment,
    Position,
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


class EmployeeFieldValidationApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr", password="test")
        self.client.force_authenticate(self.user)
        self.group = EmployeeFieldGroup.objects.create(tab="personal", name="Тест-група")

    def _create_table(self, columns):
        return self.client.post(
            "/api/employees/field-tables/",
            {"group": self.group.id, "name": "Таблиця", "columns": columns},
            format="json",
        )

    def test_valid_columns_accepted(self):
        resp = self._create_table([
            {"key": "die_z", "label": "Діє з", "type": "date"},
            {"key": "riven", "label": "Рівень", "type": "select", "options": ["A", "B"]},
            {"key": "flag", "label": "Прапор", "type": "boolean"},
        ])
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_duplicate_key_rejected(self):
        resp = self._create_table([
            {"key": "x", "label": "Перший", "type": "text"},
            {"key": "x", "label": "Другий", "type": "text"},
        ])
        self.assertEqual(resp.status_code, 400)
        self.assertIn("columns", resp.data)

    def test_select_without_options_rejected(self):
        resp = self._create_table([{"key": "s", "label": "Список", "type": "select"}])
        self.assertEqual(resp.status_code, 400)

    def test_unknown_type_rejected(self):
        resp = self._create_table([{"key": "s", "label": "Файл", "type": "file"}])
        self.assertEqual(resp.status_code, 400)

    def test_missing_label_rejected(self):
        resp = self._create_table([{"key": "s", "type": "text"}])
        self.assertEqual(resp.status_code, 400)

    def test_boolean_field_type_select_requires_options(self):
        resp = self.client.post(
            "/api/employees/fields/",
            {"group": self.group.id, "name": "Поле", "field_type": "select", "options": []},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_boolean_field_type_accepted(self):
        resp = self.client.post(
            "/api/employees/fields/",
            {"group": self.group.id, "name": "Активний", "field_type": "boolean"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(EmployeeField.objects.get(id=resp.data["id"]).field_type, "boolean")


class EmployeeTableRowApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr", password="test")
        self.client.force_authenticate(self.user)
        self.employee = Employee.objects.create(first_name="Іван", last_name="Тест")
        group = EmployeeFieldGroup.objects.create(tab="work", name="Робота")
        self.table = EmployeeFieldTable.objects.create(
            group=group,
            name="Посади",
            columns=[
                {"key": "posada", "label": "Посада", "type": "text"},
                {"key": "die_z", "label": "Діє з", "type": "date"},
            ],
        )
        self.base = f"/api/employees/employees/{self.employee.id}/table-rows/"

    def test_create_then_list_row(self):
        resp = self.client.post(
            f"{self.base}?table={self.table.id}",
            {"values": {"posada": "Лікар", "die_z": "2026-01-01", "ignored": "x"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertIn("row_id", resp.data)
        self.assertEqual(resp.data["posada"], "Лікар")
        self.assertNotIn("ignored", resp.data)  # невідома колонка відкинута

        listing = self.client.get(f"{self.base}?table={self.table.id}")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data), 1)

    def test_patch_row(self):
        created = self.client.post(
            f"{self.base}?table={self.table.id}",
            {"values": {"posada": "Лікар"}}, format="json",
        ).data
        row_id = created["row_id"]
        resp = self.client.patch(
            f"{self.base}{row_id}/?table={self.table.id}",
            {"values": {"posada": "Завідувач"}}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["posada"], "Завідувач")
        self.assertEqual(resp.data["row_id"], row_id)
        self.assertGreaterEqual(resp.data["updated_at"], created["updated_at"])

    def test_delete_row(self):
        row_id = self.client.post(
            f"{self.base}?table={self.table.id}",
            {"values": {"posada": "Лікар"}}, format="json",
        ).data["row_id"]
        resp = self.client.delete(f"{self.base}{row_id}/?table={self.table.id}")
        self.assertEqual(resp.status_code, 204)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.custom_fields.get(f"table_{self.table.id}"), [])

    def test_patch_unknown_row_404(self):
        resp = self.client.patch(
            f"{self.base}deadbeef/?table={self.table.id}",
            {"values": {"posada": "X"}}, format="json",
        )
        self.assertEqual(resp.status_code, 404)

    def test_missing_table_param_400(self):
        resp = self.client.get(self.base)
        self.assertEqual(resp.status_code, 400)

    def test_legacy_rows_get_backfilled_row_id(self):
        # Імітуємо legacy-рядки без row_id (збережені старим full-PATCH).
        self.employee.custom_fields = {f"table_{self.table.id}": [{"posada": "Стажер"}]}
        self.employee.save(update_fields=["custom_fields"])
        resp = self.client.get(f"{self.base}?table={self.table.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data[0]["row_id"])
        # row_id персистентний — можна редагувати legacy-рядок
        row_id = resp.data[0]["row_id"]
        patched = self.client.patch(
            f"{self.base}{row_id}/?table={self.table.id}",
            {"values": {"posada": "Молодший лікар"}}, format="json",
        )
        self.assertEqual(patched.status_code, 200, patched.data)


class WorkDomainSyncApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr", password="test")
        self.client.force_authenticate(self.user)
        self.employee = Employee.objects.create(first_name="Іван", last_name="Сидоренко")
        self.manager = Employee.objects.create(first_name="Олена", last_name="Керівник")
        self.clinic = Clinic.objects.create(name="Клініка Центр")
        self.department = Department.objects.create(name="Стоматологія", clinic=self.clinic)
        self.division = Division.objects.create(name="Хірургія")
        self.job_level = JobLevel.objects.create(name="Senior")
        self.position = Position.objects.create(name="Лікар-стоматолог")
        self.emp_type = EmploymentType.objects.create(name="Повна зайнятість")

        group = EmployeeFieldGroup.objects.create(tab="work", name="Робота", slug="job")
        self.posady = EmployeeFieldTable.objects.create(
            group=group, name="Посади", sync_target="positions",
            columns=[
                {"key": "die_z", "label": "Діє з", "type": "date"},
                {"key": "menedzher", "label": "Менеджер", "type": "employee"},
                {"key": "riven", "label": "Рівень", "type": "select", "options": ["Senior"]},
                {"key": "posada", "label": "Посада", "type": "select", "options": ["Лікар-стоматолог"]},
                {"key": "departament", "label": "Департамент", "type": "select", "options": ["Стоматологія"]},
                {"key": "pidrozdil", "label": "Підрозділ", "type": "select", "options": ["Хірургія"]},
                {"key": "lokatsiya", "label": "Локація", "type": "select", "options": ["Клініка Центр"]},
            ],
        )
        self.robota = EmployeeFieldTable.objects.create(
            group=group, name="Робота", sync_target="employment",
            columns=[
                {"key": "die_z", "label": "Діє з", "type": "date"},
                {"key": "tip_roboti", "label": "Тип роботи", "type": "select", "options": ["Повна зайнятість"]},
                {"key": "grafik", "label": "Графік", "type": "select", "options": ["5/2"]},
                {"key": "komentar", "label": "Коментар", "type": "textarea"},
            ],
        )
        self.base = f"/api/employees/employees/{self.employee.id}/table-rows/"

    def _add_posady_row(self, **values):
        return self.client.post(
            f"{self.base}?table={self.posady.id}", {"values": values}, format="json"
        )

    def test_posady_row_syncs_employee_and_history(self):
        resp = self._add_posady_row(
            die_z="2026-01-15", menedzher=str(self.manager.id), riven="Senior",
            posada="Лікар-стоматолог", departament="Стоматологія",
            pidrozdil="Хірургія", lokatsiya="Клініка Центр",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.position_id, self.position.id)
        self.assertEqual(self.employee.department_id, self.department.id)
        self.assertEqual(self.employee.division_id, self.division.id)
        self.assertEqual(self.employee.clinic_id, self.clinic.id)
        self.assertEqual(self.employee.job_level_id, self.job_level.id)
        # ManagerAssignment створено
        self.assertTrue(
            ManagerAssignment.objects.filter(employee=self.employee, manager=self.manager).exists()
        )
        # Історія: один запис
        self.assertEqual(
            EmployeePositionHistory.objects.filter(employee=self.employee).count(), 1
        )

    def test_latest_row_wins_for_current_fields(self):
        old_pos = Position.objects.create(name="Стажер")
        self._add_posady_row(die_z="2025-01-01", posada="Стажер")
        self._add_posady_row(die_z="2026-06-01", posada="Лікар-стоматолог")
        self.employee.refresh_from_db()
        # Поточна посада = з останнього (новішого) рядка
        self.assertEqual(self.employee.position_id, self.position.id)
        # Історія містить обидва записи
        self.assertEqual(
            EmployeePositionHistory.objects.filter(employee=self.employee).count(), 2
        )

    def test_deleting_row_removes_history_record(self):
        created = self._add_posady_row(die_z="2026-01-15", posada="Лікар-стоматолог").data
        self.client.delete(f"{self.base}{created['row_id']}/?table={self.posady.id}")
        self.assertEqual(
            EmployeePositionHistory.objects.filter(employee=self.employee).count(), 0
        )

    def test_robota_row_syncs_employment_status(self):
        resp = self.client.post(
            f"{self.base}?table={self.robota.id}",
            {"values": {"die_z": "2026-02-01", "tip_roboti": "Повна зайнятість",
                        "grafik": "5/2", "komentar": "Основне місце"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.employment_type_id, self.emp_type.id)
        status_row = EmployeeEmploymentStatus.objects.filter(employee=self.employee).first()
        self.assertIsNotNone(status_row)
        self.assertEqual(status_row.working_pattern_name, "5/2")
        self.assertEqual(status_row.comment, "Основне місце")

    def test_unresolved_name_does_not_wipe_field(self):
        # Спочатку коректний рядок
        self._add_posady_row(die_z="2026-01-01", posada="Лікар-стоматолог")
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.position_id, self.position.id)
        # Новий рядок з невідомою назвою посади — поле НЕ має обнулитися
        self._add_posady_row(die_z="2026-03-01", posada="Невідома посада")
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.position_id, self.position.id)
