"""Permission registry (RBAC, Этап 1 + расширение до PeopleForce 1:1).

Стабильный каталог permission-кодов HR Vidnova с метаданными. Это ТОЛЬКО
словарь прав — здесь НЕТ enforcement (он во flag-gated DRF, Этап 4).

Структура (как в PF, вкладка «Компанія»):
  group (категория: general/hr/pulse/time/reports/settings) → section → permission.
Группа `self` — права, относящиеся к данным самого человека / field-level; они НЕ
показываются на вкладке «Компанія» (пойдут на вкладку «Люди», фаза 2).

Виды прав (kind для UI):
- graded  → levels=(VIEW, EDIT): сегмент Немає·Перегляд·Редагування.
- bool    → levels=(VIEW,) или (): чекбокс. `on_level` — что писать при включении
            ('view' для view-only, '' для atomic-действия).

Подписи (`label`/`description`) — украинские (единственный потребитель каталога —
наш фронт). Источник формулировок: docs/роли/peopleforce-company-permissions-reference.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AccessLevel(str, Enum):
    VIEW = "view"
    EDIT = "edit"
    # «none» = отсутствие права; отдельным значением не хранится.


# Категории (левая навигация вкладки «Компанія») + служебная self.
class Group(str, Enum):
    GENERAL = "general"
    HR = "hr"
    PULSE = "pulse"
    TIME = "time"
    REPORTS = "reports"
    SETTINGS = "settings"
    SELF = "self"


CODE_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")
_SEGMENT_RE = re.compile(r"^[a-z0-9_]+$")

# Префикс field-level прав на профиль; см. field_permission_code().
FIELD_PERMISSION_PREFIX = "people.field"
# Системные вкладки профиля (apps.employees EmployeeFieldGroup.Tab).
PROFILE_FIELD_TABS = ("personal", "work", "compensation")


@dataclass(frozen=True)
class Permission:
    code: str
    module: str
    group: Group
    section: str
    action: str
    label: str
    description: str
    risk: RiskLevel
    levels: tuple[AccessLevel, ...] = field(default_factory=tuple)

    @property
    def is_graded(self) -> bool:
        return AccessLevel.EDIT in self.levels

    @property
    def kind(self) -> str:
        return "graded" if self.is_graded else "bool"

    @property
    def on_level(self) -> str:
        """Уровень, который пишем при включении bool-права."""
        if self.is_graded:
            return ""  # для graded уровень выбирается сегментом
        return AccessLevel.VIEW.value if AccessLevel.VIEW in self.levels else ""


def _p(code, module, group, section, action, label, description, risk, levels=()):  # noqa: PLR0913
    return Permission(
        code=code, module=module, group=group, section=section, action=action,
        label=label, description=description, risk=risk, levels=tuple(levels),
    )


_V = (AccessLevel.VIEW,)
_VE = (AccessLevel.VIEW, AccessLevel.EDIT)

PERMISSIONS: tuple[Permission, ...] = (
    # ═══════════════ КАТЕГОРИЯ «Загальні» (general) ═══════════════
    # ── Домашня сторінка ──────────────────────────────────────────────────────
    _p("announcements.publish", "announcements", Group.GENERAL, "home", "publish",
       "Публікувати оголошення та опитування", "Створювати оголошення й опитування компанії.", RiskLevel.MEDIUM),
    _p("company_links.manage", "company_links", Group.GENERAL, "home", "manage",
       "Керувати посиланнями компанії", "Додавати й редагувати швидкі посилання компанії.", RiskLevel.LOW),
    _p("announcements.read", "announcements", Group.GENERAL, "home", "read",
       "Переглядати оголошення", "Бачити оголошення та опитування.", RiskLevel.LOW, _V),

    # ── Календар ──────────────────────────────────────────────────────────────
    _p("calendar.view", "calendar", Group.GENERAL, "calendar", "view",
       "Дозволити доступ до календаря компанії", "Бачити календар компанії.", RiskLevel.LOW, _V),
    _p("calendar.manage_events", "calendar", Group.GENERAL, "calendar", "manage_events",
       "Управляти подіями в календарі компанії", "Створювати й редагувати події календаря.", RiskLevel.MEDIUM),
    _p("calendar.view_leave", "calendar", Group.GENERAL, "calendar", "view_leave",
       "Переглядати запити на відсутність", "Бачити відсутності в календарі.", RiskLevel.LOW, _V),
    _p("calendar.view_birthdays", "calendar", Group.GENERAL, "calendar", "view_birthdays",
       "Переглядати дні народження співробітників", "Бачити дні народження в календарі.", RiskLevel.LOW, _V),
    _p("calendar.view_first_day", "calendar", Group.GENERAL, "calendar", "view_first_day",
       "Переглядати перший день співробітників", "Бачити перші робочі дні в календарі.", RiskLevel.LOW, _V),
    _p("calendar.view_anniversaries", "calendar", Group.GENERAL, "calendar", "view_anniversaries",
       "Переглядати річниці співробітників", "Бачити робочі річниці в календарі.", RiskLevel.LOW, _V),
    _p("calendar.view_probation_end", "calendar", Group.GENERAL, "calendar", "view_probation_end",
       "Переглядати завершення випробувального терміну", "Бачити завершення випроб. терміну в календарі.", RiskLevel.LOW, _V),
    _p("calendar.view_last_day", "calendar", Group.GENERAL, "calendar", "view_last_day",
       "Переглядати останній день співробітників", "Бачити останні робочі дні в календарі.", RiskLevel.LOW, _V),

    # ── Люди ──────────────────────────────────────────────────────────────────
    _p("people.directory", "people", Group.GENERAL, "people", "directory",
       "Дозволити доступ до каталогу людей", "Бачити каталог співробітників компанії.", RiskLevel.LOW, _V),
    _p("people.advanced_search", "people", Group.GENERAL, "people", "advanced_search",
       "Дозволити розширений пошук по співробітниках",
       "Фільтрувати за будь-яким полем, якщо є дозвіл на перегляд/редагування цього поля.", RiskLevel.MEDIUM),
    _p("people.org_chart", "people", Group.GENERAL, "people", "org_chart",
       "Дозволити доступ до організаційних діаграм", "Бачити організаційні діаграми.", RiskLevel.LOW, _V),
    _p("hiring.manage", "hiring", Group.GENERAL, "people", "manage",
       "Найняти нових людей у компанію", "Наймати нових людей і бачити всіх активних та найнятих.", RiskLevel.HIGH),
    _p("system_access.manage", "system_access", Group.GENERAL, "people", "manage",
       "Вмк./вимк. доступ співробітників до системи", "Дозволяти або обмежувати доступ співробітників до системи.", RiskLevel.CRITICAL),
    _p("people.invite", "people", Group.GENERAL, "people", "invite",
       "Надіслати запрошення в систему", "Надсилати співробітникам запрошення в систему.", RiskLevel.MEDIUM),
    _p("people.view_offboarded", "people", Group.GENERAL, "people", "view_offboarded",
       "Переглядати звільнених співробітників", "Бачити всіх звільнених співробітників у компанії.", RiskLevel.MEDIUM, _V),
    _p("people.terminate", "people", Group.GENERAL, "people", "terminate",
       "Звільняти людей по всій компанії", "Звільняти співробітників у компанії.", RiskLevel.HIGH),
    _p("people.onboarding", "people", Group.GENERAL, "people", "onboarding",
       "Управління онбордингом", "Бачити деталі співробітників, які проходять онбординг.", RiskLevel.MEDIUM),
    _p("people.offboarding", "people", Group.GENERAL, "people", "offboarding",
       "Управління офбордингом", "Бачити деталі співробітників, які проходять офбординг.", RiskLevel.MEDIUM),
    _p("people.probation", "people", Group.GENERAL, "people", "probation",
       "Управління випробувальним терміном", "Бачити всіх працівників на випробувальному терміні.", RiskLevel.MEDIUM),
    _p("people.ats_inbound", "people", Group.GENERAL, "people", "ats_inbound",
       "Керування вхідними з ATS", "Переглядати й керувати імпортованими кандидатами з ATS.", RiskLevel.MEDIUM),
    _p("people.photo_manage", "people", Group.GENERAL, "people", "photo_manage",
       "Змінювати фотографії людей", "Завантажувати/замінювати фото співробітників.", RiskLevel.MEDIUM),
    _p("people.delete", "people", Group.GENERAL, "people", "delete",
       "Видаляти людей з компанії", "Остаточно видаляти записи співробітників.", RiskLevel.CRITICAL),

    # ── Завдання ──────────────────────────────────────────────────────────────
    _p("tasks.create", "tasks", Group.GENERAL, "tasks", "create",
       "Створити завдання", "Створювати завдання.", RiskLevel.LOW),
    _p("tasks.manage", "tasks", Group.GENERAL, "tasks", "manage",
       "Керувати завданнями", "Перегляд і керування всіма завданнями компанії.", RiskLevel.MEDIUM),

    # ── База знань ────────────────────────────────────────────────────────────
    _p("knowledge.read", "knowledge", Group.GENERAL, "knowledge", "read",
       "Доступ до бази знань", "Читати контент бази знань, доступний або яким поділилися.", RiskLevel.LOW, _V),
    _p("knowledge.manage_shared", "knowledge", Group.GENERAL, "knowledge", "manage_shared",
       "Створювати та керувати статтями, якими поділилися",
       "Створювати/редагувати контент у межах доступних категорій і статей.", RiskLevel.MEDIUM),
    _p("knowledge.manage", "knowledge", Group.GENERAL, "knowledge", "manage",
       "Створювати всі статті й категорії та керувати ними",
       "Повний контроль над статтями й категоріями без обмежень доступу.", RiskLevel.HIGH),

    # ── Інші ──────────────────────────────────────────────────────────────────
    _p("requests.manage", "requests", Group.GENERAL, "other", "manage",
       "Перегляд і керування запитами компанії", "Переглядати й керувати запитами компанії.", RiskLevel.MEDIUM),
    _p("offers.manage", "offers", Group.GENERAL, "other", "manage",
       "Керування пропозиціями", "Переглядати й керувати пропозиціями.", RiskLevel.MEDIUM),

    # ═══════════════ КАТЕГОРИЯ «HR» (hr) ═══════════════
    _p("leave.schedule", "leave", Group.HR, "hr", "schedule",
       "Дозволити доступ до графіка відсутностей", "Бачити всі відсутності компанії в графіку.", RiskLevel.LOW, _V),
    _p("leave.approve", "leave", Group.HR, "hr", "approve",
       "Затвердити та відхилити відсутності", "Перегляд і керування всіма відсутностями співробітників.", RiskLevel.HIGH),
    _p("leave.policies", "leave", Group.HR, "hr", "policies",
       "Керувати політиками відсутностей", "Додавати/вилучати політики відсутностей співробітників.", RiskLevel.HIGH),
    _p("documents.manage", "documents", Group.HR, "hr", "manage",
       "Керувати документами співробітників", "Перегляд, керування та запит ел. підпису документів.", RiskLevel.CRITICAL),
    _p("workflow.manage", "workflow", Group.HR, "hr", "manage",
       "Управління воркфлоу", "Керувати воркфлоу всередині компанії.", RiskLevel.MEDIUM),
    _p("teams.manage", "teams", Group.HR, "hr", "manage",
       "Управління командами", "Перегляд/редагування команд і складу.", RiskLevel.MEDIUM, _VE),
    _p("assets.manage", "assets", Group.HR, "hr", "manage",
       "Керувати активами", "Перегляд/редагування активів.", RiskLevel.MEDIUM, _VE),

    # ═══════════════ КАТЕГОРИЯ «Pulse» (pulse) ═══════════════
    _p("surveys.manage", "surveys", Group.PULSE, "pulse", "manage",
       "Управління опитуваннями", "Створювати й керувати опитуваннями (Pulse).", RiskLevel.MEDIUM),

    # ═══════════════ КАТЕГОРИЯ «Time» (time) ═══════════════
    _p("time.attendance", "time", Group.TIME, "time", "attendance",
       "Доступ до даних про відвідуваність по компанії", "Бачити дані відвідуваності/СКУД.", RiskLevel.HIGH, _V),
    _p("time.approve", "time", Group.TIME, "time", "approve",
       "Затверджувати записи часу", "Рішення щодо запитів корекції часу.", RiskLevel.HIGH),
    _p("time.edit", "time", Group.TIME, "time", "edit",
       "Редагувати облік часу", "Редагувати записи часу по компанії.", RiskLevel.HIGH),

    # ═══════════════ КАТЕГОРИЯ «Звіти» (reports) ═══════════════
    _p("reports.custom", "reports", Group.REPORTS, "reports", "custom",
       "Створювати настроювані звіти", "Будувати настроювані звіти.", RiskLevel.MEDIUM),
    _p("reports.company", "reports", Group.REPORTS, "reports", "company",
       "Звіти компанії", "Доступ до звітів компанії.", RiskLevel.HIGH, _V),

    # ═══════════════ КАТЕГОРИЯ «Налаштування» (settings) ═══════════════
    _p("settings.general", "settings", Group.SETTINGS, "settings", "general",
       "Загальні налаштування", "Перегляд/редагування загальних налаштувань.", RiskLevel.MEDIUM, _VE),
    _p("settings.notifications", "settings", Group.SETTINGS, "settings", "notifications",
       "Налаштування сповіщень", "Перегляд/редагування налаштувань сповіщень.", RiskLevel.LOW, _VE),
    _p("roles.view", "roles", Group.SETTINGS, "settings", "view",
       "Перегляд ролей", "Бачити ролі та права.", RiskLevel.HIGH, _V),
    _p("roles.manage", "roles", Group.SETTINGS, "settings", "manage",
       "Керування ролями", "Створювати/редагувати ролі, права й призначення.", RiskLevel.CRITICAL),
    _p("integrations.manage", "integrations", Group.SETTINGS, "settings", "manage",
       "Керування інтеграціями", "Керувати API-ключами, вебхуками та імпортами.", RiskLevel.CRITICAL),
    _p("audit.view", "audit", Group.SETTINGS, "settings", "view",
       "Перегляд журналу аудиту", "Читати журнали аудиту/безпеки.", RiskLevel.HIGH, _V),

    # ═══════════════ ГРУППА «self» (вкладка «Люди» / self-service, фаза 2) ═══════
    _p("people.profile", "people", Group.SELF, "personal", "profile",
       "Профіль співробітника (PII)", "Доступ до карток профілю та PII.", RiskLevel.HIGH, _VE),
    _p("people.field.personal", "people", Group.SELF, "personal", "field_personal",
       "Поля профілю: особисте", "Перегляд/редагування особистих полів профілю.", RiskLevel.HIGH, _VE),
    _p("people.field.work", "people", Group.SELF, "work", "field_work",
       "Поля профілю: робота", "Перегляд/редагування робочих полів профілю.", RiskLevel.MEDIUM, _VE),
    _p("people.field.compensation", "people", Group.SELF, "compensation", "field_compensation",
       "Поля профілю: компенсація", "Перегляд/редагування полів компенсації.", RiskLevel.CRITICAL, _VE),
    _p("people.education", "people", Group.SELF, "personal", "education",
       "Освіта", "Перегляд/редагування записів про освіту.", RiskLevel.MEDIUM, _VE),
    _p("people.certificates", "people", Group.SELF, "personal", "certificates",
       "Сертифікати / ліцензії", "Перегляд/редагування сертифікатів і ліцензій.", RiskLevel.MEDIUM, _VE),
    _p("people.skills", "people", Group.SELF, "personal", "skills",
       "Навички", "Перегляд/редагування навичок співробітника.", RiskLevel.LOW, _VE),
    _p("people.dependents", "people", Group.SELF, "personal", "dependents",
       "Утриманці", "Перегляд/редагування утриманців (родинні PII).", RiskLevel.HIGH, _VE),
    _p("people.emergency_contacts", "people", Group.SELF, "personal", "emergency_contacts",
       "Екстрені контакти", "Перегляд/редагування екстрених контактів (PII).", RiskLevel.HIGH, _VE),
    _p("people.notes", "people", Group.SELF, "personal", "notes",
       "Примітки HR", "Перегляд/редагування HR-приміток про співробітника.", RiskLevel.HIGH, _VE),
    _p("documents.view", "documents", Group.SELF, "documents", "view",
       "Перегляд документів співробітника", "Бачити файли документів співробітника.", RiskLevel.HIGH, _V),
    _p("leave.requests", "leave", Group.SELF, "leave", "requests",
       "Заявки на відсутність", "Перегляд/створення заявок на відсутність.", RiskLevel.MEDIUM, _VE),
    _p("leave.balances", "leave", Group.SELF, "leave", "balances",
       "Баланси відсутностей", "Бачити баланси відсутностей.", RiskLevel.MEDIUM, _V),
)

PERMISSIONS_BY_CODE: dict[str, Permission] = {p.code: p for p in PERMISSIONS}

# Namespaces, обязательные по плану (Этап 1 acceptance).
REQUIRED_MODULES = frozenset(
    {"people", "leave", "time", "knowledge", "reports", "settings", "roles", "integrations"}
)

# ── Каталог вкладки «Компанія»: порядок категорий и секций + украинские заголовки.
COMPANY_CATEGORY_ORDER: tuple[str, ...] = ("general", "hr", "pulse", "time", "reports", "settings")

CATEGORY_LABELS: dict[str, str] = {
    "general": "Загальні",
    "hr": "HR",
    "pulse": "Pulse",
    "time": "Time",
    "reports": "Звіти",
    "settings": "Налаштування",
}

# Порядок секций внутри категории.
SECTION_ORDER: dict[str, tuple[str, ...]] = {
    "general": ("home", "calendar", "people", "tasks", "knowledge", "other"),
    "hr": ("hr",),
    "pulse": ("pulse",),
    "time": ("time",),
    "reports": ("reports",),
    "settings": ("settings",),
}

# Заголовки секций (пустая строка → секция без заголовка, плоский список).
SECTION_LABELS: dict[str, str] = {
    "home": "Домашня сторінка",
    "calendar": "Календар",
    "people": "Люди",
    "tasks": "Завдання",
    "knowledge": "База знань",
    "other": "Інші",
    "hr": "",
    "pulse": "",
    "time": "",
    "reports": "",
    "settings": "",
}


def get_permission(code: str) -> Permission | None:
    return PERMISSIONS_BY_CODE.get(code)


def all_codes() -> list[str]:
    return [p.code for p in PERMISSIONS]


def all_modules() -> list[str]:
    seen: list[str] = []
    for p in PERMISSIONS:
        if p.module not in seen:
            seen.append(p.module)
    return seen


def permissions_for_module(module: str) -> list[Permission]:
    return [p for p in PERMISSIONS if p.module == module]


def company_catalog() -> list[dict]:
    """Каталог прав вкладки «Компанія»: categories → sections → permissions.

    Группа `self` исключена (она на вкладке «Люди», фаза 2). Порядок —
    COMPANY_CATEGORY_ORDER / SECTION_ORDER; внутри секции — порядок в PERMISSIONS.
    """
    by_group_section: dict[str, dict[str, list[Permission]]] = {}
    for perm in PERMISSIONS:
        if perm.group == Group.SELF:
            continue
        by_group_section.setdefault(perm.group.value, {}).setdefault(perm.section, []).append(perm)

    categories: list[dict] = []
    for cat in COMPANY_CATEGORY_ORDER:
        sections_map = by_group_section.get(cat, {})
        sections: list[dict] = []
        for sec in SECTION_ORDER.get(cat, tuple(sections_map.keys())):
            perms = sections_map.get(sec, [])
            if not perms:
                continue
            sections.append(
                {
                    "key": sec,
                    "label": SECTION_LABELS.get(sec, ""),
                    "permissions": [_perm_dict(p) for p in perms],
                }
            )
        if sections:
            categories.append({"key": cat, "label": CATEGORY_LABELS.get(cat, cat), "sections": sections})
    return categories


def _perm_dict(perm: Permission) -> dict:
    return {
        "code": perm.code,
        "label": perm.label,
        "description": perm.description,
        "kind": perm.kind,
        "on_level": perm.on_level,
        "levels": [lvl.value for lvl in perm.levels],
        "risk": perm.risk.value,
    }


def field_permission_code(tab: str, field_slug: str) -> str:
    """Код field-level права на поле профиля: people.field.<tab>.<field_slug>."""
    tab = (tab or "").strip().lower()
    field_slug = (field_slug or "").strip().lower()
    if not _SEGMENT_RE.match(tab) or not _SEGMENT_RE.match(field_slug):
        raise ValueError(f"invalid field permission segments: tab={tab!r}, field={field_slug!r}")
    return f"{FIELD_PERMISSION_PREFIX}.{tab}.{field_slug}"


def parse_field_permission_code(code: str) -> tuple[str, str] | None:
    """Обратное к field_permission_code: вернуть (tab, field_slug) или None."""
    prefix = FIELD_PERMISSION_PREFIX + "."
    if not code.startswith(prefix):
        return None
    rest = code[len(prefix):]
    parts = rest.split(".")
    if len(parts) != 2 or not all(_SEGMENT_RE.match(part) for part in parts):
        return None
    return parts[0], parts[1]
