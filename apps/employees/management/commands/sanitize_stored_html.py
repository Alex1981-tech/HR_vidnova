"""Backfill: прогнать уже сохранённый rich-text HTML через санитайзер (P4).

Санитайзер на serializer boundary защищает только новые записи. Эта команда
один раз приводит существующие строки к безопасному виду. Идемпотентна.

    python manage.py sanitize_stored_html            # применить
    python manage.py sanitize_stored_html --dry-run  # показать сколько изменится
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from config.sanitize import sanitize_rich_html


class Command(BaseCommand):
    help = "Sanitize stored body_html (announcements, employee notes, knowledge)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Только показать изменения, не сохранять.")

    def handle(self, *args, **options):
        from apps.announcements.models import Announcement
        from apps.employees.models import EmployeeNote
        from apps.knowledge.models import KnowledgeDocument

        dry = options["dry_run"]
        targets = (
            (Announcement, "body_html"),
            (EmployeeNote, "body_html"),
            (KnowledgeDocument, "body_html"),
        )
        total_changed = 0
        for model, field in targets:
            changed = 0
            qs = model.objects.exclude(**{field: ""}).exclude(**{f"{field}__isnull": True})
            for obj in qs.iterator():
                raw = getattr(obj, field) or ""
                cleaned = sanitize_rich_html(raw)
                if cleaned != raw:
                    changed += 1
                    if not dry:
                        setattr(obj, field, cleaned)
                        obj.save(update_fields=[field])
            total_changed += changed
            self.stdout.write(f"{model.__name__}.{field}: {changed} changed")
        prefix = "[dry-run] " if dry else ""
        self.stdout.write(self.style.SUCCESS(f"{prefix}total changed: {total_changed}"))
