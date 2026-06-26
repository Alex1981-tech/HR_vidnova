from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.utils import timezone

from apps.access.models import EmployeeTelegramLink
from apps.access.services import normalize_phone
from apps.employees.models import Employee


@dataclass(frozen=True)
class FotoTelegramLink:
    external_id: str
    telegram_chat_id: int
    phone_normalized: str


class Command(BaseCommand):
    help = "Sync Telegram chat links from FotoPacients accounts_user into HR auth links."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="fotopacients", help="Django DB alias for FotoPacients.")
        parser.add_argument("--dry-run", action="store_true", help="Report changes without writing HR links.")
        parser.add_argument(
            "--source-tsv",
            default="",
            help="Read FotoPacients links from TSV instead of connecting to the FotoPacients DB.",
        )

    def handle(self, *args, **options):
        database = options["database"]
        dry_run = options["dry_run"]
        source_tsv = options["source_tsv"]
        if source_tsv:
            links = self._read_links_tsv(source_tsv)
        elif database not in connections.databases:
            raise CommandError(
                f"Database alias '{database}' is not configured. "
                "Set FOTOPACIENTS_DB_ENABLED=1 and FOTOPACIENTS_DB_* env vars."
            )
        else:
            links = self._fetch_fotopacients_links(database)
        employees = Employee.objects.filter(
            status=Employee.Status.ACTIVE,
        ).only("id", "external_fotopacients_id", "phone", "phone2", "status")
        employees_by_external_id: dict[str, Employee] = {}
        employees_by_phone: dict[str, list[Employee]] = {}
        for employee in employees:
            if employee.external_fotopacients_id:
                employees_by_external_id[employee.external_fotopacients_id] = employee
            for phone in {normalize_phone(employee.phone), normalize_phone(employee.phone2)}:
                if not phone:
                    continue
                employees_by_phone.setdefault(phone, []).append(employee)

        stats = {
            "source_links": len(links),
            "created": 0,
            "updated": 0,
            "unchanged": 0,
            "reassigned": 0,
            "skipped_no_employee": 0,
            "skipped_phone_conflict": 0,
        }

        for link in links:
            employee = self._match_employee(link, employees_by_external_id, employees_by_phone)
            if employee is None:
                stats["skipped_no_employee"] += 1
                continue
            if employee == "phone_conflict":
                stats["skipped_phone_conflict"] += 1
                continue
            phone_normalized = normalize_phone(employee.phone) or normalize_phone(employee.phone2) or link.phone_normalized
            if dry_run:
                existing = getattr(employee, "telegram_link", None)
                if existing is None:
                    stats["created"] += 1
                elif existing.telegram_chat_id != link.telegram_chat_id or not existing.is_active:
                    stats["updated"] += 1
                else:
                    stats["unchanged"] += 1
                continue

            with transaction.atomic():
                stats["reassigned"] += EmployeeTelegramLink.objects.select_for_update().filter(
                    telegram_chat_id=link.telegram_chat_id,
                    is_active=True,
                ).exclude(employee=employee).update(is_active=False)

                existing = EmployeeTelegramLink.objects.select_for_update().filter(employee=employee).first()
                now = timezone.now()
                if existing is None:
                    EmployeeTelegramLink.objects.create(
                        employee=employee,
                        telegram_chat_id=link.telegram_chat_id,
                        phone_normalized=phone_normalized,
                        linked_at=now,
                        last_seen_at=now,
                    )
                    stats["created"] += 1
                    continue

                changed = (
                    existing.telegram_chat_id != link.telegram_chat_id
                    or existing.phone_normalized != phone_normalized
                    or not existing.is_active
                )
                if not changed:
                    stats["unchanged"] += 1
                    continue

                existing.telegram_chat_id = link.telegram_chat_id
                existing.phone_normalized = phone_normalized
                existing.is_active = True
                existing.last_seen_at = now
                existing.save(update_fields=["telegram_chat_id", "phone_normalized", "is_active", "last_seen_at", "updated_at"])
                stats["updated"] += 1

        mode = "DRY RUN" if dry_run else "APPLIED"
        self.stdout.write(self.style.SUCCESS(f"{mode}: {stats}"))

    @staticmethod
    def _match_employee(
        link: FotoTelegramLink,
        employees_by_external_id: dict[str, Employee],
        employees_by_phone: dict[str, list[Employee]],
    ) -> Employee | str | None:
        employee = employees_by_external_id.get(link.external_id)
        if employee is not None:
            return employee
        if not link.phone_normalized:
            return None
        matches = employees_by_phone.get(link.phone_normalized, [])
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            return "phone_conflict"
        return None

    @staticmethod
    def _fetch_fotopacients_links(database: str) -> list[FotoTelegramLink]:
        with connections[database].cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    CAST(id AS text),
                    telegram_chat_id,
                    phone_normalized,
                    phone,
                    phone2_normalized,
                    phone2
                FROM accounts_user
                WHERE telegram_chat_id IS NOT NULL
                  AND is_active = TRUE
                  AND is_deleted = FALSE
                """
            )
            rows = cursor.fetchall()

        links_by_chat_id: dict[int, FotoTelegramLink] = {}
        for external_id, telegram_chat_id, phone_normalized, phone, phone2_normalized, phone2 in rows:
            normalized_phone = (
                normalize_phone(phone_normalized)
                or normalize_phone(phone)
                or normalize_phone(phone2_normalized)
                or normalize_phone(phone2)
            )
            links_by_chat_id[int(telegram_chat_id)] = FotoTelegramLink(
                external_id=str(external_id),
                telegram_chat_id=int(telegram_chat_id),
                phone_normalized=normalized_phone,
            )
        return list(links_by_chat_id.values())

    @staticmethod
    def _read_links_tsv(path: str) -> list[FotoTelegramLink]:
        links_by_chat_id: dict[int, FotoTelegramLink] = {}
        for line_number, line in enumerate(Path(path).read_text().splitlines(), start=1):
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) != 6:
                raise CommandError(f"Invalid TSV row {line_number}: expected 6 columns, got {len(parts)}")
            external_id, telegram_chat_id, phone_normalized, phone, phone2_normalized, phone2 = parts
            normalized_phone = (
                normalize_phone(phone_normalized)
                or normalize_phone(phone)
                or normalize_phone(phone2_normalized)
                or normalize_phone(phone2)
            )
            links_by_chat_id[int(telegram_chat_id)] = FotoTelegramLink(
                external_id=str(external_id),
                telegram_chat_id=int(telegram_chat_id),
                phone_normalized=normalized_phone,
            )
        return list(links_by_chat_id.values())
