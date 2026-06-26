from django.test import override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.test import APITestCase

from apps.employees.models import Employee, EmployeeEmploymentStatus, WorkingPattern
from apps.skud.models import AttendancePeriod, WorkDaySummary


@override_settings(HR_PUBLIC_READ_API=True)
class CompanyAttendanceSummaryTests(APITestCase):
    def test_planned_minutes_fallback_uses_default_working_pattern(self):
        employee = Employee.objects.create(first_name="Ірина", last_name="Тестова")
        WorkingPattern.objects.create(
            name="За замовчуванням",
            monday_hours=8,
            is_default=True,
        )

        response = self.client.get(
            reverse("company-attendance-summary"),
            {"from": "2026-06-01", "to": "2026-06-01", "page_size": 10},
        )

        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.data["results"] if item["employee"] == employee.id)
        self.assertEqual(row["planned_minutes"], 480)
        self.assertEqual(row["total_absence_minutes"], 480)
        self.assertEqual(row["difference_minutes"], -480)

    def test_planned_minutes_fallback_uses_employee_status_working_pattern(self):
        employee = Employee.objects.create(first_name="Олег", last_name="Півдня")
        WorkingPattern.objects.create(
            name="За замовчуванням",
            monday_hours=8,
            is_default=True,
        )
        WorkingPattern.objects.create(name="Part-time", monday_hours=4)
        EmployeeEmploymentStatus.objects.create(
            employee=employee,
            effective_from="2026-01-01",
            working_pattern_name="Part-time",
        )

        response = self.client.get(
            reverse("company-attendance-summary"),
            {"from": "2026-06-01", "to": "2026-06-01", "page_size": 10},
        )

        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.data["results"] if item["employee"] == employee.id)
        self.assertEqual(row["planned_minutes"], 240)

    def test_existing_workday_summary_planned_minutes_take_priority(self):
        employee = Employee.objects.create(first_name="Марія", last_name="Підсумок")
        WorkingPattern.objects.create(
            name="За замовчуванням",
            monday_hours=8,
            is_default=True,
        )
        WorkDaySummary.objects.create(
            employee=employee,
            date="2026-06-01",
            planned_minutes=300,
            actual_minutes=120,
        )

        response = self.client.get(
            reverse("company-attendance-summary"),
            {"from": "2026-06-01", "to": "2026-06-01", "page_size": 10},
        )

        self.assertEqual(response.status_code, 200)
        row = next(item for item in response.data["results"] if item["employee"] == employee.id)
        self.assertEqual(row["planned_minutes"], 300)
        self.assertEqual(row["actual_minutes"], 120)

    def test_employee_attendance_detail_returns_daily_periods_and_schedule_plan(self):
        employee = Employee.objects.create(first_name="Олександр", last_name="Кузьменко")
        WorkingPattern.objects.create(
            name="За замовчуванням",
            monday_hours=8,
            is_default=True,
        )
        AttendancePeriod.objects.create(
            employee=employee,
            date="2026-06-01",
            start_at=timezone.make_aware(timezone.datetime(2026, 6, 1, 9, 0)),
            end_at=timezone.make_aware(timezone.datetime(2026, 6, 1, 13, 30)),
            duration_minutes=270,
        )

        response = self.client.get(
            reverse("employee-attendance-detail", kwargs={"employee_id": employee.id}),
            {"from": "2026-06-01", "to": "2026-06-01"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["employee"]["id"], employee.id)
        self.assertEqual(response.data["summary"]["planned_minutes"], 480)
        self.assertEqual(response.data["summary"]["actual_minutes"], 270)
        self.assertEqual(response.data["summary"]["difference_minutes"], -210)
        self.assertEqual(len(response.data["days"]), 1)
        self.assertEqual(response.data["days"][0]["planned_minutes"], 480)
        self.assertEqual(response.data["days"][0]["actual_minutes"], 270)
        self.assertEqual(len(response.data["days"][0]["periods"]), 1)

    @override_settings(HR_PUBLIC_WRITE_API=True)
    def test_employee_attendance_period_can_be_created_updated_and_deleted(self):
        employee = Employee.objects.create(first_name="Наталія", last_name="Бережна")

        create_response = self.client.post(
            reverse("employee-attendance-period-create", kwargs={"employee_id": employee.id}),
            {"date": "2026-05-07", "start_time": "06:57", "end_time": "17:05", "comment": "manual"},
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        period = AttendancePeriod.objects.get(employee=employee)
        self.assertEqual(period.duration_minutes, 608)
        self.assertEqual(period.period_type, AttendancePeriod.PeriodType.MANUAL)

        update_response = self.client.patch(
            reverse("employee-attendance-period-detail", kwargs={"employee_id": employee.id, "period_id": period.id}),
            {"date": "2026-05-07", "start_time": "07:03", "end_time": "17:11"},
            format="json",
        )

        self.assertEqual(update_response.status_code, 200)
        period.refresh_from_db()
        self.assertEqual(period.duration_minutes, 608)
        self.assertEqual(period.period_type, AttendancePeriod.PeriodType.MANUAL)

        delete_response = self.client.delete(
            reverse("employee-attendance-period-detail", kwargs={"employee_id": employee.id, "period_id": period.id}),
        )

        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(AttendancePeriod.objects.filter(pk=period.id).exists())

    @override_settings(HR_PUBLIC_READ_API=False, HR_PUBLIC_WRITE_API=False)
    def test_authenticated_employee_attendance_period_update_delete_with_csrf(self):
        user = get_user_model().objects.create_user(username="hr-user", password="pass")
        employee = Employee.objects.create(user=user, first_name="Оксана", last_name="Тест")
        period = AttendancePeriod.objects.create(
            employee=employee,
            date="2026-05-07",
            start_at=timezone.make_aware(timezone.datetime(2026, 5, 7, 6, 57)),
            end_at=timezone.make_aware(timezone.datetime(2026, 5, 7, 17, 5)),
            duration_minutes=608,
        )
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(user)
        status_response = client.get(reverse("auth-status"))
        csrf_token = status_response.cookies["hr_csrftoken"].value

        update_response = client.patch(
            reverse("employee-attendance-period-detail", kwargs={"employee_id": employee.id, "period_id": period.id}),
            {"date": "2026-05-07", "start_time": "07:03", "end_time": "17:11"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(update_response.status_code, 200)
        period.refresh_from_db()
        self.assertEqual(timezone.localtime(period.start_at).strftime("%H:%M"), "07:03")
        self.assertEqual(timezone.localtime(period.end_at).strftime("%H:%M"), "17:11")

        delete_response = client.delete(
            reverse("employee-attendance-period-detail", kwargs={"employee_id": employee.id, "period_id": period.id}),
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(AttendancePeriod.objects.filter(pk=period.id).exists())
