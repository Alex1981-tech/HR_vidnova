"""Бекфіл стартової події власності (is_creation) для активів без історії."""

from django.core.management.base import BaseCommand

from apps.assets.models import Asset, AssetOwnershipEvent


class Command(BaseCommand):
    help = "Створює стартову AssetOwnershipEvent (is_creation) з поточного стану для активів без подій."

    def handle(self, *args, **options):
        created = 0
        for asset in Asset.objects.filter(ownership_events__isnull=True).distinct():
            AssetOwnershipEvent.objects.create(
                asset=asset,
                changed_at=asset.created_at,
                location=asset.location,
                responsible=asset.responsible,
                engineer=asset.engineer,
                is_creation=True,
            )
            created += 1
        self.stdout.write(self.style.SUCCESS(f"Готово: створено {created} стартових подій."))
