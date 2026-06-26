from __future__ import annotations

import hashlib
import json
import posixpath
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone as datetime_timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

import httpx
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.text import slugify

from apps.employees.models import (
    Clinic,
    Department,
    DepartmentLevel,
    Division,
    Employee,
    EmployeeDocument,
    EmployeeDocumentFolder,
    EmployeeEmploymentStatus,
    EmployeePositionHistory,
    EmploymentType,
    ExternalEmployeeLink,
    Gender,
    Holiday,
    HolidayPolicy,
    JobLevel,
    ManagerAssignment,
    MedicalSpecialty,
    Position,
    ProbationPolicy,
    Team,
    TeamMembership,
    TerminationReason,
    TerminationType,
    WorkingPattern,
)
from apps.integrations.models import (
    PeopleForceCompatTimesheetEntry,
    PeopleForceEntity,
    PeopleForceImportIssue,
    PeopleForceImportRun,
)
from apps.integrations.peopleforce.client import PeopleForceClient
from apps.knowledge.models import KnowledgeCategory, KnowledgeDocument
from apps.knowledge.peopleforce_attachments import sync_peopleforce_document_attachments
from apps.leave.models import LeaveApprovalStep, LeaveBalance, LeaveRequest, LeaveType
from apps.skud.models import AttendancePeriod


DEFAULT_CLINIC_CODE = "peopleforce"


@dataclass(frozen=True, slots=True)
class PeopleForceSyncResult:
    run_id: int
    status: str
    counters: dict[str, int]
    issues_count: int


class PeopleForceLegacyImporter:
    def __init__(
        self,
        *,
        dry_run: bool = False,
        from_cache: bool = False,
        limit_employees: int | None = None,
        skip_per_employee: bool = False,
        skip_leave: bool = False,
        skip_knowledge: bool = False,
        skip_documents: bool = False,
        skip_timesheet: bool = False,
        download_document_files: bool = False,
        download_knowledge_attachments: bool = False,
        timesheet_start: date | None = None,
        timesheet_end: date | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.from_cache = from_cache
        self.limit_employees = limit_employees
        self.skip_per_employee = skip_per_employee
        self.skip_leave = skip_leave
        self.skip_knowledge = skip_knowledge
        self.skip_documents = skip_documents
        self.skip_timesheet = skip_timesheet
        self.download_document_files = download_document_files
        self.download_knowledge_attachments = download_knowledge_attachments
        self.timesheet_start = timesheet_start or parse_date(getattr(settings, "PEOPLEFORCE_TIMESHEET_START_DATE", "")) or date(2022, 1, 1)
        self.timesheet_end = timesheet_end or date.today()
        self.client: PeopleForceClient | None = None
        self.now = timezone.now()
        self.default_clinic: Clinic | None = None
        self.counters = defaultdict(int)

    def sync(self) -> PeopleForceSyncResult:
        if not self.from_cache and not settings.PEOPLEFORCE_API_KEY:
            raise ImproperlyConfigured("PEOPLEFORCE_API_KEY is not configured.")
        if not self.from_cache:
            self.client = PeopleForceClient()

        run = PeopleForceImportRun.objects.create(
            status=PeopleForceImportRun.Status.RUNNING,
            options={
                "dry_run": self.dry_run,
                "from_cache": self.from_cache,
                "limit_employees": self.limit_employees,
                "skip_per_employee": self.skip_per_employee,
                "skip_leave": self.skip_leave,
                "skip_knowledge": self.skip_knowledge,
                "skip_documents": self.skip_documents,
                "skip_timesheet": self.skip_timesheet,
                "download_document_files": self.download_document_files,
                "download_knowledge_attachments": self.download_knowledge_attachments,
                "timesheet_start": self.timesheet_start.isoformat(),
                "timesheet_end": self.timesheet_end.isoformat(),
            },
        )
        try:
            if self.dry_run:
                self._run(run)
            else:
                with transaction.atomic():
                    self._run(run)
            run.status = PeopleForceImportRun.Status.DRY_RUN if self.dry_run else PeopleForceImportRun.Status.COMPLETED
            run.finished_at = timezone.now()
            run.counters = dict(self.counters)
            run.save(update_fields=["status", "finished_at", "counters", "updated_at"])
        except Exception as exc:
            run.status = PeopleForceImportRun.Status.FAILED
            run.finished_at = timezone.now()
            run.counters = dict(self.counters)
            run.error_message = str(exc)
            run.save(update_fields=["status", "finished_at", "counters", "error_message", "updated_at"])
            raise

        return PeopleForceSyncResult(
            run_id=run.id,
            status=run.status,
            counters=dict(self.counters),
            issues_count=self.counters["issues"],
        )

    def _run(self, run: PeopleForceImportRun) -> None:
        self.default_clinic = self._default_clinic()
        dictionaries = self._load_dictionaries(run)
        employees = self._load_employees(run)
        self._map_dictionaries(run, dictionaries)
        self._map_employees(run, employees)
        self._resolve_org_links(run, employees, dictionaries)
        if not self.skip_per_employee:
            self._load_and_map_employee_scoped(run, employees)
        if not self.skip_leave:
            self._load_and_map_leave(run)
        if not self.skip_knowledge:
            self._load_and_map_knowledge(run)
        if not self.skip_timesheet:
            self._load_and_map_timesheet(run, employees)

    def _load_dictionaries(self, run: PeopleForceImportRun) -> dict[str, list[dict[str, Any]]]:
        endpoints = {
            "holiday_policies": "/holiday_policies",
            "locations": "/locations",
            "departments": "/departments",
            "divisions": "/divisions",
            "positions": "/positions",
            "job_levels": "/job_levels",
            "employment_types": "/employment_types",
            "probation_policies": "/probation_policies",
            "skills": "/skills",
            "termination_reasons": "/termination_reasons",
            "termination_types": "/termination_types",
            "teams": "/teams",
            "employee_fields": "/employee_fields",
            "employee_tables": "/employee_tables",
            "leave_types": "/leave_types",
            "leave_policies": "/leave_policies",
            "knowledge_categories": "/knowledge_base/categories",
        }
        if not self.skip_documents:
            endpoints["document_folders"] = "/document_folders"
        if not self.skip_per_employee:
            endpoints.update({"job_groups": "/job_groups", "job_profiles": "/job_profiles", "working_patterns": "/working_patterns"})

        data = {}
        for entity_type, endpoint in endpoints.items():
            rows = self._fetch_list(entity_type, endpoint, run)
            data[entity_type] = rows
        return data

    def _load_employees(self, run: PeopleForceImportRun) -> list[dict[str, Any]]:
        rows = self._fetch_list("employees", "/employees", run, params={"status": "all"})
        if self.limit_employees:
            rows = rows[: self.limit_employees]
        detailed = []
        for row in rows:
            external_id = ext_id(row)
            if not external_id:
                continue
            detail = self._fetch_object("employee_detail", f"/employees/{external_id}", run, fallback=row)
            detailed.append(detail)
        return detailed

    def _load_and_map_employee_scoped(self, run: PeopleForceImportRun, employees: list[dict[str, Any]]) -> None:
        for employee_payload in employees:
            employee = self._employee_by_peopleforce_id(ext_id(employee_payload))
            if not employee:
                continue
            employee_id = ext_id(employee_payload)
            positions = self._fetch_list("employee_positions", f"/employees/{employee_id}/positions", run, optional=True)
            self._map_employee_positions(run, employee, positions)
            statuses = self._fetch_list("employee_employment_statuses", f"/employees/{employee_id}/employment_statuses", run, optional=True)
            self._map_employee_statuses(employee, statuses)
            balances = self._fetch_list("employee_leave_balances", f"/employees/{employee_id}/leave_balances", run, optional=True)
            self._map_leave_balances(employee, balances)
            skills = self._fetch_employee_scoped_list("employee_skills", f"/employees/{employee_id}/skills", run, employee_id=employee_id, optional=True)
            self._map_employee_skills(employee, skills)
            self._fetch_list("employee_job_profiles", f"/employees/{employee_id}/job_profiles", run, optional=True)
            self._fetch_list("employee_field_histories", f"/employees/{employee_id}/field_histories", run, optional=True)
            if not self.skip_documents:
                self._load_and_map_employee_documents(run, employee, employee_id)

    def _load_and_map_employee_documents(self, run: PeopleForceImportRun, employee: Employee, employee_id: str) -> None:
        entity_type = "employee_documents"
        if self.from_cache:
            prefix = f"{employee_id}:"
            documents = list(
                PeopleForceEntity.objects.filter(entity_type=entity_type, external_id__startswith=prefix)
                .order_by("external_id")
                .values_list("payload", flat=True)
            )
        else:
            assert self.client is not None
            try:
                documents = self.client.list_all(f"/employees/{employee_id}/documents")
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in {403, 404}:
                    self._issue(run, "warning", entity_type, employee_id, f"Employee documents unavailable: {exc.response.status_code}", {})
                    return
                raise

        self.counters["fetched_employee_documents"] += len(documents)
        for document_payload in documents:
            document_id = ext_id(document_payload)
            if not document_id:
                continue
            external_id = f"{employee_id}:{document_id}"
            detail = document_payload
            if not self.from_cache:
                self._store_entity(run, entity_type, f"/employees/{employee_id}/documents", document_payload, external_id=external_id)
                detail = self._fetch_object(
                    "employee_document_detail",
                    f"/employees/{employee_id}/documents/{document_id}",
                    run,
                    fallback=document_payload,
                    optional=True,
                    external_id=external_id,
                )
            detail = {**document_payload, **(detail or {}), "employee_id": employee_id}
            self._map_employee_document(employee, detail)

    def _load_and_map_leave(self, run: PeopleForceImportRun) -> None:
        leave_requests = self._fetch_list("leave_requests", "/leave_requests", run)
        for payload in leave_requests:
            self._map_leave_request(payload)

    def _load_and_map_timesheet(self, run: PeopleForceImportRun, employees: list[dict[str, Any]]) -> None:
        employee_ids = [ext_id(payload) for payload in employees if ext_id(payload)]
        if self.from_cache:
            known_ids = set(employee_ids)
            for payload in self._entities("timesheet_entries"):
                employee_id = clean(payload.get("employee_id"))
                if employee_id and employee_id not in known_ids:
                    continue
                employee = self._employee_by_peopleforce_id(employee_id)
                if employee:
                    self._map_timesheet_entry(run, employee, payload)
            return

        for employee_id in employee_ids:
            employee = self._employee_by_peopleforce_id(employee_id)
            if not employee:
                continue
            rows = self._fetch_list(
                "timesheet_entries",
                "/time/timesheet_entries",
                run,
                params={
                    "starts_on": self.timesheet_start.isoformat(),
                    "ends_on": self.timesheet_end.isoformat(),
                    "employee_ids[]": employee_id,
                },
                optional=True,
            )
            for payload in rows:
                self._map_timesheet_entry(run, employee, payload)

    def _load_and_map_knowledge(self, run: PeopleForceImportRun) -> None:
        categories = self._entities("knowledge_categories")
        for category_payload in categories:
            category_id = ext_id(category_payload)
            if not category_id:
                continue
            articles = self._fetch_list("knowledge_articles", f"/knowledge_base/categories/{category_id}/articles", run)
            for article in articles:
                article_id = ext_id(article)
                if article_id:
                    detail = self._fetch_object("knowledge_article_detail", f"/knowledge_base/articles/{article_id}", run, fallback=article)
                    self._map_knowledge_article(detail)

    def _fetch_list(
        self,
        entity_type: str,
        endpoint: str,
        run: PeopleForceImportRun,
        params: dict[str, Any] | None = None,
        *,
        optional: bool = False,
    ) -> list[dict[str, Any]]:
        if self.from_cache:
            return self._entities(entity_type)
        assert self.client is not None
        try:
            rows = self.client.list_all(endpoint, params=params)
        except httpx.HTTPStatusError as exc:
            if optional and exc.response.status_code in {403, 404}:
                self._issue(run, "warning", entity_type, "", f"Optional endpoint unavailable: {exc.response.status_code} {endpoint}", {"params": params or {}})
                return []
            raise
        for row in rows:
            self._store_entity(run, entity_type, endpoint, row)
        self.counters[f"fetched_{entity_type}"] += len(rows)
        return rows

    def _fetch_employee_scoped_list(
        self,
        entity_type: str,
        endpoint: str,
        run: PeopleForceImportRun,
        *,
        employee_id: str,
        optional: bool = False,
    ) -> list[dict[str, Any]]:
        if self.from_cache:
            prefix = f"{employee_id}:"
            return list(
                PeopleForceEntity.objects.filter(entity_type=entity_type, external_id__startswith=prefix)
                .order_by("external_id")
                .values_list("payload", flat=True)
            )
        assert self.client is not None
        try:
            rows = self.client.list_all(endpoint)
        except httpx.HTTPStatusError as exc:
            if optional and exc.response.status_code in {403, 404}:
                self._issue(run, "warning", entity_type, employee_id, f"Optional endpoint unavailable: {exc.response.status_code} {endpoint}", {})
                return []
            raise
        for row in rows:
            assignment_id = ext_id(row)
            skill_id = ext_id((row.get("skill") or {}) if isinstance(row, dict) else {})
            scoped_id = assignment_id or skill_id
            if scoped_id:
                self._store_entity(run, entity_type, endpoint, row, external_id=f"{employee_id}:{scoped_id}")
        self.counters[f"fetched_{entity_type}"] += len(rows)
        return rows

    def _fetch_object(
        self,
        entity_type: str,
        endpoint: str,
        run: PeopleForceImportRun,
        fallback: dict[str, Any] | None = None,
        *,
        optional: bool = False,
        external_id: str | None = None,
    ) -> dict[str, Any]:
        external_id = external_id or endpoint.rstrip("/").split("/")[-1]
        if self.from_cache:
            entity = PeopleForceEntity.objects.filter(entity_type=entity_type, external_id=external_id).first()
            return entity.payload if entity else (fallback or {})
        assert self.client is not None
        try:
            payload = self.client.get(endpoint).get("data") or fallback or {}
        except httpx.HTTPStatusError as exc:
            if optional and exc.response.status_code in {403, 404}:
                self._issue(run, "warning", entity_type, external_id, f"Optional object unavailable: {exc.response.status_code} {endpoint}", fallback or {})
                return fallback or {}
            raise
        if isinstance(payload, dict):
            self._store_entity(run, entity_type, endpoint, payload, external_id=external_id)
            return payload
        return fallback or {}

    def _store_entity(
        self,
        run: PeopleForceImportRun,
        entity_type: str,
        endpoint: str,
        payload: dict[str, Any],
        *,
        external_id: str | None = None,
    ) -> None:
        entity_id = external_id or ext_id(payload)
        if not entity_id:
            self._issue(run, "warning", entity_type, "", "PeopleForce entity has no id", payload)
            return
        raw_hash = payload_hash(payload)
        self.counters["raw_seen"] += 1
        if self.dry_run:
            return
        PeopleForceEntity.objects.update_or_create(
            entity_type=entity_type,
            external_id=entity_id,
            defaults={
                "endpoint": endpoint,
                "payload": payload,
                "payload_hash": raw_hash,
                "fetched_at": self.now,
                "last_run": run,
            },
        )

    def _entities(self, entity_type: str) -> list[dict[str, Any]]:
        return list(
            PeopleForceEntity.objects.filter(entity_type=entity_type)
            .order_by("external_id")
            .values_list("payload", flat=True)
        )

    def _map_dictionaries(self, run: PeopleForceImportRun, data: dict[str, list[dict[str, Any]]]) -> None:
        for payload in data.get("holiday_policies", []):
            self._upsert_holiday_policy(payload)
        for payload in data.get("locations", []):
            self._upsert_clinic(payload)
        self.default_clinic = self._default_clinic()
        for payload in data.get("divisions", []):
            self._upsert_named(Division, payload, "divisions")
        for payload in data.get("positions", []):
            self._upsert_named(Position, payload, "positions")
        for payload in data.get("job_levels", []):
            self._upsert_named(JobLevel, payload, "job_levels")
        for payload in data.get("employment_types", []):
            self._upsert_named(EmploymentType, payload, "employment_types")
        for payload in data.get("probation_policies", []):
            self._upsert_probation_policy(payload)
        for payload in data.get("working_patterns", []):
            self._upsert_working_pattern(payload)
        for payload in data.get("skills", []):
            self._upsert_skill(payload)
        for payload in data.get("termination_reasons", []):
            self._upsert_named(TerminationReason, payload, "termination_reasons")
        for payload in data.get("termination_types", []):
            self._upsert_named(TerminationType, payload, "termination_types")
        for payload in data.get("leave_types", []):
            self._upsert_leave_type(payload)
        for payload in data.get("knowledge_categories", []):
            self._upsert_knowledge_category(payload)
        self._sync_knowledge_category_parents()
        for payload in data.get("document_folders", []):
            self._upsert_document_folder(payload)
        for payload in data.get("departments", []):
            self._upsert_department(payload)

    def _map_employees(self, run: PeopleForceImportRun, employees: list[dict[str, Any]]) -> None:
        for payload in employees:
            self._upsert_employee(run, payload)

    def _resolve_org_links(
        self,
        run: PeopleForceImportRun,
        employees: list[dict[str, Any]],
        data: dict[str, list[dict[str, Any]]],
    ) -> None:
        for payload in data.get("departments", []):
            department = self._department_by_peopleforce_id(ext_id(payload))
            if not department:
                continue
            parent_id = clean(payload.get("parent_id"))
            manager_id = clean(payload.get("manager_id"))
            level = self._department_level_by_payload(payload)
            update_fields = []
            if parent_id:
                parent = self._department_by_peopleforce_id(parent_id)
                if parent and department.parent_id != parent.id:
                    department.parent = parent
                    update_fields.append("parent")
            if level and department.level_id != level.id:
                department.level = level
                update_fields.append("level")
            if manager_id:
                manager = self._employee_by_peopleforce_id(manager_id)
                if manager and department.manager_id != manager.id:
                    department.manager = manager
                    update_fields.append("manager")
            if update_fields and not self.dry_run:
                department.save(update_fields=[*update_fields, "updated_at"])
            if manager_id:
                manager = self._employee_by_peopleforce_id(manager_id)
                if manager:
                    self._ensure_department_manager_assignments(department, manager)
                else:
                    self._issue(run, "warning", "department", ext_id(payload), "Department manager was not imported", payload)

        for payload in employees:
            employee = self._employee_by_peopleforce_id(ext_id(payload))
            manager_payload = payload.get("reporting_to") or {}
            manager = self._employee_by_peopleforce_id(ext_id(manager_payload))
            if employee and manager and employee.id != manager.id:
                self._upsert_manager_assignment(employee, manager, parse_date(payload.get("hired_on")))

        for payload in data.get("teams", []):
            self._upsert_team(payload)

    def _upsert_holiday_policy(self, payload: dict[str, Any]) -> HolidayPolicy | None:
        name = trim(clean(payload.get("name")), 180)
        external_id = ext_id(payload)
        if not name:
            return None
        self.counters["holiday_policies_seen"] += 1
        if self.dry_run:
            return None
        policy = HolidayPolicy.objects.filter(external_peopleforce_id=external_id).first() if external_id else None
        if policy is None:
            policy, created = HolidayPolicy.objects.get_or_create(
                name=name,
                defaults={
                    "external_peopleforce_id": external_id,
                    "country_code": trim(clean(payload.get("country_code")), 8),
                    "is_active": True,
                },
            )
        else:
            created = False
            policy.name = name
            policy.country_code = trim(clean(payload.get("country_code")), 8)
            policy.is_active = True
            policy.save(update_fields=["name", "country_code", "is_active", "updated_at"])
        if external_id and not policy.external_peopleforce_id:
            policy.external_peopleforce_id = external_id
            policy.save(update_fields=["external_peopleforce_id", "updated_at"])
        self.counters[f"holiday_policies_{'created' if created else 'updated'}"] += 1
        return policy

    def _upsert_clinic(self, payload: dict[str, Any]) -> Clinic | None:
        name = trim(clean(payload.get("name")), 160)
        external_id = ext_id(payload)
        if not name:
            return None
        code = make_code("pf-", name, external_id, 40)
        holiday_policy_id = trim(clean(payload.get("holiday_policy_id")), 120)
        holiday_policy = self._holiday_policy_by_external_id(holiday_policy_id)
        self.counters["clinics_seen"] += 1
        if self.dry_run:
            return None
        clinic, created = Clinic.objects.update_or_create(
            external_peopleforce_id=external_id,
            defaults={
                "name": name,
                "code": code,
                "country_code": trim(clean(payload.get("country_code")), 8),
                "address": trim(clean(payload.get("address")), 260),
                "holiday_policy_id": holiday_policy_id,
                "holiday_policy_name": holiday_policy.name if holiday_policy else "",
                "holiday_policy_ref": holiday_policy,
                "time_zone": trim(clean(payload.get("time_zone")) or "Kyiv", 80),
                "is_active": True,
            },
        )
        self.counters["clinics_created" if created else "clinics_updated"] += 1
        return clinic

    def _default_clinic(self) -> Clinic | None:
        if self.dry_run:
            return None
        clinic = (
            Clinic.objects.exclude(code=DEFAULT_CLINIC_CODE)
            .filter(is_active=True)
            .annotate(active_employees=Count("employees", filter=Q(employees__status=Employee.Status.ACTIVE)))
            .order_by("-active_employees", "name")
            .first()
        )
        if clinic:
            return clinic
        clinic = Clinic.objects.exclude(code=DEFAULT_CLINIC_CODE).order_by("name").first()
        if clinic:
            return clinic
        clinic, _ = Clinic.objects.get_or_create(
            code=DEFAULT_CLINIC_CODE,
            defaults={"name": "PeopleForce import", "external_peopleforce_id": "", "is_active": True},
        )
        return clinic

    def _upsert_named(self, model, payload: dict[str, Any], counter: str):
        name = trim(clean(payload.get("name")), 180)
        external_id = ext_id(payload)
        if not name:
            return None
        self.counters[f"{counter}_seen"] += 1
        if self.dry_run:
            return None
        obj = model.objects.filter(external_peopleforce_id=external_id).first() if external_id else None
        if obj is None:
            obj, created = model.objects.get_or_create(name=name, defaults={"external_peopleforce_id": external_id, "is_active": True})
        else:
            created = False
            obj.name = name
            obj.is_active = True
            obj.save(update_fields=["name", "is_active", "updated_at"])
        if external_id and not obj.external_peopleforce_id:
            obj.external_peopleforce_id = external_id
            obj.save(update_fields=["external_peopleforce_id", "updated_at"])
        self.counters[f"{counter}_{'created' if created else 'updated'}"] += 1
        return obj

    def _upsert_skill(self, payload: dict[str, Any]) -> MedicalSpecialty | None:
        name = trim(clean(payload.get("name")), 200)
        external_id = ext_id(payload)
        if not name:
            return None
        self.counters["skills_seen"] += 1
        if self.dry_run:
            return None
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
        self.counters[f"skills_{'created' if created else 'updated'}"] += 1
        return skill

    def _upsert_working_pattern(self, payload: dict[str, Any]) -> WorkingPattern | None:
        name = trim(clean(payload.get("name")), 180)
        external_id = ext_id(payload)
        if not name:
            return None
        self.counters["working_patterns_seen"] += 1
        if self.dry_run:
            return None
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
        self.counters[f"working_patterns_{'created' if created else 'updated'}"] += 1
        return working_pattern

    def _upsert_probation_policy(self, payload: dict[str, Any]) -> ProbationPolicy | None:
        name = trim(clean(payload.get("name")), 180)
        external_id = ext_id(payload)
        if not name:
            return None
        self.counters["probation_policies_seen"] += 1
        if self.dry_run:
            return None
        duration_months = int_value(payload.get("length"))
        policy = ProbationPolicy.objects.filter(external_peopleforce_id=external_id).first() if external_id else None
        if policy is None:
            policy, created = ProbationPolicy.objects.get_or_create(
                name=name,
                defaults={
                    "external_peopleforce_id": external_id,
                    "duration_months": duration_months,
                    "is_active": True,
                },
            )
        else:
            created = False
            policy.name = name
            policy.duration_months = duration_months
            policy.is_active = True
            policy.save(update_fields=["name", "duration_months", "is_active", "updated_at"])
        if external_id and not policy.external_peopleforce_id:
            policy.external_peopleforce_id = external_id
            policy.save(update_fields=["external_peopleforce_id", "updated_at"])
        self.counters[f"probation_policies_{'created' if created else 'updated'}"] += 1
        return policy

    def _upsert_department(self, payload: dict[str, Any]) -> Department | None:
        name = trim(clean(payload.get("name")), 160)
        external_id = ext_id(payload)
        if not name:
            return None
        clinic = self.default_clinic or Clinic.objects.filter(external_peopleforce_id__gt="").first()
        if clinic is None:
            return None
        code = make_code("pf-", name, external_id, 60)
        level = self._department_level_by_payload(payload)
        self.counters["departments_seen"] += 1
        if self.dry_run:
            return None
        department = Department.objects.filter(external_peopleforce_id=external_id).first() if external_id else None
        if department is None:
            department, created = Department.objects.get_or_create(
                clinic=clinic,
                name=name,
                defaults={"code": code, "external_peopleforce_id": external_id, "level": level, "is_active": True},
            )
        else:
            created = False
            department.name = name
            department.code = code
            department.clinic = clinic
            department.level = level
            department.is_active = True
            department.save(update_fields=["name", "code", "clinic", "level", "is_active", "updated_at"])
        if external_id and not department.external_peopleforce_id:
            department.external_peopleforce_id = external_id
            department.save(update_fields=["external_peopleforce_id", "updated_at"])
        self.counters[f"departments_{'created' if created else 'updated'}"] += 1
        return department

    def _upsert_department_level(self, payload: dict[str, Any] | None, fallback_id: str = "") -> DepartmentLevel | None:
        if not payload and not fallback_id:
            return None
        external_id = ext_id(payload or {}) or fallback_id
        name = trim(name_of(payload) if payload else "", 160) or (f"Level {external_id}" if external_id else "")
        if not name:
            return None
        self.counters["department_levels_seen"] += 1
        if self.dry_run:
            return None
        level = DepartmentLevel.objects.filter(external_peopleforce_id=external_id).first() if external_id else None
        if level is None:
            level, created = DepartmentLevel.objects.get_or_create(
                name=name,
                defaults={
                    "external_peopleforce_id": external_id,
                    "color": trim(clean((payload or {}).get("color") or (payload or {}).get("hex_color")), 16) or "#94a3b8",
                    "is_active": True,
                },
            )
        else:
            created = False
            level.name = name
            color = trim(clean((payload or {}).get("color") or (payload or {}).get("hex_color")), 16)
            if color:
                level.color = color
            level.is_active = True
            level.save(update_fields=["name", "color", "is_active", "updated_at"])
        if external_id and not level.external_peopleforce_id:
            level.external_peopleforce_id = external_id
            level.save(update_fields=["external_peopleforce_id", "updated_at"])
        self.counters[f"department_levels_{'created' if created else 'updated'}"] += 1
        return level

    def _upsert_leave_type(self, payload: dict[str, Any]) -> LeaveType | None:
        name = trim(clean(payload.get("name")), 120)
        external_id = ext_id(payload)
        if not name:
            return None
        code = make_code("pf-", name, external_id, 40)
        self.counters["leave_types_seen"] += 1
        if self.dry_run:
            return None
        leave_type, created = LeaveType.objects.update_or_create(
            legacy_peopleforce_id=external_id,
            defaults={
                "name": name,
                "code": code,
                "unit": trim(clean(payload.get("unit")), 40),
                "color": trim(clean(payload.get("hex_color")), 40),
                "legacy_payload": payload,
                "is_active": True,
            },
        )
        self.counters[f"leave_types_{'created' if created else 'updated'}"] += 1
        return leave_type

    def _upsert_knowledge_category(self, payload: dict[str, Any]) -> KnowledgeCategory | None:
        name = trim(clean(payload.get("name")), 160)
        external_id = ext_id(payload)
        if not name:
            return None
        slug = unique_slug(KnowledgeCategory, name, external_id)
        parent = None
        parent_id = payload.get("parent_id")
        if parent_id:
            parent = KnowledgeCategory.objects.filter(legacy_peopleforce_id=str(parent_id)).first()
        self.counters["knowledge_categories_seen"] += 1
        if self.dry_run:
            return None
        category, created = KnowledgeCategory.objects.update_or_create(
            legacy_peopleforce_id=external_id,
            defaults={
                "name": name,
                "slug": slug,
                "description": clean(payload.get("description")),
                "icon_emoji": trim(clean(payload.get("emoji")), 16) or "📄",
                "parent": parent,
                "position": int_or_zero(payload.get("position")),
                "legacy_payload": payload,
                "is_active": True,
            },
        )
        self.counters[f"knowledge_categories_{'created' if created else 'updated'}"] += 1
        return category

    def _sync_knowledge_category_parents(self) -> None:
        categories = list(KnowledgeCategory.objects.all())
        by_legacy_id = {category.legacy_peopleforce_id: category for category in categories if category.legacy_peopleforce_id}
        updated = 0
        for category in categories:
            payload = category.legacy_payload or {}
            parent_id = payload.get("parent_id")
            parent = by_legacy_id.get(str(parent_id)) if parent_id else None
            if category.parent_id == (parent.pk if parent else None):
                continue
            category.parent = parent
            category.save(update_fields=["parent"])
            updated += 1
        self.counters["knowledge_category_parents_updated"] += updated

    def _upsert_document_folder(self, payload: dict[str, Any]) -> EmployeeDocumentFolder | None:
        name = trim(clean(payload.get("name")), 180)
        external_id = ext_id(payload)
        if not name:
            return None
        self.counters["document_folders_seen"] += 1
        if self.dry_run:
            return None
        folder, created = EmployeeDocumentFolder.objects.update_or_create(
            legacy_peopleforce_id=external_id,
            defaults={
                "name": name,
                "description": clean(payload.get("description")),
                "legacy_payload": payload,
                "is_active": True,
            },
        )
        self.counters[f"document_folders_{'created' if created else 'updated'}"] += 1
        return folder

    def _upsert_employee(self, run: PeopleForceImportRun, payload: dict[str, Any]) -> Employee | None:
        external_id = ext_id(payload)
        if not external_id:
            return None
        position = self._position_by_payload(payload.get("position"))
        department = self._department_by_payload(payload.get("department"))
        division = self._division_by_payload(payload.get("division"))
        employment_type = self._employment_type_by_payload(payload.get("employment_type"))
        job_level = self._job_level_by_payload(payload.get("job_level"))
        clinic = self._clinic_by_payload(payload.get("location")) or self.default_clinic
        status = clean(payload.get("status"))
        active = payload.get("active")
        dismissed_on = parse_date(payload.get("termination_effective_on"))
        employee_status = Employee.Status.DISMISSED if status == "terminated" or active is False else Employee.Status.ACTIVE
        fields = payload.get("fields") or {}
        gender = trim(gender_value(payload.get("gender")), 40)
        if gender and not self.dry_run:
            self._ensure_gender(gender)
        defaults = {
            "legacy_peopleforce_id": external_id,
            "employee_number": trim(clean(payload.get("employee_number")), 80),
            "first_name": trim(clean(payload.get("first_name")), 120) or trim(clean(payload.get("full_name")), 120) or external_id,
            "last_name": trim(clean(payload.get("last_name")), 120),
            "middle_name": trim(clean(payload.get("middle_name")), 120),
            "email": trim(clean(payload.get("email")), 254),
            "personal_email": trim(clean(payload.get("personal_email")), 254),
            "phone": trim(clean(payload.get("mobile_number")) or peopleforce_field_value(fields, "mobile_number"), 60),
            "phone2": trim(clean(payload.get("work_phone_number")) or peopleforce_field_value(fields, "work_phone_number"), 60),
            "birth_date": parse_date(payload.get("date_of_birth")),
            "gender": gender,
            "avatar_url": trim(peopleforce_avatar_url(payload), 1000),
            "peopleforce_status": trim(status, 40),
            "peopleforce_fields": fields,
            "clinic": clinic,
            "department": department,
            "position": position,
            "division": division,
            "employment_type": employment_type,
            "job_level": job_level,
            "status": employee_status,
            "hired_on": parse_date(payload.get("hired_on")),
            "dismissed_on": dismissed_on,
        }
        self.counters["employees_seen"] += 1
        if self.dry_run:
            return None
        employee = Employee.objects.filter(legacy_peopleforce_id=external_id).first()
        if employee is None and defaults["email"]:
            employee = Employee.objects.filter(email=defaults["email"]).first()
        created = employee is None
        if created:
            employee = Employee.objects.create(**defaults)
        else:
            for field_name, value in defaults.items():
                setattr(employee, field_name, value)
            employee.save(update_fields=[*defaults.keys(), "updated_at"])
        ExternalEmployeeLink.objects.update_or_create(
            source=ExternalEmployeeLink.Source.PEOPLEFORCE_LEGACY,
            external_id=external_id,
            defaults={
                "employee": employee,
                "raw_hash": payload_hash(payload),
                "last_seen_at": self.now,
                "is_active": True,
            },
        )
        self._mark_entity("employee_detail", external_id, employee)
        self.counters[f"employees_{'created' if created else 'updated'}"] += 1
        return employee

    def _ensure_gender(self, value: str) -> Gender | None:
        if not value:
            return None
        labels = {
            "female": "Жінка",
            "male": "Чоловік",
            "woman": "Жінка",
            "man": "Чоловік",
        }
        name = labels.get(value.lower(), value)
        base_name = name
        suffix = 2
        while Gender.objects.filter(name=name).exclude(code=value).exists():
            name = f"{base_name} {suffix}"
            suffix += 1
        gender, _ = Gender.objects.get_or_create(
            code=value,
            defaults={"name": name, "is_active": True},
        )
        return gender

    def _map_employee_skills(self, employee: Employee, skills: list[dict[str, Any]]) -> None:
        if self.dry_run:
            self.counters["employee_skills_seen"] += len(skills)
            return
        current_non_peopleforce = list(employee.medical_specialties.filter(external_peopleforce_id=""))
        peopleforce_skills: list[MedicalSpecialty] = []
        seen_ids: set[int] = set()
        for payload in skills:
            skill_payload = payload.get("skill") if isinstance(payload, dict) else None
            if not isinstance(skill_payload, dict):
                skill_payload = payload
            skill = self._skill_by_payload(skill_payload)
            if skill is None:
                skill = self._upsert_skill(skill_payload)
            if skill and skill.id not in seen_ids:
                peopleforce_skills.append(skill)
                seen_ids.add(skill.id)
        employee.medical_specialties.set([*current_non_peopleforce, *peopleforce_skills])
        self.counters["employee_skills_mapped"] += len(peopleforce_skills)

    def _map_employee_positions(self, run: PeopleForceImportRun, employee: Employee, positions: list[dict[str, Any]]) -> None:
        for payload in positions:
            external_id = ext_id(payload)
            if not external_id:
                continue
            manager = self._employee_by_peopleforce_id(ext_id(payload.get("reporting_to") or {}))
            if self.dry_run:
                self.counters["employee_positions_seen"] += 1
                continue
            history, created = EmployeePositionHistory.objects.update_or_create(
                employee=employee,
                legacy_peopleforce_id=external_id,
                defaults={
                    "effective_on": parse_date(payload.get("effective_on")),
                    "position": self._position_by_payload(payload.get("position")),
                    "clinic": self._clinic_by_payload(payload.get("location")) or self.default_clinic,
                    "department": self._department_by_payload(payload.get("department")),
                    "division": self._division_by_payload(payload.get("division")),
                    "job_level": self._job_level_by_payload(payload.get("job_level")),
                    "manager": manager,
                    "raw_payload": payload,
                },
            )
            if manager and manager.id != employee.id:
                self._upsert_manager_assignment(employee, manager, history.effective_on)
            self.counters[f"employee_positions_{'created' if created else 'updated'}"] += 1

    def _map_employee_statuses(self, employee: Employee, statuses: list[dict[str, Any]]) -> None:
        for payload in statuses:
            external_id = ext_id(payload)
            if not external_id:
                continue
            if self.dry_run:
                self.counters["employee_statuses_seen"] += 1
                continue
            _, created = EmployeeEmploymentStatus.objects.update_or_create(
                employee=employee,
                legacy_peopleforce_id=external_id,
                defaults={
                    "effective_from": parse_date(payload.get("effective_from")),
                    "employment_type": self._employment_type_by_payload(payload.get("employment_type")),
                    "probation_policy": self._probation_policy_by_payload(payload.get("probation_policy")),
                    "working_pattern_name": trim(name_of(payload.get("working_pattern")), 180),
                    "probation_policy_name": trim(name_of(payload.get("probation_policy")), 180),
                    "comment": clean(payload.get("comment")),
                    "raw_payload": payload,
                },
            )
            self.counters[f"employee_statuses_{'created' if created else 'updated'}"] += 1

    def _map_leave_balances(self, employee: Employee, balances: list[dict[str, Any]]) -> None:
        for payload in balances:
            leave_type = self._leave_type_by_payload(payload.get("leave_type"))
            if not leave_type:
                continue
            external_id = ext_id(payload)
            if self.dry_run:
                self.counters["leave_balances_seen"] += 1
                continue
            policy = payload.get("leave_type_policy") or {}
            _, created = LeaveBalance.objects.update_or_create(
                employee=employee,
                leave_type=leave_type,
                legacy_peopleforce_id=external_id,
                defaults={
                    "effective_on": parse_date(payload.get("effective_on")),
                    "balance": decimal_value(payload.get("balance")),
                    "policy_name": trim(clean(policy.get("name")), 180),
                    "policy_activity_type": trim(clean(policy.get("activity_type")), 80),
                    "policy_counted_as": trim(clean(policy.get("counted_as")), 80),
                    "legacy_payload": payload,
                },
            )
            self.counters[f"leave_balances_{'created' if created else 'updated'}"] += 1

    def _map_employee_document(self, employee: Employee, payload: dict[str, Any]) -> EmployeeDocument | None:
        external_id = ext_id(payload)
        if not external_id:
            self.counters["employee_documents_skipped"] += 1
            return None

        name = trim(clean(payload.get("name")) or f"PeopleForce document {external_id}", 240)
        document_type = clean(payload.get("type")) or EmployeeDocument.DocumentType.UNKNOWN
        if document_type not in EmployeeDocument.DocumentType.values:
            document_type = EmployeeDocument.DocumentType.UNKNOWN

        if self.dry_run:
            self.counters["employee_documents_seen"] += 1
            return None

        document, created = EmployeeDocument.objects.update_or_create(
            employee=employee,
            legacy_peopleforce_id=external_id,
            defaults={
                "folder": self._document_folder_by_payload({"id": payload.get("document_folder_id")}),
                "name": name,
                "document_type": document_type,
                "source_url": trim(clean(payload.get("url")), 200),
                "expires_at": parse_dt(payload.get("expires_at")),
                "legacy_payload": payload,
                "file_download_error": "",
            },
        )
        if self.download_document_files and document.document_type == EmployeeDocument.DocumentType.FILE and document.source_url:
            self._download_employee_document_file(document)
        self.counters[f"employee_documents_{'created' if created else 'updated'}"] += 1
        return document

    def _map_timesheet_entry(self, run: PeopleForceImportRun, employee: Employee, payload: dict[str, Any]) -> PeopleForceCompatTimesheetEntry | None:
        external_id = ext_id(payload)
        starts_at = parse_dt(payload.get("starts_at"))
        ends_at = parse_dt(payload.get("ends_at"))
        if not external_id or not starts_at or not ends_at or starts_at >= ends_at:
            self.counters["timesheet_entries_skipped"] += 1
            self._issue(run, "warning", "timesheet_entries", external_id, "Timesheet entry has invalid id or time range", payload)
            return None

        legacy_employee_id = clean(payload.get("employee_id")) or employee.legacy_peopleforce_id
        minutes = int_or_zero(payload.get("minutes")) or int(round((ends_at - starts_at).total_seconds() / 60))
        entry_date = parse_date(payload.get("date")) or starts_at.astimezone(timezone.get_default_timezone()).date()
        comment = clean(payload.get("comment"))
        entry_type = clean(payload.get("type")) or "working"
        status_value = clean(payload.get("status")) or PeopleForceCompatTimesheetEntry.Status.UNSUBMITTED
        if status_value not in PeopleForceCompatTimesheetEntry.Status.values:
            status_value = PeopleForceCompatTimesheetEntry.Status.UNSUBMITTED

        if self.dry_run:
            self.counters["timesheet_entries_seen"] += 1
            return None

        attendance_period = self._upsert_attendance_period(employee, starts_at, ends_at, entry_date, minutes, comment)
        entry = PeopleForceCompatTimesheetEntry.objects.filter(legacy_peopleforce_entry_id=external_id).first()
        if entry is None:
            entry = PeopleForceCompatTimesheetEntry.objects.filter(
                legacy_peopleforce_employee_id=legacy_employee_id,
                starts_at=starts_at,
                ends_at=ends_at,
                deleted_at__isnull=True,
            ).first()

        defaults = {
            "employee": employee,
            "legacy_peopleforce_entry_id": external_id,
            "legacy_peopleforce_employee_id": legacy_employee_id,
            "attendance_period": attendance_period,
            "starts_at": starts_at,
            "ends_at": ends_at,
            "date": entry_date,
            "minutes": max(0, minutes),
            "status": status_value,
            "entry_type": entry_type,
            "comment": comment,
            "raw_payload": payload,
            "deleted_at": None,
        }
        created = entry is None
        if created:
            entry = PeopleForceCompatTimesheetEntry.objects.create(**defaults)
        else:
            for field_name, value in defaults.items():
                setattr(entry, field_name, value)
            entry.save(update_fields=[*defaults.keys(), "updated_at"])
        self._mark_entity("timesheet_entries", external_id, entry)
        self.counters[f"timesheet_entries_{'created' if created else 'updated'}"] += 1
        return entry

    def _upsert_attendance_period(
        self,
        employee: Employee,
        starts_at: datetime,
        ends_at: datetime,
        entry_date: date,
        minutes: int,
        comment: str,
    ) -> AttendancePeriod:
        period = AttendancePeriod.objects.filter(
            employee=employee,
            start_at=starts_at,
            end_at=ends_at,
        ).first()
        period_type = AttendancePeriod.PeriodType.MANUAL if comment else AttendancePeriod.PeriodType.REGULAR
        defaults = {
            "date": entry_date,
            "duration_minutes": max(0, minutes),
            "period_type": period_type,
            "comment": comment,
        }
        if period is None:
            return AttendancePeriod.objects.create(
                employee=employee,
                start_at=starts_at,
                end_at=ends_at,
                **defaults,
            )
        for field_name, value in defaults.items():
            setattr(period, field_name, value)
        period.save(update_fields=[*defaults.keys(), "updated_at"])
        return period

    def _download_employee_document_file(self, document: EmployeeDocument) -> None:
        if document.local_file:
            return
        try:
            with httpx.Client(timeout=getattr(settings, "PEOPLEFORCE_DOCUMENT_DOWNLOAD_TIMEOUT_SECONDS", 30)) as client:
                response = client.get(document.source_url)
                response.raise_for_status()
            document.local_file.save(employee_document_filename(document), ContentFile(response.content), save=False)
            document.file_downloaded_at = timezone.now()
            document.file_download_error = ""
        except Exception as exc:
            document.file_download_error = trim(str(exc), 1000)
        document.save(update_fields=["local_file", "file_downloaded_at", "file_download_error", "updated_at"])

    def _map_leave_request(self, payload: dict[str, Any]) -> LeaveRequest | None:
        employee = self._employee_by_peopleforce_id(clean(payload.get("employee_id")))
        leave_type = self._leave_type_by_payload({"id": payload.get("leave_type_id"), "name": payload.get("leave_type")})
        external_id = ext_id(payload)
        if not employee or not leave_type or not external_id:
            self.counters["leave_requests_skipped"] += 1
            return None
        if self.dry_run:
            self.counters["leave_requests_seen"] += 1
            return None
        request, created = LeaveRequest.objects.update_or_create(
            legacy_peopleforce_id=external_id,
            defaults={
                "employee": employee,
                "leave_type": leave_type,
                "date_from": parse_date(payload.get("starts_on")) or date.today(),
                "date_to": parse_date(payload.get("ends_on")) or parse_date(payload.get("starts_on")) or date.today(),
                "reason": clean(payload.get("comment")),
                "amount": decimal_value(payload.get("amount")),
                "tracking_time_in": trim(clean(payload.get("tracking_time_in")), 20),
                "status": map_leave_state(payload.get("state")),
                "legacy_payload": payload,
            },
        )
        LeaveApprovalStep.objects.filter(leave_request=request).delete()
        for order, approval in enumerate(payload.get("approvals") or [], start=1):
            assigned_to = approval.get("assigned_to") or {}
            approver_employee = self._employee_by_peopleforce_id(ext_id(assigned_to))
            if approver_employee and approver_employee.user_id:
                LeaveApprovalStep.objects.create(
                    leave_request=request,
                    approver=approver_employee.user,
                    order=order,
                    status=map_approval_state(approval.get("state")),
                )
        self.counters[f"leave_requests_{'created' if created else 'updated'}"] += 1
        return request

    def _map_knowledge_article(self, payload: dict[str, Any]) -> KnowledgeDocument | None:
        category = self._knowledge_category_by_payload(payload.get("category"))
        external_id = ext_id(payload)
        title = trim(clean(payload.get("title")), 240)
        if not category or not external_id or not title:
            self.counters["knowledge_articles_skipped"] += 1
            return None
        existing_document = KnowledgeDocument.objects.filter(legacy_peopleforce_id=external_id).first()
        if existing_document and (existing_document.legacy_payload or {}).get("hr_local_edit"):
            legacy_payload = dict(existing_document.legacy_payload or {})
            legacy_payload["peopleforce_latest"] = payload
            existing_document.legacy_payload = legacy_payload
            existing_document.save(update_fields=["legacy_payload"])
            if self.download_knowledge_attachments:
                result = sync_peopleforce_document_attachments(existing_document)
                self.counters["knowledge_attachments_downloaded"] += result.downloaded
                self.counters["knowledge_attachments_reused"] += result.reused
                self.counters["knowledge_attachments_failed"] += result.failed
                self.counters["knowledge_attachment_links_rewritten"] += result.rewritten
            self.counters["knowledge_articles_preserved_local_edit"] += 1
            return existing_document
        slug = unique_slug(KnowledgeDocument, title, external_id)
        if self.dry_run:
            self.counters["knowledge_articles_seen"] += 1
            return None
        document, created = KnowledgeDocument.objects.update_or_create(
            legacy_peopleforce_id=external_id,
            defaults={
                "category": category,
                "title": title,
                "slug": slug,
                "summary": "",
                "body": clean(payload.get("body")),
                "body_html": clean(payload.get("body_html")),
                "status": KnowledgeDocument.Status.PUBLISHED,
                "legacy_payload": payload,
            },
        )
        if self.download_knowledge_attachments:
            result = sync_peopleforce_document_attachments(document)
            self.counters["knowledge_attachments_downloaded"] += result.downloaded
            self.counters["knowledge_attachments_reused"] += result.reused
            self.counters["knowledge_attachments_failed"] += result.failed
            self.counters["knowledge_attachment_links_rewritten"] += result.rewritten
        self.counters[f"knowledge_articles_{'created' if created else 'updated'}"] += 1
        return document

    def _upsert_team(self, payload: dict[str, Any]) -> Team | None:
        name = trim(clean(payload.get("name")), 180)
        external_id = ext_id(payload)
        if not name:
            return None
        lead = self._employee_by_peopleforce_id(ext_id(payload.get("team_lead") or {}))
        if self.dry_run:
            self.counters["teams_seen"] += 1
            return None
        team, created = Team.objects.update_or_create(
            external_peopleforce_id=external_id,
            defaults={"name": name, "description": clean(payload.get("description")), "lead": lead, "is_active": True},
        )
        TeamMembership.objects.filter(team=team).update(is_active=False)
        for member in payload.get("team_members") or []:
            employee = self._employee_by_peopleforce_id(ext_id(member.get("user") or member))
            if employee:
                TeamMembership.objects.update_or_create(
                    team=team,
                    employee=employee,
                    defaults={"external_peopleforce_id": ext_id(member), "is_active": True},
                )
        self.counters[f"teams_{'created' if created else 'updated'}"] += 1
        return team

    def _ensure_department_manager_assignments(self, department: Department, manager: Employee) -> None:
        for employee in Employee.objects.filter(department=department, status=Employee.Status.ACTIVE).exclude(pk=manager.pk):
            self._upsert_manager_assignment(employee, manager, employee.hired_on)

    def _upsert_manager_assignment(self, employee: Employee, manager: Employee, valid_from: date | None) -> None:
        if self.dry_run:
            self.counters["manager_assignments_seen"] += 1
            return
        _, created = ManagerAssignment.objects.update_or_create(
            employee=employee,
            manager=manager,
            valid_from=valid_from or employee.hired_on or date.today(),
            defaults={"is_primary": True},
        )
        self.counters[f"manager_assignments_{'created' if created else 'updated'}"] += 1

    def _mark_entity(self, entity_type: str, external_id: str, obj) -> None:
        PeopleForceEntity.objects.filter(entity_type=entity_type, external_id=external_id).update(
            mapping_status=PeopleForceEntity.MappingStatus.MAPPED,
            hr_model=f"{obj._meta.app_label}.{obj._meta.model_name}",
            hr_object_id=str(obj.pk),
        )

    def _issue(self, run: PeopleForceImportRun, severity: str, entity_type: str, external_id: str, message: str, raw_fragment: dict[str, Any]) -> None:
        self.counters["issues"] += 1
        if self.dry_run:
            return
        PeopleForceImportIssue.objects.create(
            run=run,
            severity=severity,
            entity_type=entity_type,
            external_id=trim(external_id, 160),
            message=trim(message, 500),
            raw_fragment=raw_fragment,
        )

    def _employee_by_peopleforce_id(self, external_id: str) -> Employee | None:
        if not external_id:
            return None
        return Employee.objects.filter(legacy_peopleforce_id=external_id).first()

    def _department_by_peopleforce_id(self, external_id: str) -> Department | None:
        if not external_id:
            return None
        return Department.objects.filter(external_peopleforce_id=external_id).first()

    def _department_by_payload(self, payload: Any) -> Department | None:
        return self._department_by_peopleforce_id(ext_id(payload))

    def _department_level_by_payload(self, payload: Any) -> DepartmentLevel | None:
        if not isinstance(payload, dict):
            return None
        level_payload = payload.get("department_level")
        fallback_id = clean(payload.get("department_level_id"))
        if isinstance(level_payload, dict) or fallback_id:
            return self._upsert_department_level(level_payload if isinstance(level_payload, dict) else None, fallback_id=fallback_id)
        return None

    def _position_by_payload(self, payload: Any) -> Position | None:
        return Position.objects.filter(external_peopleforce_id=ext_id(payload)).first() if ext_id(payload) else None

    def _division_by_payload(self, payload: Any) -> Division | None:
        return Division.objects.filter(external_peopleforce_id=ext_id(payload)).first() if ext_id(payload) else None

    def _employment_type_by_payload(self, payload: Any) -> EmploymentType | None:
        return EmploymentType.objects.filter(external_peopleforce_id=ext_id(payload)).first() if ext_id(payload) else None

    def _job_level_by_payload(self, payload: Any) -> JobLevel | None:
        return JobLevel.objects.filter(external_peopleforce_id=ext_id(payload)).first() if ext_id(payload) else None

    def _skill_by_payload(self, payload: Any) -> MedicalSpecialty | None:
        external_id = ext_id(payload)
        if external_id:
            return MedicalSpecialty.objects.filter(external_peopleforce_id=external_id).first()
        name = name_of(payload)
        if name:
            return MedicalSpecialty.objects.filter(name=name).first()
        return None

    def _probation_policy_by_payload(self, payload: Any) -> ProbationPolicy | None:
        external_id = ext_id(payload)
        if external_id:
            found = ProbationPolicy.objects.filter(external_peopleforce_id=external_id).first()
            if found:
                return found
        name = name_of(payload)
        if name:
            return ProbationPolicy.objects.filter(name=name).first()
        return None

    def _holiday_policy_by_external_id(self, external_id: str) -> HolidayPolicy | None:
        if not external_id:
            return None
        return HolidayPolicy.objects.filter(external_peopleforce_id=external_id).first()

    def _clinic_by_payload(self, payload: Any) -> Clinic | None:
        return Clinic.objects.filter(external_peopleforce_id=ext_id(payload)).first() if ext_id(payload) else None

    def _leave_type_by_payload(self, payload: Any) -> LeaveType | None:
        external_id = ext_id(payload)
        if external_id:
            found = LeaveType.objects.filter(legacy_peopleforce_id=external_id).first()
            if found:
                return found
        name = name_of(payload)
        if name:
            return LeaveType.objects.filter(name=name).first()
        return None

    def _knowledge_category_by_payload(self, payload: Any) -> KnowledgeCategory | None:
        external_id = ext_id(payload)
        if external_id:
            return KnowledgeCategory.objects.filter(legacy_peopleforce_id=external_id).first()
        return None

    def _document_folder_by_payload(self, payload: Any) -> EmployeeDocumentFolder | None:
        external_id = ext_id(payload)
        if external_id:
            return EmployeeDocumentFolder.objects.filter(legacy_peopleforce_id=external_id).first()
        return None


def ext_id(payload: Any) -> str:
    if isinstance(payload, dict):
        value = payload.get("id")
    else:
        value = payload
    return clean(value)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def trim(value: str, max_length: int) -> str:
    return value[:max_length]


def peopleforce_field_value(fields: dict[str, Any], key: str) -> str:
    field = fields.get(key)
    if isinstance(field, dict):
        return clean(field.get("value"))
    return clean(field)


def peopleforce_avatar_url(payload: dict[str, Any]) -> str:
    for key in ("avatar_url", "photo_url", "image_url", "picture_url"):
        url = clean(payload.get(key))
        if url:
            return url
    for key in ("avatar", "photo", "image", "picture"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if not isinstance(value, dict):
            continue
        for nested_key in ("url", "thumb_url", "thumbnail_url", "medium_url", "large_url", "original_url"):
            url = clean(value.get(nested_key))
            if url:
                return url
    return ""


def name_of(payload: Any) -> str:
    if isinstance(payload, dict):
        return clean(payload.get("name") or payload.get("full_name"))
    return clean(payload)


def gender_value(payload: Any) -> str:
    if isinstance(payload, dict):
        return clean(payload.get("name") or payload.get("id"))
    return clean(payload)


def parse_date(value: Any) -> date | None:
    text = clean(value)
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def parse_dt(value: Any) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    parsed = parse_datetime(text)
    if parsed is None and text.isdigit():
        try:
            parsed = datetime.fromtimestamp(float(text), tz=datetime_timezone.utc)
        except (OverflowError, ValueError):
            return None
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_default_timezone())
    return parsed


def decimal_value(value: Any) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def int_value(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


WORKING_PATTERN_DAYS = (
    ("monday", "Понеділок"),
    ("tuesday", "Вівторок"),
    ("wednesday", "Середа"),
    ("thursday", "Четвер"),
    ("friday", "П'ятниця"),
    ("saturday", "Субота"),
    ("sunday", "Неділя"),
)


def bool_value(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    text = clean(value).lower()
    if not text:
        return default
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def working_pattern_schedule(payload: dict[str, Any]) -> dict[str, Any]:
    days = []
    for key, label in WORKING_PATTERN_DAYS:
        hours = decimal_value(payload.get(f"{key}_hours"))
        days.append(
            {
                "key": key,
                "label": label,
                "time_range": "",
                "break_hours": 0,
                "hours": float(hours),
            }
        )
    return {
        "source": "peopleforce",
        "days": days,
        "raw": payload,
    }


def working_pattern_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        f"{key}_hours": decimal_value(payload.get(f"{key}_hours"))
        for key, _label in WORKING_PATTERN_DAYS
    }
    name = clean(payload.get("name")).lower()
    is_default = bool_value(payload.get("default") if "default" in payload else payload.get("is_default"))
    if name in {"за замовчуванням", "default"}:
        is_default = True
    defaults.update(
        {
            "uses_time_range": bool_value(payload.get("uses_time_range"), default=True),
            "is_default": is_default,
            "schedule": working_pattern_schedule(payload),
            "is_active": bool_value(payload.get("active") if "active" in payload else payload.get("is_active"), default=True),
        }
    )
    return defaults


def int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def payload_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def unique_slug(model, label: str, external_id: str) -> str:
    base = slugify(label) or "peopleforce"
    suffix = external_id or hashlib.sha1(label.encode("utf-8")).hexdigest()[:8]
    slug = trim(f"{base}-{suffix}", 250)
    return slug


def make_code(prefix: str, label: str, external_id: str, max_length: int) -> str:
    ident = re.sub(r"[^0-9a-zA-Z]+", "", external_id)[:8]
    slug = re.sub(r"[^0-9a-zA-Z]+", "-", slugify(label) or label.lower()).strip("-")
    body = slug or ident or "unknown"
    if ident and ident not in body:
        body = f"{body}-{ident}"
    code = f"{prefix}{body}"
    if len(code) <= max_length:
        return code
    if ident:
        keep = max_length - len(prefix) - len(ident) - 1
        return f"{prefix}{body[:keep].strip('-')}-{ident}"
    return code[:max_length].rstrip("-")


def employee_document_filename(document: EmployeeDocument) -> str:
    parsed_path = posixpath.basename(urlparse(document.source_url).path)
    raw_name = parsed_path or document.name or f"peopleforce-document-{document.legacy_peopleforce_id}"
    raw_name = raw_name.split("?")[0].split("#")[0]
    if "." in raw_name:
        stem, extension = raw_name.rsplit(".", 1)
        extension = f".{re.sub(r'[^0-9A-Za-z]+', '', extension)[:12]}"
    else:
        stem, extension = raw_name, ""
    safe_stem = slugify(stem) or f"peopleforce-document-{document.legacy_peopleforce_id}"
    safe_id = re.sub(r"[^0-9A-Za-z_-]+", "-", document.legacy_peopleforce_id)[:80]
    return f"{document.employee_id}-{safe_id}-{safe_stem[:120]}{extension}"


def map_leave_state(state: Any) -> str:
    value = clean(state)
    return {
        "pending": LeaveRequest.Status.SUBMITTED,
        "approved": LeaveRequest.Status.APPROVED,
        "rejected": LeaveRequest.Status.REJECTED,
        "withdrawn": LeaveRequest.Status.CANCELLED,
    }.get(value, LeaveRequest.Status.DRAFT)


def map_approval_state(state: Any) -> str:
    value = clean(state)
    return {
        "pending": LeaveApprovalStep.Status.PENDING,
        "approved": LeaveApprovalStep.Status.APPROVED,
        "rejected": LeaveApprovalStep.Status.REJECTED,
        "skipped": LeaveApprovalStep.Status.SKIPPED,
    }.get(value, LeaveApprovalStep.Status.PENDING)
