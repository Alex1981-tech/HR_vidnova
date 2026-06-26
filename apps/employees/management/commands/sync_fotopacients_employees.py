from __future__ import annotations

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError

from apps.employees.integrations.fotopacients import sync_fotopacients_employees


class Command(BaseCommand):
    help = "Sync all staff employees from FotoPacients accounts_user into HR Vidnova."

    def add_arguments(self, parser):
        parser.add_argument(
            "--database",
            default="fotopacients",
            help="Django database alias for the FotoPacients database.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Read FotoPacients and record an import run without changing employee dictionaries.",
        )
        parser.add_argument(
            "--include-inactive",
            action="store_true",
            help="Include inactive or soft-deleted FotoPacients users and mark them dismissed in HR.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Process only the first N staff rows. Useful for checking mappings.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit is not None and limit < 1:
            raise CommandError("--limit must be greater than zero.")

        try:
            result = sync_fotopacients_employees(
                database=options["database"],
                dry_run=options["dry_run"],
                include_inactive=options["include_inactive"],
                limit=limit,
            )
        except ImproperlyConfigured as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"FotoPacients import run #{result.run_id}: {result.status}, "
                f"issues={result.issues_count}"
            )
        )
        for key, value in sorted(result.counters.items()):
            self.stdout.write(f"{key}: {value}")
