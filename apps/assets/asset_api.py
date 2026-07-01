"""HR-нативний API активів (після консолідації — читає з HR-моделей, не проксі CMMS).

Тримає ту саму форму відповіді, що й старі проксі-в'юхи (`responsible_person_name`,
`location_name`, `photo_url`, …), щоб фронт працював без змін.
"""

from __future__ import annotations

from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.employees.models import Department, Employee

from django.shortcuts import get_object_or_404

from .models import Asset, AssetCategory, AssetOwnershipEvent, AssetType, PhysicalLocation

_ASSET_STATUSES = ["в експлуатації", "на складі", "у ремонті", "списаний", "резерв"]


# ---- location tree helpers -------------------------------------------------
def _location_index() -> dict[int, PhysicalLocation]:
    return {loc.id: loc for loc in PhysicalLocation.objects.all()}


def _path_names(loc_id, index) -> list[str]:
    names: list[str] = []
    node = index.get(loc_id)
    while node is not None:
        names.append(node.name)
        node = index.get(node.parent_id)
    return list(reversed(names))


def _subtree_ids(root_id, index) -> list[int]:
    children_by_parent: dict[int, list[int]] = {}
    for loc in index.values():
        children_by_parent.setdefault(loc.parent_id, []).append(loc.id)
    out, stack = [], [root_id]
    while stack:
        cur = stack.pop()
        out.append(cur)
        stack.extend(children_by_parent.get(cur, []))
    return out


def _location_tree() -> list[dict]:
    index = _location_index()
    children: dict[int, list[PhysicalLocation]] = {}
    roots: list[PhysicalLocation] = []
    for loc in sorted(index.values(), key=lambda n: (n.order, n.name)):
        if loc.parent_id:
            children.setdefault(loc.parent_id, []).append(loc)
        else:
            roots.append(loc)

    def build(node) -> dict:
        return {
            "id": node.id,
            "name": node.name,
            "parent_id": node.parent_id,
            "level": node.level,
            "sublocations": [build(c) for c in children.get(node.id, [])],
        }

    return [build(r) for r in roots]


def _photo_url(asset) -> str | None:
    # Обкладинка картки — тільки зображення (не відео).
    images = [p for p in asset.photos.all() if p.image and not p.is_video]
    if not images:
        return None
    primary = next((p for p in images if p.is_primary), images[0])
    return primary.image.url


def _person_dict(emp) -> dict | None:
    if not emp:
        return None
    avatar = ""
    if getattr(emp, "avatar_file", None):
        try:
            avatar = emp.avatar_file.url
        except ValueError:
            avatar = ""
    if not avatar:
        avatar = getattr(emp, "avatar_url", "") or ""
    return {
        "id": emp.id,
        "full_name": emp.full_name,
        "position": emp.position.name if getattr(emp, "position_id", None) and emp.position else "",
        "avatar_url": avatar or None,
    }


def _asset_dict(asset, index, *, detail=False) -> dict:
    path = _path_names(asset.location_id, index) if asset.location_id else None
    data = {
        "id": asset.id,
        "inventory_number": asset.inventory_number,
        "name": asset.name,
        "status": asset.status,
        "manufacturer": asset.manufacturer,
        "asset_type_id": asset.asset_type_id,
        "category_id": asset.category_id,
        "location_id": asset.location_id,
        "location_path": path,
        "location_name": " → ".join(path) if path else None,
        "department_id": asset.department_id,
        "department_name": asset.department.name if asset.department else None,
        "responsible_person_id": asset.responsible_id,
        "responsible_person_name": asset.responsible.full_name if asset.responsible else None,
        "engineer_id": asset.engineer_id,
        "engineer_name": asset.engineer.full_name if asset.engineer else None,
        "photo_url": _photo_url(asset),
    }
    if detail:
        data["description"] = asset.description
        data["tags"] = asset.tags
        data["responsible"] = _person_dict(asset.responsible)
        data["engineer"] = _person_dict(asset.engineer)
        data["photos"] = [
            {
                "id": p.id,
                "url": p.image.url if p.image else None,
                "thumbnail_url": p.image.url if p.image else None,
                "is_primary": p.is_primary,
                "content_type": p.content_type,
                "is_video": p.is_video,
            }
            for p in asset.photos.all()
        ]
    return data


def _multi(request, key) -> list[int]:
    out = []
    for v in request.query_params.getlist(key):
        if v not in ("", "all"):
            try:
                out.append(int(v))
            except (TypeError, ValueError):
                pass
    return out


class AssetListView(APIView):
    """Список активів (HR-нативно) з фільтрами й пагінацією."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Asset.objects.filter(is_active=True).select_related(
            "location", "department", "responsible", "engineer"
        ).prefetch_related("photos")

        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(inventory_number__icontains=search))

        status_value = request.query_params.get("status")
        if status_value not in (None, "", "all"):
            qs = qs.filter(status=status_value)

        location_ids = _multi(request, "location_ids")
        if location_ids:
            qs = qs.filter(location_id__in=location_ids)

        department_ids = _multi(request, "department_ids")
        if department_ids:
            qs = qs.filter(department_id__in=department_ids)

        responsible_ids = _multi(request, "responsible_ids")
        if responsible_ids:
            qs = qs.filter(responsible_id__in=responsible_ids)

        hr_employee_id = request.query_params.get("hr_employee_id")
        if hr_employee_id:
            qs = qs.filter(responsible_id=hr_employee_id)

        qs = qs.order_by("name")
        total = qs.count()

        try:
            page = max(1, int(request.query_params.get("page", 1) or 1))
            page_size = max(1, min(200, int(request.query_params.get("page_size", 30) or 30)))
        except (TypeError, ValueError):
            page, page_size = 1, 30
        start = (page - 1) * page_size
        page_items = list(qs[start:start + page_size])

        index = _location_index()
        return Response({"total": total, "items": [_asset_dict(a, index) for a in page_items]})


class AssetDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, asset_id: int):
        asset = (
            Asset.objects.filter(pk=asset_id)
            .select_related("location", "department", "responsible__position", "engineer__position")
            .prefetch_related("photos")
            .first()
        )
        if not asset:
            return Response({"detail": "Актив не знайдено"}, status=status.HTTP_404_NOT_FOUND)
        return Response(_asset_dict(asset, _location_index(), detail=True))


class AssetOptionsView(APIView):
    """Довідники фільтрів (HR-нативно): статуси, дерево локацій, департаменти, співробітники."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        departments = [{"id": d.id, "name": d.name} for d in Department.objects.filter(is_active=True).order_by("name")]
        employees = [
            {"id": e.id, "full_name": e.full_name}
            for e in Employee.objects.filter(status=Employee.Status.ACTIVE).order_by("last_name", "first_name")
        ]
        return Response(
            {
                "statuses": _ASSET_STATUSES,
                "asset_types": [{"id": t.id, "name": t.name} for t in AssetType.objects.order_by("name")],
                "categories": [
                    {"id": c.id, "name": c.name, "parent_id": c.parent_id}
                    for c in AssetCategory.objects.order_by("name")
                ],
                "locations": _location_tree(),
                "departments": departments,
                "employees": employees,
            }
        )


def _split_path(path: list[str]) -> tuple:
    """[місто, клініка, поверх, кабінет] → (city, clinic, cabinet)."""
    city = path[0] if len(path) >= 1 else None
    clinic = path[1] if len(path) >= 2 else None
    cabinet = path[-1] if len(path) >= 4 else None
    return city, clinic, cabinet


class AssetOwnershipHistoryView(APIView):
    """Історія володіння — нативно з AssetOwnershipEvent (без CMMS)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, asset_id: int):
        asset = Asset.objects.filter(pk=asset_id).select_related("location", "responsible", "engineer").first()
        if not asset:
            return Response({"items": []})
        index = _location_index()
        events = list(
            asset.ownership_events.select_related("location", "responsible", "engineer").order_by("changed_at", "id")
        )

        if not events:
            # Синтетичний creation-рядок з поточного стану (для активів без зафіксованих подій).
            path = _path_names(asset.location_id, index) if asset.location_id else []
            city, clinic, cabinet = _split_path(path)
            return Response({"items": [{
                "date": asset.created_at.isoformat() if asset.created_at else "",
                "city": city, "clinic": clinic, "cabinet": cabinet,
                "responsible_name": asset.responsible.full_name if asset.responsible else None,
                "engineer_name": asset.engineer.full_name if asset.engineer else None,
                "handed_over": None, "is_creation": True,
            }]})

        rows = []
        for ev in events:
            path = _path_names(ev.location_id, index) if ev.location_id else []
            city, clinic, cabinet = _split_path(path)
            rows.append({
                "date": ev.changed_at.isoformat(),
                "city": city, "clinic": clinic, "cabinet": cabinet,
                "responsible_name": ev.responsible.full_name if ev.responsible else None,
                "engineer_name": ev.engineer.full_name if ev.engineer else None,
                "is_creation": ev.is_creation,
            })
        for k in range(len(rows)):
            rows[k]["handed_over"] = rows[k + 1]["date"] if k + 1 < len(rows) else None
        rows.reverse()
        return Response({"items": rows})


class AssignResponsibleView(APIView):
    """Призначити/зняти відповідального (HR-нативно)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, asset_id: int):
        asset = Asset.objects.filter(pk=asset_id).first()
        if not asset:
            return Response({"detail": "Актив не знайдено"}, status=status.HTTP_404_NOT_FOUND)
        employee_id = request.data.get("employee_id")
        if employee_id in (None, "", "null"):
            asset.responsible = None
        else:
            employee = Employee.objects.filter(pk=employee_id).first()
            if not employee:
                return Response({"detail": "Співробітника не знайдено"}, status=status.HTTP_404_NOT_FOUND)
            asset.responsible = employee
        asset.save(update_fields=["responsible", "updated_at"])
        return Response(
            {
                "asset_id": asset.id,
                "responsible_person_id": asset.responsible_id,
                "responsible_person_name": asset.responsible.full_name if asset.responsible else None,
            }
        )


# ---------------------------------------------------------------------------
# Фізична структура (tree-builder): клініка → поверхи → кабінети
# ---------------------------------------------------------------------------

# Наступний рівень при додаванні дочірнього вузла.
_CHILD_KIND = {
    None: PhysicalLocation.KIND_CITY,
    PhysicalLocation.KIND_CITY: PhysicalLocation.KIND_CLINIC,
    PhysicalLocation.KIND_CLINIC: PhysicalLocation.KIND_FLOOR,
    PhysicalLocation.KIND_FLOOR: PhysicalLocation.KIND_CABINET,
    PhysicalLocation.KIND_CABINET: PhysicalLocation.KIND_CABINET,
}


def _pl_tree() -> list[dict]:
    index = {loc.id: loc for loc in PhysicalLocation.objects.select_related("engineer").all()}
    ordered = sorted(index.values(), key=lambda n: (n.order, n.name))
    children: dict[int, list[PhysicalLocation]] = {}
    roots: list[PhysicalLocation] = []
    for loc in ordered:
        if loc.parent_id:
            children.setdefault(loc.parent_id, []).append(loc)
        else:
            roots.append(loc)

    # к-сть активів по вузлах (для UI/захисту видалення)
    asset_counts: dict[int, int] = {}
    for lid in Asset.objects.filter(location_id__isnull=False).values_list("location_id", flat=True):
        asset_counts[lid] = asset_counts.get(lid, 0) + 1

    def build(node) -> dict:
        return {
            "id": node.id,
            "name": node.name,
            "kind": node.kind,
            "parent_id": node.parent_id,
            "order": node.order,
            "asset_count": asset_counts.get(node.id, 0),
            "engineer_id": node.engineer_id,
            "engineer_name": node.engineer.full_name if node.engineer else None,
            "children": [build(c) for c in children.get(node.id, [])],
        }

    return [build(r) for r in roots]


class PhysicalLocationListView(APIView):
    """Дерево фізичної структури + створення вузла."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"items": _pl_tree(), "child_kind": _CHILD_KIND})

    def post(self, request):
        parent_id = request.data.get("parent_id") or None
        parent = PhysicalLocation.objects.filter(pk=parent_id).first() if parent_id else None
        kind = request.data.get("kind") or _CHILD_KIND.get(parent.kind if parent else None)
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"detail": "Вкажіть назву"}, status=status.HTTP_400_BAD_REQUEST)
        last = PhysicalLocation.objects.filter(parent=parent).order_by("-order").first()
        node = PhysicalLocation.objects.create(
            name=name, kind=kind, parent=parent, order=(last.order + 1 if last else 0)
        )
        return Response(
            {"id": node.id, "name": node.name, "kind": node.kind, "parent_id": node.parent_id},
            status=status.HTTP_201_CREATED,
        )


class PhysicalLocationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, node_id: int):
        node = get_object_or_404(PhysicalLocation, pk=node_id)
        if "name" in request.data:
            node.name = (request.data.get("name") or "").strip() or node.name
        if request.data.get("kind"):
            node.kind = request.data["kind"]
        if request.data.get("order") is not None:
            node.order = request.data["order"]
        if "engineer_id" in request.data:
            eng_id = request.data.get("engineer_id")
            node.engineer = Employee.objects.filter(pk=eng_id).first() if eng_id else None
        node.save()
        return Response(
            {
                "id": node.id,
                "name": node.name,
                "kind": node.kind,
                "parent_id": node.parent_id,
                "engineer_id": node.engineer_id,
                "engineer_name": node.engineer.full_name if node.engineer else None,
            }
        )

    def delete(self, request, node_id: int):
        node = get_object_or_404(PhysicalLocation, pk=node_id)
        index = _location_index()
        subtree = set(_subtree_ids(node.id, index))
        assets_here = Asset.objects.filter(location_id__in=subtree).count()
        if assets_here:
            return Response(
                {"detail": f"У цій зоні/субдереві {assets_here} активів. Спершу переназначте їх."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        node.delete()  # cascade дочірні (порожні)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PhysicalLocationApplyView(APIView):
    """Застосувати інженера вузла до всіх активів у субдереві (`?preview=1` — лише підрахунок)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, node_id: int):
        node = get_object_or_404(PhysicalLocation, pk=node_id)
        index = _location_index()
        subtree = _subtree_ids(node.id, index)
        qs = Asset.objects.filter(location_id__in=subtree)

        preview = request.query_params.get("preview") in ("1", "true", "yes")
        if preview:
            return Response({"count": qs.count()})
        if not node.engineer_id:
            return Response({"detail": "У вузлі не призначено інженера"}, status=status.HTTP_400_BAD_REQUEST)

        applied = 0
        for asset in qs.exclude(engineer_id=node.engineer_id):
            asset.engineer_id = node.engineer_id
            asset.save(update_fields=["engineer", "updated_at"])  # тригерить ownership-event
            applied += 1
        return Response({"applied": applied, "total": qs.count()})
