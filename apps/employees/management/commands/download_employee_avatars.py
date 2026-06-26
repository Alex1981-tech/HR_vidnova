from django.core.management.base import BaseCommand, CommandError

from apps.employees.avatar_import import download_employee_avatar
from apps.employees.models import Employee


class Command(BaseCommand):
    help = "Download employee avatars from imported avatar_url values into local media storage."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Re-download avatars even when the local file already exists for the same source URL.")
        parser.add_argument("--limit", type=int, default=None, help="Limit number of employees processed.")
        parser.add_argument("--employee-id", type=int, default=None, help="Download avatar for one local Employee ID.")
        parser.add_argument("--active-only", action="store_true", help="Process only active employees.")

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit is not None and limit < 1:
            raise CommandError("--limit must be greater than zero.")

        qs = Employee.objects.exclude(avatar_url="").order_by("last_name", "first_name", "id")
        if options["employee_id"]:
            qs = qs.filter(id=options["employee_id"])
        if options["active_only"]:
            qs = qs.filter(status=Employee.Status.ACTIVE)
        if limit:
            qs = qs[:limit]

        counters = {"downloaded": 0, "skipped": 0, "error": 0}
        for employee in qs:
            result = download_employee_avatar(employee, force=options["force"])
            counters[result.status] = counters.get(result.status, 0) + 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Employee avatars: downloaded={counters.get('downloaded', 0)}, "
                f"skipped={counters.get('skipped', 0)}, errors={counters.get('error', 0)}"
            )
        )
