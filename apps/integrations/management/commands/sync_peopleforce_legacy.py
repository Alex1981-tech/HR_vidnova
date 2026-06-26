from __future__ import annotations

from datetime import date

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError

from apps.integrations.peopleforce.importer import PeopleForceLegacyImporter


class Command(BaseCommand):
    help = "Import legacy HR data from PeopleForce into HR Vidnova."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Fetch/inspect without writing normalized data.")
        parser.add_argument("--from-cache", action="store_true", help="Map existing PeopleForceEntity rows without API calls.")
        parser.add_argument("--limit-employees", type=int, default=None, help="Limit employee detail/per-employee imports.")
        parser.add_argument("--skip-per-employee", action="store_true", help="Skip per-employee history/doc/balance endpoints.")
        parser.add_argument("--skip-leave", action="store_true", help="Skip company leave requests import.")
        parser.add_argument("--skip-knowledge", action="store_true", help="Skip knowledge base article import.")
        parser.add_argument("--skip-documents", action="store_true", help="Skip employee documents import.")
        parser.add_argument("--skip-timesheet", action="store_true", help="Skip PeopleForce time/timesheet_entries import.")
        parser.add_argument("--download-document-files", action="store_true", help="Download employee document files from temporary PeopleForce URLs.")
        parser.add_argument("--download-knowledge-attachments", action="store_true", help="Download knowledge base rich-text attachments and rewrite links to local media.")
        parser.add_argument("--timesheet-start", default=None, help="Timesheet import start date, YYYY-MM-DD. Defaults to PEOPLEFORCE_TIMESHEET_START_DATE or 2022-01-01.")
        parser.add_argument("--timesheet-end", default=None, help="Timesheet import end date, YYYY-MM-DD. Defaults to today.")

    def handle(self, *args, **options):
        limit = options["limit_employees"]
        if limit is not None and limit < 1:
            raise CommandError("--limit-employees must be greater than zero.")
        timesheet_start = parse_cli_date(options["timesheet_start"], "--timesheet-start")
        timesheet_end = parse_cli_date(options["timesheet_end"], "--timesheet-end")
        if timesheet_start and timesheet_end and timesheet_start > timesheet_end:
            raise CommandError("--timesheet-start must be earlier than or equal to --timesheet-end.")
        try:
            result = PeopleForceLegacyImporter(
                dry_run=options["dry_run"],
                from_cache=options["from_cache"],
                limit_employees=limit,
                skip_per_employee=options["skip_per_employee"],
                skip_leave=options["skip_leave"],
                skip_knowledge=options["skip_knowledge"],
                skip_documents=options["skip_documents"],
                skip_timesheet=options["skip_timesheet"],
                download_document_files=options["download_document_files"],
                download_knowledge_attachments=options["download_knowledge_attachments"],
                timesheet_start=timesheet_start,
                timesheet_end=timesheet_end,
            ).sync()
        except ImproperlyConfigured as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"PeopleForce import run #{result.run_id}: {result.status}, issues={result.issues_count}"))
        for key, value in sorted(result.counters.items()):
            self.stdout.write(f"{key}: {value}")


def parse_cli_date(value: str | None, option_name: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CommandError(f"{option_name} must use YYYY-MM-DD format.") from exc
