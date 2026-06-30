"""Idempotent seed прав ролей по утверждённой матрице (RBAC, после Этапа 0).

Приводит permission grants системных ролей в точное соответствие
`apps/access/role_matrix.py` (добавляет недостающие, обновляет уровень, удаляет
лишние — для ролей, присутствующих в матрице). `admin` не трогаем (bypass).

    python manage.py seed_access_role_permissions
    python manage.py seed_access_role_permissions --dry-run
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.access.role_matrix import ROLE_PERMISSIONS


class Command(BaseCommand):
    help = "Sync role permission grants to the approved matrix (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        from apps.access.models import AccessRole, AccessRolePermission

        dry = options["dry_run"]
        created = updated = removed = missing_roles = 0

        for slug, grants in ROLE_PERMISSIONS.items():
            role = AccessRole.objects.filter(slug=slug).first()
            if role is None:
                missing_roles += 1
                self.stderr.write(f"role not found, skipped: {slug} (run seed_access_roles first)")
                continue

            desired = {code: level for code, level in grants}
            current = {p.permission_code: p for p in role.permissions.all()}

            for code, perm in current.items():
                if code not in desired:
                    removed += 1
                    if not dry:
                        perm.delete()
            for code, level in desired.items():
                perm = current.get(code)
                if perm is None:
                    created += 1
                    if not dry:
                        AccessRolePermission.objects.create(
                            role=role, permission_code=code, level=level
                        )
                elif perm.level != level:
                    updated += 1
                    if not dry:
                        perm.level = level
                        perm.save(update_fields=["level", "updated_at"])

        prefix = "[dry-run] " if dry else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}grants created={created} updated={updated} removed={removed} "
                f"missing_roles={missing_roles}"
            )
        )
