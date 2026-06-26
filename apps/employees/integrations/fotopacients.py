from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.db import connections, transaction
from django.utils import timezone

from apps.employees.models import (
    Clinic,
    Department,
    Employee,
    EmployeeImportIssue,
    EmployeeImportRun,
    ExternalEmployeeLink,
    MedicalSpecialty,
    Position,
)


ROLE_POSITION_NAMES = {
    "admin": "Адміністратор FotoPacients",
    "senior_doctor": "Старший лікар",
    "doctor": "Лікар",
    "assistant": "Асистент",
    "staff": "Співробітник",
}
DOCTOR_ROLES = {"doctor", "senior_doctor"}


@dataclass(slots=True)
class FotoPacientsEmployeeRecord:
    payload: dict[str, Any]
    departments: list[dict[str, Any]] = field(default_factory=list)
    specialties: list[dict[str, Any]] = field(default_factory=list)

    @property
    def external_id(self) -> str:
        return clean_text(self.payload.get("external_id"))


@dataclass(frozen=True, slots=True)
class FotoPacientsSyncResult:
    run_id: int
    status: str
    counters: dict[str, int]
    issues_count: int


def sync_fotopacients_employees(
    *,
    database: str = "fotopacients",
    dry_run: bool = False,
    include_inactive: bool = False,
    limit: int | None = None,
) -> FotoPacientsSyncResult:
    service = FotoPacientsEmployeeSync(
        database=database,
        dry_run=dry_run,
        include_inactive=include_inactive,
        limit=limit,
    )
    return service.sync()


class FotoPacientsEmployeeSync:
    def __init__(
        self,
        *,
        database: str,
        dry_run: bool,
        include_inactive: bool,
        limit: int | None,
    ) -> None:
        self.database = database
        self.dry_run = dry_run
        self.include_inactive = include_inactive
        self.limit = limit
        self.counters = {
            "read": 0,
            "created": 0,
            "updated": 0,
            "would_create": 0,
            "would_update": 0,
            "skipped": 0,
            "failed": 0,
            "issues": 0,
            "clinics_created": 0,
            "departments_created": 0,
            "positions_created": 0,
            "specialties_created": 0,
        }

    def sync(self) -> FotoPacientsSyncResult:
        self._check_database_configured()
        run = EmployeeImportRun.objects.create(
            source=EmployeeImportRun.Source.FOTOPACIENTS,
            status=EmployeeImportRun.Status.RUNNING,
            counters=self.counters,
        )

        try:
            records = self._fetch_records()
            self.counters["read"] = len(records)

            for record in records:
                try:
                    if self.dry_run:
                        self._inspect_record(run, record)
                    else:
                        with transaction.atomic():
                            self._upsert_record(run, record)
                except Exception as exc:  # noqa: BLE001 - import must continue per employee.
                    self.counters["failed"] += 1
                    self._add_issue(
                        run,
                        EmployeeImportIssue.Severity.ERROR,
                        record.external_id,
                        f"Не вдалося імпортувати співробітника: {exc}",
                        {"employee": record.payload},
                    )

            run.status = (
                EmployeeImportRun.Status.DRY_RUN
                if self.dry_run
                else EmployeeImportRun.Status.COMPLETED
            )
            run.finished_at = timezone.now()
            run.counters = self.counters
            run.save(update_fields=["status", "finished_at", "counters", "updated_at"])
        except Exception as exc:
            run.status = EmployeeImportRun.Status.FAILED
            run.finished_at = timezone.now()
            run.error_message = str(exc)
            run.counters = self.counters
            run.save(update_fields=["status", "finished_at", "error_message", "counters", "updated_at"])
            raise

        return FotoPacientsSyncResult(
            run_id=run.id,
            status=run.status,
            counters=dict(self.counters),
            issues_count=self.counters["issues"],
        )

    def _check_database_configured(self) -> None:
        if self.database not in connections.databases:
            raise ImproperlyConfigured(
                f"Database alias '{self.database}' is not configured. "
                "Set FOTOPACIENTS_DB_ENABLED=1 and FOTOPACIENTS_DB_* env vars."
            )

    def _fetch_records(self) -> list[FotoPacientsEmployeeRecord]:
        staff_rows = self._fetch_staff_rows()
        if self.limit is not None:
            staff_rows = staff_rows[: self.limit]

        department_rows = self._fetch_department_rows()
        specialty_rows = self._fetch_specialty_rows()

        departments_by_user: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in department_rows:
            departments_by_user[clean_text(row.get("user_id"))].append(row)

        specialties_by_user: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in specialty_rows:
            specialties_by_user[clean_text(row.get("user_id"))].append(row)

        records = []
        for row in staff_rows:
            external_id = clean_text(row.get("external_id"))
            records.append(
                FotoPacientsEmployeeRecord(
                    payload=row,
                    departments=departments_by_user.get(external_id, []),
                    specialties=specialties_by_user.get(external_id, []),
                )
            )
        return records

    def _fetch_staff_rows(self) -> list[dict[str, Any]]:
        sql = """
            SELECT
                u.id::text AS external_id,
                u.username,
                u.first_name,
                u.last_name,
                u.middle_name,
                u.email,
                u.phone,
                u.phone2,
                u.role,
                u.specialty,
                u.baf_id,
                u.is_active,
                u.is_deleted,
                COALESCE(d_baf.is_deleted_in_baf, FALSE) AS doctor_is_deleted_in_baf,
                u.clinic_id::text AS clinic_id,
                c.name AS clinic_name,
                c.slug AS clinic_slug
            FROM accounts_user u
            LEFT JOIN patients_clinic c ON c.id = u.clinic_id
            LEFT JOIN patients_doctor d_baf ON d_baf.id::text = u.baf_id
            WHERE (
                %s
                OR (
                    u.is_active = TRUE
                    AND COALESCE(u.is_deleted, FALSE) = FALSE
                    AND COALESCE(d_baf.is_deleted_in_baf, FALSE) = FALSE
                )
            )
            ORDER BY u.last_name, u.first_name, u.username
        """
        with connections[self.database].cursor() as cursor:
            cursor.execute(sql, [self.include_inactive])
            return dict_rows(cursor)

    def _fetch_department_rows(self) -> list[dict[str, Any]]:
        sql = """
            SELECT
                ud.user_id::text AS user_id,
                d.id::text AS department_id,
                d.name AS department_name,
                d.slug AS department_slug,
                d.clinic_id::text AS clinic_id,
                c.name AS clinic_name,
                c.slug AS clinic_slug
            FROM accounts_user_departments ud
            INNER JOIN patients_department d ON d.id = ud.department_id
            LEFT JOIN patients_clinic c ON c.id = d.clinic_id
            WHERE (
                %s
                OR (
                    COALESCE(d.is_deleted, FALSE) = FALSE
                    AND COALESCE(d.is_deleted_in_baf, FALSE) = FALSE
                )
            )
            ORDER BY d.name
        """
        with connections[self.database].cursor() as cursor:
            cursor.execute(sql, [self.include_inactive])
            return dict_rows(cursor)

    def _fetch_specialty_rows(self) -> list[dict[str, Any]]:
        sql = """
            SELECT
                u.id::text AS user_id,
                s.id::text AS specialty_id,
                s.name AS specialty_name
            FROM accounts_user u
            INNER JOIN patients_doctor d ON d.id::text = u.baf_id
            INNER JOIN patients_doctor_specialties ds ON ds.doctor_id = d.id
            INNER JOIN patients_specialty s ON s.id = ds.specialty_id
            WHERE (
                %s
                OR (
                    COALESCE(s.is_deleted, FALSE) = FALSE
                    AND COALESCE(s.is_deleted_in_baf, FALSE) = FALSE
                )
            )
            ORDER BY s.name
        """
        with connections[self.database].cursor() as cursor:
            cursor.execute(sql, [self.include_inactive])
            return dict_rows(cursor)

    def _inspect_record(self, run: EmployeeImportRun, record: FotoPacientsEmployeeRecord) -> None:
        employee, _link = self._find_employee(record)
        if employee:
            self.counters["would_update"] += 1
        else:
            self.counters["would_create"] += 1
        self._warn_about_record_shape(run, record)

    def _upsert_record(self, run: EmployeeImportRun, record: FotoPacientsEmployeeRecord) -> None:
        self._warn_about_record_shape(run, record)

        employee, link = self._find_employee(record)
        clinic_data = self._primary_clinic_data(record)
        department_data = self._primary_department_data(record)
        clinic = self._upsert_clinic(clinic_data) if clinic_data else None
        department = self._upsert_department(department_data, clinic) if department_data and clinic else None
        position = self._upsert_position(record.payload)
        defaults = self._employee_defaults(record, clinic, department, position)

        created = employee is None
        if created:
            employee = Employee.objects.create(**defaults)
            self.counters["created"] += 1
        else:
            changed_fields = []
            for field_name, value in defaults.items():
                if getattr(employee, field_name) != value:
                    setattr(employee, field_name, value)
                    changed_fields.append(field_name)
            if changed_fields:
                employee.save(update_fields=[*changed_fields, "updated_at"])
            self.counters["updated"] += 1

        specialty_items = self._specialty_items(record)
        if specialty_items or clean_text(record.payload.get("role")) in DOCTOR_ROLES:
            employee.medical_specialties.set(self._upsert_specialties(specialty_items))

        if link is None:
            link = ExternalEmployeeLink(
                source=ExternalEmployeeLink.Source.FOTOPACIENTS,
                external_id=record.external_id,
                employee=employee,
            )
        link.employee = employee
        link.raw_hash = self._raw_hash(record)
        link.last_seen_at = timezone.now()
        link.is_active = True
        link.save()

    def _find_employee(
        self,
        record: FotoPacientsEmployeeRecord,
    ) -> tuple[Employee | None, ExternalEmployeeLink | None]:
        external_id = record.external_id
        link = (
            ExternalEmployeeLink.objects.select_related("employee")
            .filter(source=ExternalEmployeeLink.Source.FOTOPACIENTS, external_id=external_id)
            .first()
        )
        if link:
            return link.employee, link

        employee = Employee.objects.filter(external_fotopacients_id=external_id).first()
        if employee:
            return employee, None

        baf_id = clean_text(record.payload.get("baf_id"))
        if baf_id:
            employee = Employee.objects.filter(external_baf_id=baf_id).first()
            if employee:
                return employee, None

        return None, None

    def _employee_defaults(
        self,
        record: FotoPacientsEmployeeRecord,
        clinic: Clinic | None,
        department: Department | None,
        position: Position,
    ) -> dict[str, Any]:
        row = record.payload
        first_name = trim(clean_text(row.get("first_name")), 120)
        last_name = trim(clean_text(row.get("last_name")), 120)
        username = clean_text(row.get("username"))
        if not first_name and not last_name:
            first_name = trim(username or record.external_id[:8], 120)

        is_active = (
            bool(row.get("is_active"))
            and not bool(row.get("is_deleted"))
            and not bool(row.get("doctor_is_deleted_in_baf"))
        )
        return {
            "external_fotopacients_id": record.external_id,
            "external_baf_id": trim(clean_text(row.get("baf_id")), 120),
            "first_name": first_name,
            "last_name": last_name,
            "middle_name": trim(clean_text(row.get("middle_name")), 120),
            "email": trim(clean_text(row.get("email")), 254),
            "phone": trim(clean_text(row.get("phone")), 60),
            "phone2": trim(clean_text(row.get("phone2")), 60),
            "clinic": clinic,
            "department": department,
            "position": position,
            "status": Employee.Status.ACTIVE if is_active else Employee.Status.DISMISSED,
        }

    def _warn_about_record_shape(self, run: EmployeeImportRun, record: FotoPacientsEmployeeRecord) -> None:
        if len(record.departments) > 1:
            self._add_issue(
                run,
                EmployeeImportIssue.Severity.WARNING,
                record.external_id,
                "У FotoPacients вказано кілька департаментів; у HR записано перший як основний.",
                {
                    "departments": [
                        clean_text(item.get("department_name")) for item in record.departments
                    ],
                },
            )

    def _primary_clinic_data(self, record: FotoPacientsEmployeeRecord) -> dict[str, Any] | None:
        row = record.payload
        if clean_text(row.get("clinic_id")) or clean_text(row.get("clinic_name")):
            return {
                "clinic_id": row.get("clinic_id"),
                "clinic_name": row.get("clinic_name"),
                "clinic_slug": row.get("clinic_slug"),
            }
        if record.departments:
            department = record.departments[0]
            return {
                "clinic_id": department.get("clinic_id"),
                "clinic_name": department.get("clinic_name"),
                "clinic_slug": department.get("clinic_slug"),
            }
        return None

    def _primary_department_data(self, record: FotoPacientsEmployeeRecord) -> dict[str, Any] | None:
        if not record.departments:
            return None
        return record.departments[0]

    def _upsert_clinic(self, data: dict[str, Any]) -> Clinic | None:
        external_id = clean_text(data.get("clinic_id"))
        name = trim(clean_text(data.get("clinic_name")) or clean_text(data.get("clinic_slug")) or external_id, 160)
        if not name:
            return None
        code = make_code("fp-", clean_text(data.get("clinic_slug")) or name, external_id, 40)
        clinic, created = Clinic.objects.get_or_create(code=code, defaults={"name": name, "is_active": True})
        if created:
            self.counters["clinics_created"] += 1
        elif clinic.name != name or not clinic.is_active:
            clinic.name = name
            clinic.is_active = True
            clinic.save(update_fields=["name", "is_active", "updated_at"])
        return clinic

    def _upsert_department(self, data: dict[str, Any], clinic: Clinic) -> Department | None:
        external_id = clean_text(data.get("department_id"))
        name = trim(clean_text(data.get("department_name")) or clean_text(data.get("department_slug")) or external_id, 160)
        if not name:
            return None
        code = make_code("fp-", clean_text(data.get("department_slug")) or name, external_id, 60)
        department, created = Department.objects.get_or_create(
            clinic=clinic,
            name=name,
            defaults={"code": code, "is_active": True},
        )
        if created:
            self.counters["departments_created"] += 1
        else:
            changed_fields = []
            if department.code != code:
                department.code = code
                changed_fields.append("code")
            if not department.is_active:
                department.is_active = True
                changed_fields.append("is_active")
            if changed_fields:
                department.save(update_fields=[*changed_fields, "updated_at"])
        return department

    def _upsert_position(self, row: dict[str, Any]) -> Position:
        role = clean_text(row.get("role"))
        name = trim(ROLE_POSITION_NAMES.get(role) or role or "Співробітник", 180)
        position, created = Position.objects.get_or_create(name=name, defaults={"is_active": True})
        if created:
            self.counters["positions_created"] += 1
        elif not position.is_active:
            position.is_active = True
            position.save(update_fields=["is_active", "updated_at"])
        return position

    def _upsert_specialties(self, items: list[dict[str, Any]]) -> list[MedicalSpecialty]:
        specialties = []
        seen_names = set()
        for item in items:
            name = trim(clean_text(item.get("specialty_name")) or clean_text(item.get("name")), 200)
            if not name:
                continue
            name_key = name.casefold()
            if name_key in seen_names:
                continue
            seen_names.add(name_key)
            external_id = trim(clean_text(item.get("specialty_id")), 120)
            specialty = None
            if external_id:
                specialty = MedicalSpecialty.objects.filter(external_fotopacients_id=external_id).first()
            if specialty is None:
                specialty, created = MedicalSpecialty.objects.get_or_create(
                    name=name,
                    defaults={"external_fotopacients_id": external_id, "is_active": True},
                )
                if created:
                    self.counters["specialties_created"] += 1
            changed_fields = []
            if specialty.name != name:
                specialty.name = name
                changed_fields.append("name")
            if external_id and not specialty.external_fotopacients_id:
                specialty.external_fotopacients_id = external_id
                changed_fields.append("external_fotopacients_id")
            if not specialty.is_active:
                specialty.is_active = True
                changed_fields.append("is_active")
            if changed_fields:
                specialty.save(update_fields=[*changed_fields, "updated_at"])
            specialties.append(specialty)
        return specialties

    def _specialty_items(self, record: FotoPacientsEmployeeRecord) -> list[dict[str, Any]]:
        items = list(record.specialties)
        seen_names = {clean_text(item.get("specialty_name")).casefold() for item in items}
        for name in split_specialty_text(record.payload.get("specialty")):
            if name.casefold() in seen_names:
                continue
            items.append({"specialty_id": "", "specialty_name": name})
            seen_names.add(name.casefold())
        return items

    def _raw_hash(self, record: FotoPacientsEmployeeRecord) -> str:
        payload = {
            "employee": record.payload,
            "departments": record.departments,
            "specialties": self._specialty_items(record),
        }
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _add_issue(
        self,
        run: EmployeeImportRun,
        severity: str,
        external_id: str,
        message: str,
        raw_fragment: dict[str, Any],
    ) -> None:
        EmployeeImportIssue.objects.create(
            run=run,
            severity=severity,
            external_id=trim(external_id, 160),
            message=trim(message, 500),
            raw_fragment=raw_fragment,
        )
        self.counters["issues"] += 1


def dict_rows(cursor) -> list[dict[str, Any]]:
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def trim(value: str, max_length: int) -> str:
    return value[:max_length]


def split_specialty_text(value: Any) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    parts = re.split(r"[;,]\s*", text)
    return [trim(part.strip(), 200) for part in parts if part.strip()]


def make_code(prefix: str, label: str, external_id: str, max_length: int) -> str:
    ident = re.sub(r"[^0-9a-zA-Z]+", "", external_id)[:8]
    slug = re.sub(r"[^0-9a-zA-Z]+", "-", label.lower()).strip("-")
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
