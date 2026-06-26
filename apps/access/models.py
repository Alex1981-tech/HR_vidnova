from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

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
