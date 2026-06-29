from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.employees.models import Employee
from apps.projects.models import Project


class ProjectApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="hr", password="test")
        self.client.force_authenticate(self.user)
        self.emp1 = Employee.objects.create(first_name="Іван", last_name="Петренко")
        self.emp2 = Employee.objects.create(first_name="Олена", last_name="Коваль")

    def test_create_defaults_emoji(self):
        resp = self.client.post("/api/projects/", {"name": "Тест"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["emoji"], "📁")
        self.assertEqual(resp.data["member_count"], 0)
        self.assertEqual(resp.data["order"], 1)

    def test_create_with_emoji(self):
        resp = self.client.post("/api/projects/", {"name": "Запуск", "emoji": "🚀"}, format="json")
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.data["emoji"], "🚀")

    def test_list_returns_member_count(self):
        project = Project.objects.create(name="A")
        project.members.add(self.emp1, self.emp2)
        resp = self.client.get("/api/projects/")
        self.assertEqual(resp.status_code, 200)
        row = next(r for r in resp.data["results"] if r["id"] == project.id)
        self.assertEqual(row["member_count"], 2)

    def test_filter_archived(self):
        Project.objects.create(name="Active", is_archived=False)
        Project.objects.create(name="Old", is_archived=True)
        active = self.client.get("/api/projects/?archived=false")
        self.assertEqual({r["name"] for r in active.data["results"]}, {"Active"})
        archived = self.client.get("/api/projects/?archived=true")
        self.assertEqual({r["name"] for r in archived.data["results"]}, {"Old"})

    def test_filter_q(self):
        Project.objects.create(name="Маркетинг")
        Project.objects.create(name="Розробка")
        resp = self.client.get("/api/projects/?q=марк")
        self.assertEqual({r["name"] for r in resp.data["results"]}, {"Маркетинг"})

    def test_add_and_remove_members(self):
        project = Project.objects.create(name="A")
        add = self.client.post(
            f"/api/projects/{project.id}/add-members/",
            {"employee_ids": [self.emp1.id, self.emp2.id]},
            format="json",
        )
        self.assertEqual(add.status_code, 200, add.data)
        self.assertEqual(add.data["member_count"], 2)
        names = {m["full_name"] for m in add.data["members"]}
        self.assertIn("Петренко Іван", names)
        remove = self.client.post(
            f"/api/projects/{project.id}/remove-members/",
            {"employee_ids": [self.emp1.id]},
            format="json",
        )
        self.assertEqual(remove.status_code, 200, remove.data)
        self.assertEqual(remove.data["member_count"], 1)

    def test_add_members_invalid_payload(self):
        project = Project.objects.create(name="A")
        resp = self.client.post(
            f"/api/projects/{project.id}/add-members/", {"employee_ids": "x"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_archive_unarchive(self):
        project = Project.objects.create(name="A")
        arch = self.client.post(f"/api/projects/{project.id}/archive/")
        self.assertEqual(arch.status_code, 200)
        self.assertTrue(arch.data["is_archived"])
        unarch = self.client.post(f"/api/projects/{project.id}/unarchive/")
        self.assertFalse(unarch.data["is_archived"])

    def test_detail_has_members(self):
        project = Project.objects.create(name="A")
        project.members.add(self.emp1)
        resp = self.client.get(f"/api/projects/{project.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["members"][0]["full_name"], "Петренко Іван")
