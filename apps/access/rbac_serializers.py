"""Сериализаторы RBAC management API (Этап 6)."""

from __future__ import annotations

from django.utils.text import slugify
from rest_framework import serializers

from apps.access import rbac
from apps.access.models import (
    AccessRole,
    AccessRoleAssignment,
    AccessRoleAuditEvent,
    AccessRolePermission,
)
from apps.access.permissions_registry import get_permission


class AccessRolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRolePermission
        fields = ("permission_code", "level")


class AccessRoleSerializer(serializers.ModelSerializer):
    permissions = AccessRolePermissionSerializer(many=True, read_only=True)
    people_count = serializers.SerializerMethodField()

    class Meta:
        model = AccessRole
        fields = (
            "id", "slug", "name", "description", "type", "is_active",
            "is_membership_computed", "order", "people_count", "permissions",
        )
        read_only_fields = ("slug", "type", "is_membership_computed", "people_count", "permissions")

    def get_people_count(self, obj):
        return rbac.role_people_count(obj)

    def validate_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Назва обов'язкова.")
        return value

    def create(self, validated_data):
        # Через API создаются только кастомные роли.
        validated_data["type"] = AccessRole.Type.CUSTOM
        base = slugify(validated_data["name"])[:70] or "role"
        slug, i = base, 1
        while AccessRole.objects.filter(slug=slug).exists():
            i += 1
            slug = f"{base}-{i}"
        validated_data["slug"] = slug
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # slug у любой роли неизменяем через API.
        validated_data.pop("slug", None)
        return super().update(instance, validated_data)


class SetPermissionsItemSerializer(serializers.Serializer):
    permission_code = serializers.CharField()
    level = serializers.CharField(allow_blank=True, required=False, default="")

    def validate(self, attrs):
        perm = get_permission(attrs["permission_code"])
        if perm is None:
            raise serializers.ValidationError({"permission_code": "Невідомий код права."})
        level = attrs.get("level") or ""
        if perm.levels:
            allowed = {lvl.value for lvl in perm.levels}
            if level not in allowed:
                raise serializers.ValidationError({"level": f"Має бути одне з {sorted(allowed)}."})
        elif level:
            raise serializers.ValidationError({"level": "Atomic право — без рівня."})
        attrs["level"] = level
        return attrs


class AccessRoleAssignmentSerializer(serializers.ModelSerializer):
    role_slug = serializers.CharField(source="role.slug", read_only=True)

    class Meta:
        model = AccessRoleAssignment
        fields = (
            "id", "role", "role_slug", "user", "employee", "is_system_computed",
            "scope_type", "scope_payload", "valid_from", "valid_to", "is_active",
        )
        read_only_fields = ("is_system_computed",)

    def validate(self, attrs):
        user = attrs.get("user", getattr(self.instance, "user", None))
        employee = attrs.get("employee", getattr(self.instance, "employee", None))
        if not user and not employee:
            raise serializers.ValidationError("Потрібно вказати user або employee.")
        return attrs


class AccessRoleAuditEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    role_slug = serializers.CharField(source="role.slug", read_only=True)

    class Meta:
        model = AccessRoleAuditEvent
        fields = ("id", "action", "role", "role_slug", "actor", "actor_name", "summary", "payload", "created_at")
        read_only_fields = fields

    def get_actor_name(self, obj):
        if not obj.actor_id:
            return ""
        return obj.actor.get_full_name() or obj.actor.get_username()
