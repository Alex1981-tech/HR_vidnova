from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.leave.models import LeaveType


class LeaveTypeUnitApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr", password="test")
        self.client.force_authenticate(self.user)

    def test_create_defaults_to_days(self):
        resp = self.client.post("/api/leave/types/", {"name": "Відпустка"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["unit"], "days")

    def test_hours_accepted(self):
        resp = self.client.post(
            "/api/leave/types/", {"name": "Лікарняний", "unit": "hours"}, format="json"
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["unit"], "hours")

    def test_legacy_unit_normalized(self):
        resp = self.client.post(
            "/api/leave/types/", {"name": "Декрет", "unit": "Day"}, format="json"
        )
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["unit"], "days")

    def test_invalid_unit_rejected(self):
        resp = self.client.post(
            "/api/leave/types/", {"name": "Інше", "unit": "тижні"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
