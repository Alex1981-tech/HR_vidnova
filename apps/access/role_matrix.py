"""Утверждённая матрица прав ролей (RBAC, после Этапа 0).

Решения Alex (2026-06-30):
- #1 manager attendance — только scope подчинённых (роль manager имеет scope
  reports, поэтому grant `time.attendance` view автоматически ограничен).
- #2 admins назначают только admin'ы → `roles.manage` ни одной роли тут не выдаём
  (только admin через bypass).
- #5 компенсация — admin/hr_admin (edit), hr_specialist (view), остальные none.

`admin` отсутствует в матрице намеренно: это суперроль с bypass (rbac.is_admin).

Computed-роли (all_people/self/manager/team_lead) имеют встроенный scope (Этап 3),
поэтому их grant'ы автоматически ограничены этим scope.
"""

from __future__ import annotations

# slug -> [(permission_code, level)]; level "" для atomic, "view"/"edit" для graded.
ROLE_PERMISSIONS: dict[str, list[tuple[str, str]]] = {
    "all_people": [
        ("people.directory", "view"),
        ("people.org_chart", "view"),
        ("calendar.view", "view"),
        ("announcements.read", "view"),
        ("knowledge.read", "view"),
        ("leave.schedule", "view"),
    ],
    "self": [
        ("people.field.personal", "view"),
        ("people.field.work", "view"),
        # people.field.compensation НЕ выдаём (решение #5: self -> none)
        ("people.education", "edit"),
        ("people.certificates", "edit"),
        ("people.skills", "edit"),
        ("people.dependents", "edit"),
        ("people.emergency_contacts", "edit"),
        ("leave.requests", "edit"),
        ("leave.balances", "view"),
        ("documents.view", "view"),
    ],
    # manager: добавки сверх all_people; scope роли = прямые+непрямые подчинённые.
    "manager": [
        ("people.profile", "view"),
        ("time.attendance", "view"),  # решение #1: только в scope подчинённых
        ("leave.requests", "view"),
    ],
    # team_lead: scope = активные члены команды.
    "team_lead": [
        ("people.profile", "view"),
    ],
    "hr_admin": [
        ("people.profile", "edit"),
        ("people.field.personal", "edit"),
        ("people.field.work", "edit"),
        ("people.field.compensation", "edit"),  # решение #5
        ("people.education", "edit"),
        ("people.certificates", "edit"),
        ("people.skills", "edit"),
        ("people.dependents", "edit"),
        ("people.emergency_contacts", "edit"),
        ("people.notes", "edit"),
        ("people.photo_manage", ""),
        ("documents.view", "view"),
        ("documents.manage", ""),
        ("leave.requests", "edit"),
        ("leave.balances", "view"),
        ("leave.approve", ""),
        ("leave.policies", ""),
        ("leave.schedule", "view"),
        ("time.attendance", "view"),
        ("time.approve", ""),
        ("time.edit", ""),
        ("teams.manage", "edit"),
        ("assets.manage", "edit"),
        ("reports.company", "view"),
        ("reports.custom", ""),
        ("hiring.manage", ""),
        ("system_access.manage", ""),
    ],
    "hr_specialist": [
        ("people.profile", "edit"),
        ("people.field.personal", "edit"),
        ("people.field.work", "edit"),
        ("people.field.compensation", "view"),  # решение #5: hr_specialist -> view
        ("people.education", "edit"),
        ("people.certificates", "edit"),
        ("people.skills", "edit"),
        ("people.dependents", "edit"),
        ("people.emergency_contacts", "edit"),
        ("people.notes", "edit"),
        ("documents.view", "view"),
        ("leave.requests", "edit"),
        ("leave.balances", "view"),
        ("leave.schedule", "view"),
    ],
    "knowledge_admin": [
        ("knowledge.read", "view"),
        ("knowledge.manage", ""),
    ],
    "timekeeper": [
        ("time.attendance", "view"),
        ("time.approve", ""),
        ("time.edit", ""),
        ("leave.schedule", "view"),
    ],
    "reports_viewer": [
        ("reports.company", "view"),
        ("reports.custom", ""),
    ],
    "integration_admin": [
        ("integrations.manage", ""),
        ("settings.general", "view"),
    ],
}
