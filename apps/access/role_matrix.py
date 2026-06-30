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
}
