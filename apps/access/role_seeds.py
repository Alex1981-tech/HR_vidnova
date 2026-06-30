"""Определения системных ролей для idempotent seed (RBAC, Этап 2).

Роли создаются ПУСТЫМИ (без permission grants) — наполнение прав = матрица,
которая зависит от Этапа 0 (бизнес-решения Alex). Здесь только «оболочки» ролей,
их тип, описание и способ определения состава участников.
"""

from __future__ import annotations

# Slug суперроли — защищён last-admin инвариантом.
ADMIN_ROLE_SLUG = "admin"


# membership_computed=True -> состав вычисляется правилом (Этап 3 scope engine),
# а не явными assignment. False -> участники назначаются вручную.
SYSTEM_ROLE_SEEDS: tuple[dict, ...] = (
    {
        "slug": ADMIN_ROLE_SLUG,
        "name": "Адміністратори",
        "description": "Адміністратори — це суперкористувачі, вони мають доступ до всього й можуть керувати всіма даними",
        "membership_computed": False,
        "order": 0,
    },
    {
        "slug": "all_people",
        "name": "Усі люди",
        "description": "Права доступу для перегляду інших людей у вашій компанії",
        "membership_computed": True,
        "order": 10,
    },
    {
        "slug": "self",
        "name": "Люди стосовно себе",
        "description": "Права доступу до власних даних людей",
        "membership_computed": True,
        "order": 20,
    },
    {
        "slug": "manager",
        "name": "Менеджери",
        "description": "Права доступу менеджерів до даних їхніх прямих і непрямих підлеглих",
        "membership_computed": True,
        "order": 30,
    },
    {
        "slug": "team_lead",
        "name": "Лідери команд",
        "description": "Права доступу тимлідів до даних членів їхньої команди",
        "membership_computed": True,
        "order": 40,
    },
)

# Функциональные роли (HR/timekeeper/knowledge/reports/integration) НЕ системные —
# их админ создаёт как кастомные через /settings/roles по необходимости (как в PF).
# Только 5 системных ролей seed'ятся автоматически.
