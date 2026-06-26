from __future__ import annotations

from collections import defaultdict
from typing import Any

import httpx
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.employees.models import Employee, MedicalSpecialty
from apps.integrations.models import PeopleForceEntity, PeopleForceImportIssue, PeopleForceImportRun
from apps.integrations.peopleforce.client import PeopleForceClient
from apps.integrations.peopleforce.importer import clean, ext_id, payload_hash, trim


class Command(BaseCommand):
    help = "Import PeopleForce skills and employee skill assignments only."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Fetch and count without writing skills or assignments.")
        parser.add_argument("--limit-employees", type=int, default=None, help="Limit employee skill assignment imports.")
        parser.add_argument("--active-only", action="store_true", help="Import assignments only for active HR employees.")

    def handle(self, *args, **options):
        limit = options["limit_employees"]
        if limit is not None and limit < 1:
            raise CommandError("--limit-employees must be greater than zero.")

        counters: dict[str, int] = defaultdict(int)
        run = PeopleForceImportRun.objects.create(
            status=PeopleForceImportRun.Status.RUNNING,
            options={
                "command": "sync_peopleforce_skills",
                "dry_run": options["dry_run"],
                "limit_employees": limit,
                "active_only": options["active_only"],
            },
        )
        try:
            client = PeopleForceClient()
            if options["dry_run"]:
                self._sync(client, run, counters, dry_run=True, limit=limit, active_only=options["active_only"])
            else:
                with transaction.atomic():
                    self._sync(client, run, counters, dry_run=False, limit=limit, active_only=options["active_only"])
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

        self.stdout.write(self.style.SUCCESS(f"PeopleForce skills import run #{run.id}: {run.status}"))
        for key, value in sorted(counters.items()):
            self.stdout.write(f"{key}: {value}")

    def _sync(
        self,
        client: PeopleForceClient,
        run: PeopleForceImportRun,
        counters: dict[str, int],
        *,
        dry_run: bool,
        limit: int | None,
        active_only: bool,
    ) -> None:
        skills = client.list_all("/skills")
        counters["fetched_skills"] = len(skills)
        for payload in skills:
            self._upsert_skill(payload, run, counters, dry_run=dry_run)

        employees = Employee.objects.exclude(legacy_peopleforce_id="").order_by("last_name", "first_name", "id")
        if active_only:
            employees = employees.filter(status=Employee.Status.ACTIVE)
        if limit:
            employees = employees[:limit]

        for employee in employees:
            employee_id = employee.legacy_peopleforce_id
            try:
                rows = client.list_all(f"/employees/{employee_id}/skills")
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in {403, 404}:
                    self._issue(run, "employee_skills", employee_id, f"Optional endpoint unavailable: {exc.response.status_code}", counters)
                    rows = []
                else:
                    raise
            counters["fetched_employee_skill_assignments"] += len(rows)
            self._map_employee_skills(employee, rows, run, counters, dry_run=dry_run)

    def _upsert_skill(
        self,
        payload: dict[str, Any],
        run: PeopleForceImportRun,
        counters: dict[str, int],
        *,
        dry_run: bool,
    ) -> MedicalSpecialty | None:
        name = trim(clean(payload.get("name")), 200)
        external_id = ext_id(payload)
        if not name:
            counters["skills_skipped"] += 1
            return None
        counters["skills_seen"] += 1
        if dry_run:
            return None
        self._store_entity("skills", external_id, "/skills", payload, run)
        skill = MedicalSpecialty.objects.filter(external_peopleforce_id=external_id).first() if external_id else None
        if skill is None:
            skill, created = MedicalSpecialty.objects.get_or_create(
                name=name,
                defaults={"external_peopleforce_id": external_id, "is_active": True},
            )
        else:
            created = False
            skill.name = name
            skill.is_active = True
            skill.save(update_fields=["name", "is_active", "updated_at"])
        if external_id and not skill.external_peopleforce_id:
            skill.external_peopleforce_id = external_id
            skill.save(update_fields=["external_peopleforce_id", "updated_at"])
        counters[f"skills_{'created' if created else 'updated'}"] += 1
        return skill

    def _map_employee_skills(
        self,
        employee: Employee,
        rows: list[dict[str, Any]],
        run: PeopleForceImportRun,
        counters: dict[str, int],
        *,
        dry_run: bool,
    ) -> None:
        if dry_run:
            counters["employees_seen"] += 1
            return

        local_skills = list(employee.medical_specialties.filter(external_peopleforce_id=""))
        peopleforce_skills: list[MedicalSpecialty] = []
        seen_ids: set[int] = set()
        for row in rows:
            skill_payload = row.get("skill") if isinstance(row, dict) else None
            if not isinstance(skill_payload, dict):
                skill_payload = row
            assignment_id = ext_id(row)
            skill_id = ext_id(skill_payload)
            scoped_id = assignment_id or skill_id
            if scoped_id:
                self._store_entity("employee_skills", f"{employee.legacy_peopleforce_id}:{scoped_id}", f"/employees/{employee.legacy_peopleforce_id}/skills", row, run)
            skill = self._upsert_skill(skill_payload, run, counters, dry_run=False)
            if skill and skill.id not in seen_ids:
                peopleforce_skills.append(skill)
                seen_ids.add(skill.id)

        employee.medical_specialties.set([*local_skills, *peopleforce_skills])
        counters["employees_updated"] += 1
        counters["employee_skills_mapped"] += len(peopleforce_skills)

    def _store_entity(self, entity_type: str, external_id: str, endpoint: str, payload: dict[str, Any], run: PeopleForceImportRun) -> None:
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
                "mapping_status": PeopleForceEntity.MappingStatus.MAPPED,
                "hr_model": "employees.MedicalSpecialty" if entity_type == "skills" else "",
            },
        )

    def _issue(self, run: PeopleForceImportRun, entity_type: str, external_id: str, message: str, counters: dict[str, int]) -> None:
        counters["issues"] += 1
        PeopleForceImportIssue.objects.create(
            run=run,
            severity=PeopleForceImportIssue.Severity.WARNING,
            entity_type=entity_type,
            external_id=external_id,
            message=message,
            raw_fragment={},
        )
