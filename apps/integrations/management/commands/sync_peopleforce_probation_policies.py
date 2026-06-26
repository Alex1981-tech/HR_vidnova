from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.employees.models import EmployeeEmploymentStatus, ProbationPolicy
from apps.integrations.models import PeopleForceEntity, PeopleForceImportRun
from apps.integrations.peopleforce.client import PeopleForceClient
from apps.integrations.peopleforce.importer import clean, ext_id, int_value, name_of, payload_hash, trim


class Command(BaseCommand):
    help = "Import PeopleForce probation policies only and link existing employment statuses."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Fetch and count without writing probation policies.")

    def handle(self, *args, **options):
        counters: dict[str, int] = defaultdict(int)
        run = PeopleForceImportRun.objects.create(
            status=PeopleForceImportRun.Status.RUNNING,
            options={
                "command": "sync_peopleforce_probation_policies",
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

        self.stdout.write(self.style.SUCCESS(f"PeopleForce probation policies import run #{run.id}: {run.status}"))
        for key, value in sorted(counters.items()):
            self.stdout.write(f"{key}: {value}")

    def _sync(self, client: PeopleForceClient, run: PeopleForceImportRun, counters: dict[str, int], *, dry_run: bool) -> None:
        rows = client.list_all("/probation_policies")
        counters["fetched_probation_policies"] = len(rows)
        for payload in rows:
            self._upsert_probation_policy(payload, run, counters, dry_run=dry_run)
        self._link_employment_statuses(counters, dry_run=dry_run)

    def _upsert_probation_policy(
        self,
        payload: dict[str, Any],
        run: PeopleForceImportRun,
        counters: dict[str, int],
        *,
        dry_run: bool,
    ) -> ProbationPolicy | None:
        name = trim(clean(payload.get("name")), 180)
        external_id = ext_id(payload)
        if not name:
            counters["probation_policies_skipped"] += 1
            return None
        counters["probation_policies_seen"] += 1
        if dry_run:
            return None
        self._store_entity("probation_policies", external_id, "/probation_policies", payload, run)
        defaults = {
            "external_peopleforce_id": external_id,
            "duration_months": int_value(payload.get("length")),
            "is_active": True,
        }
        policy = ProbationPolicy.objects.filter(external_peopleforce_id=external_id).first() if external_id else None
        if policy is None:
            policy, created = ProbationPolicy.objects.get_or_create(name=name, defaults=defaults)
        else:
            created = False
            policy.name = name
            for field_name, value in defaults.items():
                setattr(policy, field_name, value)
            policy.save(update_fields=["name", *defaults.keys(), "updated_at"])
        if external_id and not policy.external_peopleforce_id:
            policy.external_peopleforce_id = external_id
            policy.save(update_fields=["external_peopleforce_id", "updated_at"])
        counters[f"probation_policies_{'created' if created else 'updated'}"] += 1
        return policy

    def _link_employment_statuses(self, counters: dict[str, int], *, dry_run: bool) -> None:
        statuses = EmployeeEmploymentStatus.objects.filter(probation_policy__isnull=True).exclude(probation_policy_name="")
        for status in statuses.iterator():
            payload = status.raw_payload.get("probation_policy") if isinstance(status.raw_payload, dict) else None
            policy = self._policy_by_payload(payload) or ProbationPolicy.objects.filter(name=status.probation_policy_name).first()
            if not policy:
                counters["employment_statuses_unlinked"] += 1
                continue
            counters["employment_statuses_linked"] += 1
            if not dry_run:
                status.probation_policy = policy
                status.save(update_fields=["probation_policy", "updated_at"])

    def _policy_by_payload(self, payload: Any) -> ProbationPolicy | None:
        external_id = ext_id(payload)
        if external_id:
            found = ProbationPolicy.objects.filter(external_peopleforce_id=external_id).first()
            if found:
                return found
        name = name_of(payload)
        if name:
            return ProbationPolicy.objects.filter(name=name).first()
        return None

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
