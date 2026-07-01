"""Бекфіл фізичної структури з CMMS locations у HR (одноразово перед тим, як HR стане майстром).

Ідемпотентно: матчить наявні PhysicalLocation за cmms_location_id, оновлює name/kind/parent.
"""

from django.core.management.base import BaseCommand

from apps.assets.cmms_client import CmmsError, cmms_client
from apps.assets.models import PhysicalLocation

_LEVEL_KIND = {
    0: PhysicalLocation.KIND_CITY,
    1: PhysicalLocation.KIND_CLINIC,
    2: PhysicalLocation.KIND_FLOOR,
    3: PhysicalLocation.KIND_CABINET,
}


class Command(BaseCommand):
    help = "Імпортує дерево CMMS locations у HR PhysicalLocation (бекфіл)."

    def handle(self, *args, **options):
        try:
            tree = cmms_client.list_locations()
        except CmmsError as exc:
            self.stderr.write(f"CMMS error: {exc}")
            return

        created = updated = 0

        def walk(nodes, parent_hr):
            nonlocal created, updated
            for order, node in enumerate(nodes or []):
                cmms_id = node.get("id")
                level = node.get("level", 0)
                kind = _LEVEL_KIND.get(level, PhysicalLocation.KIND_CABINET)
                obj = PhysicalLocation.objects.filter(cmms_location_id=cmms_id).first()
                if obj:
                    obj.name = node.get("name") or obj.name
                    obj.kind = kind
                    obj.parent = parent_hr
                    obj.order = order
                    obj.save()
                    updated += 1
                else:
                    obj = PhysicalLocation.objects.create(
                        name=node.get("name") or "",
                        kind=kind,
                        parent=parent_hr,
                        order=order,
                        cmms_location_id=cmms_id,
                    )
                    created += 1
                walk(node.get("sublocations") or [], obj)

        walk(tree, None)
        self.stdout.write(self.style.SUCCESS(f"Готово: створено {created}, оновлено {updated}."))
