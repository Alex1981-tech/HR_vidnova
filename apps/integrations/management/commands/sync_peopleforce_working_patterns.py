from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.employees.models import WorkingPattern
from apps.integrations.models import PeopleForceEntity, PeopleForceImportRun
from apps.integrations.peopleforce.client import PeopleForceClient
from apps.integrations.peopleforce.importer import clean, ext_id, payload_hash, trim, working_pattern_defaults


class Command(BaseCommand):
    help = "Import PeopleForce working patterns only."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Fetch and count without writing working patterns.")

    def handle(self, *args, **options):
        counters: dict[str, int] = defaultdict(int)
        run = PeopleForceImportRun.objects.create(
            status=PeopleForceImportRun.Status.RUNNING,
            options={
                "command": "sync_peopleforce_working_patterns",
                "dry_run": options["dry_run"],
            },
        )
        try:
            client = PeopleForceClient()
            if options["dry_run"]:
                self._sync(client, run, counters, dry_run=True)
            else:
                with transaction.atomic():
                    self._sync(client, run, counters, dry_run=False)
            run.status = PeopleForceImportRun.Status.DRY_RUN if options["dry_run"] else PeopleForceImportRun.Status.COMPLETED
            run.finished_at = timezone.now()
            run.counters = dict(counters)
            run.save(update_fields=["status", "finished_at", "counters", "updated_at"])
        except ImproperlyConfigured as exc:
            run.status = PeopleForceImportRun.Status.FAILED
            run.finished_at = timezone.now()
            run.error_message = str(exc)
            run.counters = dict(counters)
            run.save(update_fields=["status", "finished_at", "error_message", "counters", "updated_at"])
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            run.status = PeopleForceImportRun.Status.FAILED
            run.finished_at = timezone.now()
            run.error_message = str(exc)
            run.counters = dict(counters)
            run.save(update_fields=["status", "finished_at", "error_message", "counters", "updated_at"])
            raise

        self.stdout.write(self.style.SUCCESS(f"PeopleForce working patterns import run #{run.id}: {run.status}"))
        for key, value in sorted(counters.items()):
            self.stdout.write(f"{key}: {value}")

    def _sync(self, client: PeopleForceClient, run: PeopleForceImportRun, counters: dict[str, int], *, dry_run: bool) -> None:
        rows = client.list_all("/working_patterns")
        counters["fetched_working_patterns"] = len(rows)
        for payload in rows:
            self._upsert_working_pattern(payload, run, counters, dry_run=dry_run)

    def _upsert_working_pattern(
        self,
        payload: dict[str, Any],
        run: PeopleForceImportRun,
        counters: dict[str, int],
        *,
        dry_run: bool,
    ) -> WorkingPattern | None:
        name = trim(clean(payload.get("name")), 180)
        external_id = ext_id(payload)
        if not name:
            counters["working_patterns_skipped"] += 1
            return None
        counters["working_patterns_seen"] += 1
        if dry_run:
            return None
        self._store_entity("working_patterns", external_id, "/working_patterns", payload, run)
        defaults = working_pattern_defaults(payload)
        working_pattern = WorkingPattern.objects.filter(external_peopleforce_id=external_id).first() if external_id else None
        if working_pattern is None:
            working_pattern, created = WorkingPattern.objects.get_or_create(
                name=name,
                defaults={"external_peopleforce_id": external_id, **defaults},
            )
        else:
            created = False
            working_pattern.name = name
            for field_name, value in defaults.items():
                setattr(working_pattern, field_name, value)
            working_pattern.save(update_fields=["name", *defaults.keys(), "updated_at"])
        if external_id and not working_pattern.external_peopleforce_id:
            working_pattern.external_peopleforce_id = external_id
            working_pattern.save(update_fields=["external_peopleforce_id", "updated_at"])
        counters[f"working_patterns_{'created' if created else 'updated'}"] += 1
        return working_pattern

    def _store_entity(
        self,
        entity_type: str,
        external_id: str,
        endpoint: str,
        payload: dict[str, Any],
        run: PeopleForceImportRun,
    ) -> None:
        if not external_id:
            return
        PeopleForceEntity.objects.update_or_create(
            entity_type=entity_type,
            external_id=external_id,
            defaults={
                "endpoint": endpoint,
                "payload": payload,
                "payload_hash": payload_hash(payload),
                "fetched_at": timezone.now(),
                "last_run": run,
            },
        )
