from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.access.permissions_registry import get_permission, parse_field_permission_code
from apps.access.role_seeds import ADMIN_ROLE_SLUG
from apps.employees.models import Employee, TimestampedModel


class EmployeeTelegramLink(TimestampedModel):
    class Source(models.TextChoices):
        SHARED_BOT = "shared_bot", "Shared Telegram bot"

    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="telegram_link")
    telegram_chat_id = models.BigIntegerField()
    telegram_user_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    telegram_username = models.CharField(max_length=160, blank=True)
    phone_normalized = models.CharField(max_length=32, db_index=True)
    source = models.CharField(max_length=40, choices=Source.choices, default=Source.SHARED_BOT)
    is_active = models.BooleanField(default=True)
    linked_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["employee__last_name", "employee__first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["telegram_chat_id"],
                condition=models.Q(is_active=True),
                name="uniq_active_telegram_chat_id",
            ),
        ]
        indexes = [
            models.Index(fields=["is_active", "phone_normalized"], name="tg_link_active_phone_idx"),
            models.Index(fields=["is_active", "telegram_chat_id"], name="tg_link_active_chat_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.employee} Telegram link"


class TelegramLoginCode(TimestampedModel):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="telegram_login_codes")
    telegram_link = models.ForeignKey(
        EmployeeTelegramLink,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="login_codes",
    )
    code_hash = models.CharField(max_length=160)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    request_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employee", "-created_at"], name="tg_code_employee_created_idx"),
            models.Index(fields=["employee", "consumed_at"], name="tg_code_employee_used_idx"),
            models.Index(fields=["expires_at", "consumed_at"], name="tg_code_expiry_used_idx"),
        ]

    @property
    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_usable(self) -> bool:
        return not self.is_consumed and not self.is_expired

    def __str__(self) -> str:
        return f"{self.employee} login code {self.created_at:%Y-%m-%d %H:%M}"


class AuthAuditEvent(models.Model):
    class Event(models.TextChoices):
        TELEGRAM_LINK_REQUESTED = "telegram_link_requested", "Telegram link requested"
        TELEGRAM_LINKED = "telegram_linked", "Telegram linked"
        LOGIN_CODE_REQUESTED = "login_code_requested", "Login code requested"
        LOGIN_CODE_SENT = "login_code_sent", "Login code sent"
        LOGIN_SUCCEEDED = "login_succeeded", "Login succeeded"
        LOGIN_FAILED = "login_failed", "Login failed"
        LOGOUT = "logout", "Logout"
        SESSION_EXPIRED = "session_expired", "Session expired"
        ACCESS_DENIED = "access_denied", "Access denied"

    class Result(models.TextChoices):
        OK = "ok", "OK"
        DENIED = "denied", "Denied"
        FAILED = "failed", "Failed"
        CONFLICT = "conflict", "Conflict"
        NOT_FOUND = "not_found", "Not found"
        LOCKED = "locked", "Locked"

    employee = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="auth_audit_events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hr_auth_audit_events",
    )
    telegram_link = models.ForeignKey(
        EmployeeTelegramLink,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    event = models.CharField(max_length=60, choices=Event.choices, db_index=True)
    result = models.CharField(max_length=30, choices=Result.choices, db_index=True)
    phone_normalized = models.CharField(max_length=32, blank=True, db_index=True)
    telegram_chat_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["event", "result", "-created_at"], name="auth_audit_event_result_idx"),
            models.Index(fields=["employee", "-created_at"], name="auth_audit_employee_idx"),
            models.Index(fields=["user", "-created_at"], name="auth_audit_user_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.event}:{self.result} {self.created_at:%Y-%m-%d %H:%M:%S}"


# ── RBAC (Этап 2): роли, права, назначения, audit ───────────────────────────


class AccessRole(TimestampedModel):
    """Роль RBAC. System-роли защищены от удаления; права наполняются отдельно."""

    class Type(models.TextChoices):
        SYSTEM = "system", "Системна"
        CUSTOM = "custom", "Кастомна"

    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    type = models.CharField(max_length=10, choices=Type.choices, default=Type.CUSTOM)
    is_active = models.BooleanField(default=True)
    # Для system-ролей: состав вычисляется правилом (scope engine), а не явными assignment.
    is_membership_computed = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"

    @property
    def is_system(self) -> bool:
        return self.type == self.Type.SYSTEM

    @property
    def is_admin(self) -> bool:
        return self.slug == ADMIN_ROLE_SLUG

    def delete(self, *args, **kwargs):
        if self.is_system:
            raise ValidationError("Системну роль не можна видалити.")
        return super().delete(*args, **kwargs)


class AccessRolePermission(TimestampedModel):
    """Связь роль -> permission code (из registry) с уровнем для graded прав."""

    role = models.ForeignKey(AccessRole, on_delete=models.CASCADE, related_name="permissions")
    permission_code = models.CharField(max_length=120)
    # "" для atomic прав; "view"/"edit" для graded.
    level = models.CharField(max_length=10, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission_code"], name="access_role_permission_unique"
            )
        ]

    def __str__(self) -> str:
        suffix = f":{self.level}" if self.level else ""
        return f"{self.role.slug} -> {self.permission_code}{suffix}"

    def clean(self):
        permission = get_permission(self.permission_code)
        if permission is None:
            # Динамічне field-level право на конкретне поле/таблицю профілю
            # (people.field.<tab>.<slug>) — у реєстрі немає, валідуємо за формою.
            if parse_field_permission_code(self.permission_code) is not None:
                if self.level not in {"view", "edit"}:
                    raise ValidationError(
                        {"level": f"Для {self.permission_code} рівень має бути view або edit."}
                    )
                return
            raise ValidationError({"permission_code": f"Невідомий permission code: {self.permission_code}"})
        if permission.levels:
            allowed = {level.value for level in permission.levels}
            if self.level not in allowed:
                raise ValidationError(
                    {"level": f"Для {self.permission_code} рівень має бути одним з {sorted(allowed)}."}
                )
        elif self.level:
            raise ValidationError({"level": f"{self.permission_code} — atomic право, рівень не задається."})

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)


class AccessRoleAssignment(TimestampedModel):
    """Назначение роли пользователю/сотруднику с object-level scope."""

    class ScopeType(models.TextChoices):
        SELF = "self", "Себе"
        ALL_COMPANY = "all_company", "Вся компанія"
        DIRECT_REPORTS = "direct_reports", "Прямі підлеглі"
        DIRECT_AND_INDIRECT_REPORTS = "direct_and_indirect_reports", "Прямі та непрямі підлеглі"
        TEAM_MEMBERS = "team_members", "Члени команди"
        CLINIC = "clinic", "Клініка"
        DEPARTMENT = "department", "Відділ"
        DIVISION = "division", "Підрозділ"
        EXPLICIT_EMPLOYEES = "explicit_employees", "Явний список"
        CUSTOM_CONDITIONS = "custom_conditions", "Кастомні умови"

    role = models.ForeignKey(AccessRole, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
        related_name="access_role_assignments",
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, null=True, blank=True,
        related_name="access_role_assignments",
    )
    # True -> назначение вычислено системным правилом, а не выдано вручную.
    is_system_computed = models.BooleanField(default=False)
    scope_type = models.CharField(max_length=40, choices=ScopeType.choices, default=ScopeType.SELF)
    # Доп. параметры scope: explicit employee ids, условия. Без secrets/PII-дампов.
    scope_payload = models.JSONField(default=dict, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["role", "is_active"], name="access_assignment_role_idx"),
            models.Index(fields=["user", "is_active"], name="access_assignment_user_idx"),
            models.Index(fields=["employee", "is_active"], name="access_assignment_emp_idx"),
        ]

    def __str__(self) -> str:
        target = self.user_id or self.employee_id or "—"
        return f"{self.role.slug} -> {target} [{self.scope_type}]"


class AccessRoleAuditEvent(models.Model):
    """Audit изменений RBAC. Без secrets/raw tokens в payload."""

    class Action(models.TextChoices):
        ROLE_CREATED = "role_created", "Роль створено"
        ROLE_UPDATED = "role_updated", "Роль оновлено"
        ROLE_DELETED = "role_deleted", "Роль видалено"
        PERMISSION_GRANTED = "permission_granted", "Право видано"
        PERMISSION_REVOKED = "permission_revoked", "Право відкликано"
        ASSIGNMENT_CREATED = "assignment_created", "Призначення створено"
        ASSIGNMENT_UPDATED = "assignment_updated", "Призначення оновлено"
        ASSIGNMENT_REMOVED = "assignment_removed", "Призначення знято"

    role = models.ForeignKey(
        AccessRole, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="access_audit_events",
    )
    action = models.CharField(max_length=40, choices=Action.choices, db_index=True)
    summary = models.CharField(max_length=300, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["action", "-created_at"], name="access_audit_action_idx"),
            models.Index(fields=["role", "-created_at"], name="access_audit_role_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.created_at:%Y-%m-%d %H:%M:%S}"
