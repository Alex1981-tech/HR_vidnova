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
from apps.access.permissions_registry import (
    company_catalog,
    field_permission_code,
    parse_field_permission_code,
)
from apps.access.rbac_invariants import would_remove_last_admin
from apps.access.role_seeds import ADMIN_ROLE_SLUG
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
        return Response({"categories": company_catalog()})


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

    def _members_payload(self, role):
        rows = list(
            AccessRoleAssignment.objects.filter(role=role, employee__isnull=False)
            .values('employee_id', 'is_active')
        )
        return {
            'members': [{'employee_id': r['employee_id'], 'is_active': r['is_active']} for r in rows],
            'people_count': rbac.role_people_count(role),
        }

    @action(detail=True, methods=["get", "post"], url_path="members")
    def members(self, request, pk=None):
        """Состав роли: GET — список со статусом, POST {add:[ids]} — добавить/реактивировать."""
        role = self.get_object()
        if request.method.lower() == 'get':
            return Response(self._members_payload(role))

        raw = request.data.get('add', [])
        if not isinstance(raw, list):
            raise DRFValidationError('add має бути списком id.')
        try:
            wanted = {int(x) for x in raw}
        except (TypeError, ValueError):
            raise DRFValidationError('add містить некоректні значення.')
        if not wanted:
            return Response(self._members_payload(role))

        existing = {
            a.employee_id: a
            for a in AccessRoleAssignment.objects.filter(role=role, employee_id__in=wanted)
        }
        for emp_id in wanted:
            assignment = existing.get(emp_id)
            if assignment is None:
                AccessRoleAssignment.objects.create(
                    role=role, employee_id=emp_id,
                    scope_type=AccessRoleAssignment.ScopeType.ALL_COMPANY, is_active=True,
                )
            elif not assignment.is_active:
                assignment.is_active = True
                assignment.save(update_fields=['is_active', 'updated_at'])
        _audit(
            request.user, role, Action.ASSIGNMENT_CREATED,
            f'До ролі {role.slug} додано {len(wanted)} осіб',
        )
        return Response(self._members_payload(role))

    @action(detail=True, methods=["post"], url_path="member-action")
    def member_action(self, request, pk=None):
        """Дія над одним членом ролі: remove | deactivate | activate."""
        role = self.get_object()
        try:
            emp_id = int(request.data.get('employee_id'))
        except (TypeError, ValueError):
            raise DRFValidationError('employee_id обовʼязковий.')
        op = request.data.get('action')
        if op not in {'remove', 'deactivate', 'activate'}:
            raise DRFValidationError('action має бути remove | deactivate | activate.')

        assignment = AccessRoleAssignment.objects.filter(role=role, employee_id=emp_id).first()
        if assignment is None:
            raise DRFValidationError('Цю людину не призначено на роль.')

        if op in {'remove', 'deactivate'} and would_remove_last_admin(assignment):
            raise DRFValidationError('Не можна зняти останнього адміністратора системи.')

        if op == 'remove':
            assignment.delete()
            _audit(request.user, role, Action.ASSIGNMENT_REMOVED, f'Знято з ролі {role.slug}: emp {emp_id}')
        elif op == 'deactivate':
            if assignment.is_active:
                assignment.is_active = False
                assignment.save(update_fields=['is_active', 'updated_at'])
            _audit(request.user, role, Action.ASSIGNMENT_UPDATED, f'Деактивовано в ролі {role.slug}: emp {emp_id}')
        else:  # activate
            if not assignment.is_active:
                assignment.is_active = True
                assignment.save(update_fields=['is_active', 'updated_at'])
            _audit(request.user, role, Action.ASSIGNMENT_UPDATED, f'Активовано в ролі {role.slug}: emp {emp_id}')
        return Response(self._members_payload(role))

    # ── Вкладка «Люди» (field-level доступ) ───────────────────────────────────
    def _field_access_payload(self, role):
        """Структура полів профілю (вкладки→групи→поля/таблиці) з рівнями ролі."""
        from apps.employees.models import EmployeeFieldGroup

        grants = {
            p.permission_code: p.level
            for p in AccessRolePermission.objects.filter(role=role)
        }

        def lvl(tab, slug):
            return grants.get(field_permission_code(tab, slug), "")

        tabs = []
        for tab_value, tab_label in EmployeeFieldGroup.Tab.choices:
            groups_out = []
            groups = (
                EmployeeFieldGroup.objects.filter(tab=tab_value)
                .prefetch_related("fields", "tables")
                .order_by("order", "id")
            )
            for group in groups:
                fields_out = [
                    {
                        "code": field_permission_code(tab_value, f"field_{f.id}"),
                        "label": f.name,
                        "level": lvl(tab_value, f"field_{f.id}"),
                    }
                    for f in group.fields.all().order_by("order", "id")
                    if f.is_enabled
                ]
                tables_out = [
                    {
                        "code": field_permission_code(tab_value, f"table_{t.id}"),
                        "label": t.name,
                        "level": lvl(tab_value, f"table_{t.id}"),
                    }
                    for t in group.tables.all().order_by("order", "id")
                    if t.is_enabled
                ]
                if fields_out or tables_out:
                    groups_out.append(
                        {"id": group.id, "name": group.name, "fields": fields_out, "tables": tables_out}
                    )
            tabs.append({"key": tab_value, "label": tab_label, "groups": groups_out})
        return {"tabs": tabs}

    @action(detail=True, methods=["get", "post"], url_path="field-access")
    def field_access(self, request, pk=None):
        """GET — структура полів з рівнями; POST {items:[{code,level}]} — зберегти."""
        role = self.get_object()
        if request.method.lower() == "get":
            return Response(self._field_access_payload(role))

        items = request.data.get("items", [])
        if not isinstance(items, list):
            raise DRFValidationError("items має бути списком.")
        changed = 0
        for item in items:
            code = (item or {}).get("code", "")
            level = (item or {}).get("level", "") or ""
            if parse_field_permission_code(code) is None:
                raise DRFValidationError(f"Невідоме field-право: {code}")
            if level not in {"", "view", "edit"}:
                raise DRFValidationError("level має бути '', view або edit.")
            if level:
                AccessRolePermission.objects.update_or_create(
                    role=role, permission_code=code, defaults={"level": level}
                )
            else:
                AccessRolePermission.objects.filter(role=role, permission_code=code).delete()
            changed += 1
        _audit(request.user, role, Action.ROLE_UPDATED, f"Поля ролі {role.slug}: {changed} змін")
        return Response(self._field_access_payload(role))


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
