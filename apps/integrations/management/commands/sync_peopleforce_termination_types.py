from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.employees.models import TerminationType
from apps.integrations.models import PeopleForceEntity, PeopleForceImportRun
from apps.integrations.peopleforce.client import PeopleForceClient
from apps.integrations.peopleforce.importer import clean, ext_id, payload_hash, trim


class Command(BaseCommand):
    help = "Import PeopleForce termination types only."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Fetch and count without writing termination types.")

    def handle(self, *args, **options):
        counters: dict[str, int] = defaultdict(int)
        run = PeopleForceImportRun.objects.create(
            status=PeopleForceImportRun.Status.RUNNING,
            options={
                "command": "sync_peopleforce_termination_types",
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

        self.stdout.write(self.style.SUCCESS(f"PeopleForce termination types import run #{run.id}: {run.status}"))
        for key, value in sorted(counters.items()):
            self.stdout.write(f"{key}: {value}")

    def _sync(self, client: PeopleForceClient, run: PeopleForceImportRun, counters: dict[str, int], *, dry_run: bool) -> None:
        rows = client.list_all("/termination_types")
        counters["fetched_termination_types"] = len(rows)
        for payload in rows:
            self._upsert_type(payload, run, counters, dry_run=dry_run)

    def _upsert_type(
        self,
        payload: dict[str, Any],
        run: PeopleForceImportRun,
        counters: dict[str, int],
        *,
        dry_run: bool,
    ) -> TerminationType | None:
        name = trim(clean(payload.get("name")), 180)
        external_id = ext_id(payload)
        if not name:
            counters["termination_types_skipped"] += 1
            return None
        counters["termination_types_seen"] += 1
        if dry_run:
            return None
        self._store_entity("termination_types", external_id, "/termination_types", payload, run)
        termination_type = TerminationType.objects.filter(external_peopleforce_id=external_id).first() if external_id else None
        if termination_type is None:
            termination_type, created = TerminationType.objects.get_or_create(
                name=name,
                defaults={"external_peopleforce_id": external_id, "is_active": True},
            )
        else:
            created = False
            termination_type.name = name
            termination_type.is_active = True
            termination_type.save(update_fields=["name", "is_active", "updated_at"])
        if external_id and not termination_type.external_peopleforce_id:
            termination_type.external_peopleforce_id = external_id
            termination_type.save(update_fields=["external_peopleforce_id", "updated_at"])
        counters[f"termination_types_{'created' if created else 'updated'}"] += 1
        return termination_type

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
