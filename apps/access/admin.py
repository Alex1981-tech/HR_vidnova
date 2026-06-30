from __future__ import annotations

from django.contrib import admin

from .models import (
    AccessRole,
    AccessRoleAssignment,
    AccessRoleAuditEvent,
    AccessRolePermission,
    AuthAuditEvent,
    EmployeeTelegramLink,
    TelegramLoginCode,
)


def _mask_tail(value: object, visible: int = 4) -> str:
    text = str(value or "")
    if not text:
        return ""
    if len(text) <= visible:
        return "*" * len(text)
    return f"{'*' * (len(text) - visible)}{text[-visible:]}"


@admin.register(EmployeeTelegramLink)
class EmployeeTelegramLinkAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "masked_phone_normalized",
        "masked_telegram_chat_id",
        "telegram_username",
        "is_active",
        "linked_at",
        "last_seen_at",
    )
    search_fields = (
        "employee__last_name",
        "employee__first_name",
        "employee__middle_name",
        "employee__email",
        "telegram_username",
    )
    list_filter = ("is_active", "source", "linked_at", "last_seen_at")
    raw_id_fields = ("employee",)
    exclude = ("telegram_chat_id", "phone_normalized")
    readonly_fields = (
        "masked_phone_normalized",
        "masked_telegram_chat_id",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Phone")
    def masked_phone_normalized(self, obj: EmployeeTelegramLink) -> str:
        return _mask_tail(obj.phone_normalized)

    @admin.display(description="Telegram chat")
    def masked_telegram_chat_id(self, obj: EmployeeTelegramLink) -> str:
        return _mask_tail(obj.telegram_chat_id)


@admin.register(TelegramLoginCode)
class TelegramLoginCodeAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "code_hash_fingerprint",
        "expires_at",
        "consumed_at",
        "failed_attempts",
        "created_at",
    )
    list_filter = ("expires_at", "consumed_at", "created_at")
    raw_id_fields = ("employee", "telegram_link")
    exclude = ("code_hash",)
    readonly_fields = (
        "employee",
        "telegram_link",
        "code_hash_fingerprint",
        "expires_at",
        "consumed_at",
        "failed_attempts",
        "request_ip",
        "user_agent",
        "created_at",
        "updated_at",
    )

    @admin.display(description="Code hash")
    def code_hash_fingerprint(self, obj: TelegramLoginCode) -> str:
        if not obj.code_hash:
            return ""
        return f"{obj.code_hash[:8]}...{obj.code_hash[-8:]}"

    def has_add_permission(self, request) -> bool:
        return False


@admin.register(AuthAuditEvent)
class AuthAuditEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "event",
        "result",
        "employee",
        "user",
        "masked_phone_normalized",
        "masked_telegram_chat_id",
        "ip_address",
    )
    list_filter = ("event", "result", "created_at")
    search_fields = (
        "employee__last_name",
        "employee__first_name",
        "employee__middle_name",
        "user__username",
    )
    raw_id_fields = ("employee", "user", "telegram_link")
    exclude = ("phone_normalized", "telegram_chat_id")
    readonly_fields = (
        "created_at",
        "employee",
        "user",
        "telegram_link",
        "event",
        "result",
        "masked_phone_normalized",
        "masked_telegram_chat_id",
        "ip_address",
        "user_agent",
        "metadata",
    )

    @admin.display(description="Phone")
    def masked_phone_normalized(self, obj: AuthAuditEvent) -> str:
        return _mask_tail(obj.phone_normalized)

    @admin.display(description="Telegram chat")
    def masked_telegram_chat_id(self, obj: AuthAuditEvent) -> str:
        return _mask_tail(obj.telegram_chat_id)

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


# ── RBAC admin (Этап 2) ──────────────────────────────────────────────────────


class AccessRolePermissionInline(admin.TabularInline):
    model = AccessRolePermission
    extra = 0
    fields = ("permission_code", "level")


@admin.register(AccessRole)
class AccessRoleAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "type", "is_active", "is_membership_computed", "order")
    list_filter = ("type", "is_active", "is_membership_computed")
    search_fields = ("slug", "name", "description")
    inlines = (AccessRolePermissionInline,)
    readonly_fields = ("created_at", "updated_at")

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        # slug system-роли менять нельзя (стабильный machine-id).
        if obj is not None and obj.is_system:
            ro.append("slug")
        return tuple(ro)

    def has_delete_permission(self, request, obj=None) -> bool:
        if obj is not None and obj.is_system:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(AccessRoleAssignment)
class AccessRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("role", "user", "employee", "scope_type", "is_system_computed", "is_active")
    list_filter = ("role", "scope_type", "is_active", "is_system_computed")
    search_fields = ("user__username", "employee__last_name", "employee__first_name", "role__slug")
    raw_id_fields = ("user", "employee")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AccessRoleAuditEvent)
class AccessRoleAuditEventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "role", "actor", "summary")
    list_filter = ("action", "created_at")
    search_fields = ("summary", "role__slug", "actor__username")
    raw_id_fields = ("role", "actor")
    readonly_fields = ("created_at", "action", "role", "actor", "summary", "payload")

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
