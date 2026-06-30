"""Idempotent seed системных RBAC-ролей (Этап 2).

Создаёт «оболочки» системных ролей БЕЗ permission grants (наполнение прав =
матрица, зависит от Этапа 0). Повторный запуск не создаёт дубликатов и
обновляет name/description/order/membership у существующих system-ролей.

    python manage.py seed_access_roles
    python manage.py seed_access_roles --dry-run
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.access.role_seeds import SYSTEM_ROLE_SEEDS


class Command(BaseCommand):
    help = "Seed system RBAC roles (idempotent, empty roles)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        from apps.access.models import AccessRole

        dry = options["dry_run"]
        created = updated = 0
        for seed in SYSTEM_ROLE_SEEDS:
            defaults = {
                "name": seed["name"],
                "description": seed["description"],
                "type": AccessRole.Type.SYSTEM,
                "is_membership_computed": seed["membership_computed"],
                "order": seed["order"],
            }
            existing = AccessRole.objects.filter(slug=seed["slug"]).first()
            if existing is None:
                created += 1
                if not dry:
                    AccessRole.objects.create(slug=seed["slug"], **defaults)
                continue
            # Обновляем метаданные системной роли (не трогаем is_active).
            changed = any(getattr(existing, key) != value for key, value in defaults.items())
            if changed:
                updated += 1
                if not dry:
                    for key, value in defaults.items():
                        setattr(existing, key, value)
                    existing.save(update_fields=[*defaults.keys(), "updated_at"])

        prefix = "[dry-run] " if dry else ""
        self.stdout.write(self.style.SUCCESS(f"{prefix}roles created={created} updated={updated}"))
