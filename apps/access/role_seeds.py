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
        "description": "Повний доступ до всіх даних і налаштувань. Призначається вручну.",
        "membership_computed": False,
        "order": 0,
    },
    {
        "slug": "all_people",
        "name": "Усі люди",
        "description": "Базова роль усіх активних співробітників (довідник, календар, база знань).",
        "membership_computed": True,
        "order": 10,
    },
    {
        "slug": "self",
        "name": "Люди стосовно себе",
        "description": "Доступ кожного користувача до власних даних (self-service).",
        "membership_computed": True,
        "order": 20,
    },
    {
        "slug": "manager",
        "name": "Менеджери",
        "description": "Доступ керівників до даних прямих і непрямих підлеглих.",
        "membership_computed": True,
        "order": 30,
    },
    {
        "slug": "team_lead",
        "name": "Лідери команд",
        "description": "Доступ тимлідів до даних членів команди.",
        "membership_computed": True,
        "order": 40,
    },
    {
        "slug": "hr_admin",
        "name": "HR-адміністратори",
        "description": "Операційне керування HR-даними компанії. Призначається вручну.",
        "membership_computed": False,
        "order": 50,
    },
    {
        "slug": "hr_specialist",
        "name": "HR-спеціалісти",
        "description": "Операційний HR без повних адмін-прав. Призначається вручну.",
        "membership_computed": False,
        "order": 60,
    },
    {
        "slug": "knowledge_admin",
        "name": "Адміністратори бази знань",
        "description": "Керування базою знань. Призначається вручну.",
        "membership_computed": False,
        "order": 70,
    },
    {
        "slug": "timekeeper",
        "name": "Облік робочого часу",
        "description": "Відвідуваність і ручні корекції часу. Призначається вручну.",
        "membership_computed": False,
        "order": 80,
    },
    {
        "slug": "reports_viewer",
        "name": "Перегляд звітів",
        "description": "Доступ до звітів. Призначається вручну.",
        "membership_computed": False,
        "order": 90,
    },
    {
        "slug": "integration_admin",
        "name": "Адміністратори інтеграцій",
        "description": "API-ключі, вебхуки, імпорти. Призначається вручну.",
        "membership_computed": False,
        "order": 100,
    },
)
