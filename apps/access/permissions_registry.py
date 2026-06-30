"""Permission registry (RBAC, Этап 1).

Стабильный каталог permission-кодов HR Vidnova с метаданными. Это ТОЛЬКО
словарь прав — здесь НЕТ enforcement (он появится на Этапе 4 в DRF permission
classes/scopes). Источник vocabulary: docs/роли/peopleforce-roles-research.md.

Принципы:
- code — стабильный machine-id, не зависит от UI-локализации (label — dev-facing
  английский дескриптор; локализованные подписи живут на фронте по code).
- Два вида прав:
  * graded — поле/раздел с уровнями (`view`, `edit`); хранится `levels=(VIEW[, EDIT])`.
  * atomic — действие-флаг (approve, delete, manage); `levels=()`.
- Динамические права на поля профиля (`people.field.<tab>.<field>`) строятся
  хелпером `field_permission_code()` поверх системных и кастомных `EmployeeField`.
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


# UI-группы (вкладки company-матрицы PeopleForce). Стабильные ключи, не локализация.
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
    action: str
    label: str
    description: str
    risk: RiskLevel
    levels: tuple[AccessLevel, ...] = field(default_factory=tuple)

    @property
    def is_graded(self) -> bool:
        return bool(self.levels)


def _p(code, module, group, action, label, description, risk, levels=()):  # noqa: PLR0913
    return Permission(
        code=code, module=module, group=group, action=action,
        label=label, description=description, risk=risk, levels=tuple(levels),
    )


_V = (AccessLevel.VIEW,)
_VE = (AccessLevel.VIEW, AccessLevel.EDIT)

PERMISSIONS: tuple[Permission, ...] = (
    # ── people / directory / profile ────────────────────────────────────────
    _p("people.directory", "people", Group.GENERAL, "directory",
       "View people directory", "See the company people directory.", RiskLevel.LOW, _V),
    _p("people.profile", "people", Group.GENERAL, "profile",
       "View/edit employee profile (PII)", "Access employee profile cards and PII.", RiskLevel.HIGH, _VE),
    _p("people.org_chart", "people", Group.GENERAL, "org_chart",
       "View organization charts", "See org charts.", RiskLevel.LOW, _V),
    _p("people.photo_manage", "people", Group.GENERAL, "photo_manage",
       "Change employee photos", "Upload/replace employee photos.", RiskLevel.MEDIUM),
    _p("people.delete", "people", Group.GENERAL, "delete",
       "Delete people", "Permanently delete employee records.", RiskLevel.CRITICAL),

    # ── people field areas (system tabs); per-field via field_permission_code ─
    _p("people.field.personal", "people", Group.SELF, "field_personal",
       "Profile area: personal fields", "View/edit personal profile fields.", RiskLevel.HIGH, _VE),
    _p("people.field.work", "people", Group.SELF, "field_work",
       "Profile area: work fields", "View/edit work profile fields.", RiskLevel.MEDIUM, _VE),
    _p("people.field.compensation", "people", Group.SELF, "field_compensation",
       "Profile area: compensation fields", "View/edit compensation fields.", RiskLevel.CRITICAL, _VE),

    # ── self-fill ресурсы профиля ────────────────────────────────────────────
    _p("people.education", "people", Group.SELF, "education",
       "Education records", "View/edit employee education records.", RiskLevel.MEDIUM, _VE),
    _p("people.certificates", "people", Group.SELF, "certificates",
       "Certificates / licenses", "View/edit certificates and licenses.", RiskLevel.MEDIUM, _VE),
    _p("people.skills", "people", Group.SELF, "skills",
       "Skills", "View/edit employee skills.", RiskLevel.LOW, _VE),
    _p("people.dependents", "people", Group.SELF, "dependents",
       "Dependents", "View/edit dependents (family PII).", RiskLevel.HIGH, _VE),
    _p("people.emergency_contacts", "people", Group.SELF, "emergency_contacts",
       "Emergency contacts", "View/edit emergency contacts (PII).", RiskLevel.HIGH, _VE),
    _p("people.notes", "people", Group.HR, "notes",
       "Employee notes (HR)", "View/edit HR notes about an employee.", RiskLevel.HIGH, _VE),

    # ── hiring / system access ───────────────────────────────────────────────
    _p("hiring.manage", "hiring", Group.GENERAL, "manage",
       "Hiring / termination", "Hire and terminate employees.", RiskLevel.HIGH),
    _p("system_access.manage", "system_access", Group.GENERAL, "manage",
       "Manage employee system access", "Enable/disable access, invitations, password resets.", RiskLevel.CRITICAL),

    # ── announcements / calendar / knowledge ─────────────────────────────────
    _p("announcements.read", "announcements", Group.GENERAL, "read",
       "Read announcements", "View announcements and polls.", RiskLevel.LOW, _V),
    _p("announcements.publish", "announcements", Group.GENERAL, "publish",
       "Publish announcements", "Publish announcements and polls.", RiskLevel.MEDIUM),
    _p("calendar.view", "calendar", Group.GENERAL, "view",
       "View company calendar", "See the company calendar.", RiskLevel.LOW, _V),
    _p("knowledge.read", "knowledge", Group.GENERAL, "read",
       "Read knowledge base", "Read knowledge documents.", RiskLevel.LOW, _V),
    _p("knowledge.manage", "knowledge", Group.GENERAL, "manage",
       "Manage knowledge base", "Create/edit/delete knowledge documents.", RiskLevel.MEDIUM),

    # ── HR: documents / leave / teams / assets ───────────────────────────────
    _p("documents.view", "documents", Group.HR, "view",
       "View employee documents", "View employee document files.", RiskLevel.HIGH, _V),
    _p("documents.manage", "documents", Group.HR, "manage",
       "Manage employee documents", "Upload/replace/delete employee documents.", RiskLevel.CRITICAL),
    _p("leave.schedule", "leave", Group.HR, "schedule",
       "View absence schedule", "See company absence schedule.", RiskLevel.LOW, _V),
    _p("leave.requests", "leave", Group.HR, "requests",
       "Leave requests", "View/create leave requests.", RiskLevel.MEDIUM, _VE),
    _p("leave.balances", "leave", Group.HR, "balances",
       "View leave balances", "See leave balances.", RiskLevel.MEDIUM, _V),
    _p("leave.approve", "leave", Group.HR, "approve",
       "Approve/reject leave", "Decide on leave requests.", RiskLevel.HIGH),
    _p("leave.policies", "leave", Group.HR, "policies",
       "Manage leave policies", "Manage leave types/policies.", RiskLevel.HIGH),
    _p("teams.manage", "teams", Group.HR, "manage",
       "Manage teams", "View/edit teams and memberships.", RiskLevel.MEDIUM, _VE),
    _p("assets.manage", "assets", Group.HR, "manage",
       "Manage assets", "View/edit assets.", RiskLevel.MEDIUM, _VE),

    # ── Time / attendance ────────────────────────────────────────────────────
    _p("time.attendance", "time", Group.TIME, "attendance",
       "View attendance data", "See attendance/SKUD data.", RiskLevel.HIGH, _V),
    _p("time.approve", "time", Group.TIME, "approve",
       "Approve/reject time records", "Decide on time correction requests.", RiskLevel.HIGH),
    _p("time.edit", "time", Group.TIME, "edit",
       "Edit time tracking", "Edit time records company-wide.", RiskLevel.HIGH),

    # ── Reports ──────────────────────────────────────────────────────────────
    _p("reports.custom", "reports", Group.REPORTS, "custom",
       "Create custom reports", "Build custom reports.", RiskLevel.MEDIUM),
    _p("reports.company", "reports", Group.REPORTS, "company",
       "View company reports", "View company-level reports.", RiskLevel.HIGH, _V),

    # ── Settings / roles / integrations / audit ──────────────────────────────
    _p("settings.general", "settings", Group.SETTINGS, "general",
       "General settings", "View/edit general settings.", RiskLevel.MEDIUM, _VE),
    _p("settings.notifications", "settings", Group.SETTINGS, "notifications",
       "Notification settings", "View/edit notification settings.", RiskLevel.LOW, _VE),
    _p("roles.view", "roles", Group.SETTINGS, "view",
       "View roles", "View roles and permissions.", RiskLevel.HIGH, _V),
    _p("roles.manage", "roles", Group.SETTINGS, "manage",
       "Manage roles", "Create/edit roles, permissions and assignments.", RiskLevel.CRITICAL),
    _p("integrations.manage", "integrations", Group.SETTINGS, "manage",
       "Manage integrations", "Manage API keys, webhooks and imports.", RiskLevel.CRITICAL),
    _p("audit.view", "audit", Group.SETTINGS, "view",
       "View audit log", "Read audit/security logs.", RiskLevel.HIGH, _V),
)

PERMISSIONS_BY_CODE: dict[str, Permission] = {p.code: p for p in PERMISSIONS}

# Namespaces, обязательные по плану (Этап 1 acceptance).
REQUIRED_MODULES = frozenset(
    {"people", "leave", "time", "knowledge", "reports", "settings", "roles", "integrations"}
)


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


def field_permission_code(tab: str, field_slug: str) -> str:
    """Код field-level права на поле профиля: people.field.<tab>.<field_slug>.

    Покрывает и системные поля (tab из PROFILE_FIELD_TABS), и кастомные
    EmployeeField (любой валидный slug). Сегменты — [a-z0-9_].
    """
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
