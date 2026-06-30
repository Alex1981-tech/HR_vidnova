"""RBAC management API (Этап 6) для страницы /settings/roles."""

from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access import rbac
from apps.access.models import (
    AccessRole,
    AccessRoleAssignment,
    AccessRoleAuditEvent,
    AccessRolePermission,
)
from apps.access.permissions_registry import PERMISSIONS
from apps.access.rbac_invariants import would_remove_last_admin
from apps.access.rbac_serializers import (
    AccessRoleAssignmentSerializer,
    AccessRoleAuditEventSerializer,
    AccessRoleSerializer,
    SetPermissionsItemSerializer,
)
from apps.employees.models import Employee

Action = AccessRoleAuditEvent.Action


class RolesAPIPermission(BasePermission):
    """Управление ролями всегда требует roles.view/roles.manage (не shadow-gated)."""

    message = "Потрібні права керування ролями."

    def has_permission(self, request, view):
        code = "roles.view" if request.method in SAFE_METHODS else "roles.manage"
        return rbac.has_perm(request.user, code)


def _audit(actor, role, action, summary, payload=None):
    AccessRoleAuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        role=role,
        action=action,
        summary=summary[:300],
        payload=payload or {},
    )


class PermissionCatalogView(APIView):
    permission_classes = [RolesAPIPermission]

    def get(self, request):
        groups: dict[str, list] = {}
        for perm in PERMISSIONS:
            groups.setdefault(perm.group.value, []).append(
                {
                    "code": perm.code,
                    "module": perm.module,
                    "action": perm.action,
                    "label": perm.label,
                    "description": perm.description,
                    "risk": perm.risk.value,
                    "levels": [lvl.value for lvl in perm.levels],
                }
            )
        return Response({"groups": groups})


class AccessRoleViewSet(viewsets.ModelViewSet):
    permission_classes = [RolesAPIPermission]
    serializer_class = AccessRoleSerializer
    queryset = AccessRole.objects.all().prefetch_related("permissions")

    def perform_create(self, serializer):
        role = serializer.save()
        _audit(self.request.user, role, Action.ROLE_CREATED, f"Створено роль {role.slug}")

    def perform_update(self, serializer):
        role = serializer.save()
        _audit(self.request.user, role, Action.ROLE_UPDATED, f"Оновлено роль {role.slug}")

    def perform_destroy(self, instance):
        if instance.is_system:
            raise DRFValidationError("Системну роль не можна видалити.")
        slug = instance.slug
        _audit(self.request.user, None, Action.ROLE_DELETED, f"Видалено роль {slug}")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="set-permissions")
    def set_permissions(self, request, pk=None):
        role = self.get_object()
        serializer = SetPermissionsItemSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        desired = {item["permission_code"]: item["level"] for item in serializer.validated_data}
        current = {p.permission_code: p for p in role.permissions.all()}
        added = changed = removed = 0
        for code, perm in current.items():
            if code not in desired:
                perm.delete()
                removed += 1
        for code, level in desired.items():
            perm = current.get(code)
            if perm is None:
                AccessRolePermission.objects.create(role=role, permission_code=code, level=level)
                added += 1
            elif perm.level != level:
                perm.level = level
                perm.save(update_fields=["level", "updated_at"])
                changed += 1
        _audit(
            request.user, role, Action.PERMISSION_GRANTED,
            f"Права ролі {role.slug}: +{added} ~{changed} -{removed}",
            {"added": added, "changed": changed, "removed": removed},
        )
        role.refresh_from_db()
        return Response(AccessRoleSerializer(role).data)


class AccessRoleAssignmentViewSet(viewsets.ModelViewSet):
    permission_classes = [RolesAPIPermission]
    serializer_class = AccessRoleAssignmentSerializer

    def get_queryset(self):
        qs = AccessRoleAssignment.objects.select_related("role", "user", "employee")
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role__slug=role)
        return qs

    def perform_create(self, serializer):
        assignment = serializer.save()
        _audit(
            self.request.user, assignment.role, Action.ASSIGNMENT_CREATED,
            f"Призначено роль {assignment.role.slug}",
        )

    def perform_update(self, serializer):
        instance = serializer.instance
        deactivating = serializer.validated_data.get("is_active") is False and instance.is_active
        if deactivating and would_remove_last_admin(instance):
            raise DRFValidationError("Не можна зняти останнього адміністратора системи.")
        assignment = serializer.save()
        _audit(
            self.request.user, assignment.role, Action.ASSIGNMENT_UPDATED,
            f"Оновлено призначення ролі {assignment.role.slug}",
        )

    def perform_destroy(self, instance):
        if would_remove_last_admin(instance):
            raise DRFValidationError("Не можна зняти останнього адміністратора системи.")
        role = instance.role
        _audit(self.request.user, role, Action.ASSIGNMENT_REMOVED, f"Знято призначення ролі {role.slug}")
        instance.delete()


class AccessRoleAuditViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [RolesAPIPermission]
    serializer_class = AccessRoleAuditEventSerializer

    def get_queryset(self):
        qs = AccessRoleAuditEvent.objects.select_related("role", "actor")
        role = self.request.query_params.get("role")
        if role:
            qs = qs.filter(role__slug=role)
        return qs


class EffectiveAccessPreviewView(APIView):
    """Превью людей по scope (без сохранения) — для UI назначения роли."""

    permission_classes = [RolesAPIPermission]

    def post(self, request):
        scope_type = request.data.get("scope_type")
        scope_payload = request.data.get("scope_payload") or {}
        anchor_id = request.data.get("employee_id")
        anchor = Employee.objects.filter(pk=anchor_id).first() if anchor_id else None
        ids = rbac.preview_employee_ids(scope_type, scope_payload, anchor)
        if ids is None:
            qs = Employee.objects.all()
            total = qs.count()
        else:
            qs = Employee.objects.filter(pk__in=ids)
            total = len(ids)
        sample = [
            {"id": e.id, "full_name": e.full_name}
            for e in qs.order_by("last_name", "first_name")[:10]
        ]
        return Response({"count": total, "all_company": ids is None, "sample": sample})
