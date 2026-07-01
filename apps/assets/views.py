from urllib.parse import quote

import httpx
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.employees.models import Employee

from .cmms_client import CmmsError, cmms_client
from .models import AssetResponsibilityZone

# Single-value and multi-value (repeatable) filter params forwarded to CMMS.
_PASSTHROUGH_SINGLE = ("search", "status", "asset_type_id", "tags")
_PASSTHROUGH_MULTI = ("location_ids", "department_ids", "category_ids", "responsible_ids", "engineer_ids")

# Asset statuses CMMS uses (for the status filter dropdown).
_ASSET_STATUSES = ["в експлуатації", "на складі", "у ремонті", "списаний", "резерв"]


def _proxy_photo(signed_path: str | None) -> str | None:
    """Return a same-origin HR URL that proxies a CMMS signed /uploads link.

    The browser hits hr.vidnova.app (no cross-domain / Cloudflare-Access issues);
    HR fetches the bytes from CMMS internally using the embedded signed token.
    """
    if not signed_path or not signed_path.startswith("/uploads/"):
        return None
    return f"/api/assets/photo/?src={quote(signed_path, safe='')}"


def _build_location_paths(locations: list[dict]) -> dict[int, list[str]]:
    """Flatten the CMMS locations tree into {id: [root_name, …, leaf_name]}.

    Локації приходять деревом (місто → клініка → поверх → кабінет); картка активу
    показує повний шлях, тому кешуємо готові списки назв за id вузла.
    """
    paths: dict[int, list[str]] = {}

    def walk(nodes: list[dict], prefix: list[str]) -> None:
        for node in nodes or []:
            node_id = node.get("id")
            name = node.get("name") or ""
            trail = prefix + [name]
            if node_id is not None:
                paths[node_id] = trail
            walk(node.get("sublocations") or [], trail)

    walk(locations, [])
    return paths


def _load_reference_maps() -> dict:
    """CMMS-довідники для збагачення активів: імена співробітників, шляхи локацій, департаменти."""
    name_by_id = {emp["id"]: emp.get("full_name") or emp.get("name") for emp in cmms_client.list_employees()}
    engineer_by_id = {u["id"]: u.get("full_name") or u.get("username") for u in cmms_client.list_users()}
    location_path_by_id = _build_location_paths(cmms_client.list_locations())
    department_name_by_id = {
        dep["id"]: dep.get("name") for dep in cmms_client.list_departments() if dep.get("id") is not None
    }
    return {
        "names": name_by_id,
        "engineers": engineer_by_id,
        "locations": location_path_by_id,
        "departments": department_name_by_id,
    }


def _enrich_asset(item: dict, refs: dict) -> dict:
    """Додає читабельні назви (локація/відповідальний/інженер/департамент) + первинне фото."""
    names = refs["names"]
    path = refs["locations"].get(item.get("location_id"))
    item["responsible_person_name"] = names.get(item.get("responsible_person_id"))
    item["engineer_name"] = refs["engineers"].get(item.get("engineer_id"))
    item["department_name"] = refs["departments"].get(item.get("department_id"))
    item["location_path"] = path
    item["location_name"] = " → ".join(path) if path else None
    photos = item.get("photos") or []
    primary = next((p for p in photos if p.get("is_primary")), photos[0] if photos else None)
    item["photo_url"] = _proxy_photo((primary or {}).get("thumbnail_url") or (primary or {}).get("url"))
    return item


def _sniff_content_type(blob: bytes) -> str:
    if blob.startswith(b"\x89PNG"):
        return "image/png"
    if blob.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if blob[:4] == b"RIFF" and blob[8:12] == b"WEBP":
        return "image/webp"
    if blob[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return "application/octet-stream"


class AssetPhotoProxyView(APIView):
    """Stream a CMMS asset photo (signed /uploads link) through HR's own origin."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        src = request.query_params.get("src", "")
        if not src.startswith("/uploads/"):
            return Response({"detail": "Invalid src"}, status=status.HTTP_400_BAD_REQUEST)
        base = (getattr(settings, "CMMS_API_BASE_URL", "") or "").rstrip("/")
        try:
            resp = httpx.get(f"{base}{src}", timeout=settings.CMMS_API_TIMEOUT)
        except httpx.HTTPError:
            return Response(status=status.HTTP_502_BAD_GATEWAY)
        if resp.status_code != 200:
            return Response(status=resp.status_code)
        content = resp.content
        http_resp = HttpResponse(content, content_type=_sniff_content_type(content))
        http_resp["Cache-Control"] = "private, max-age=600"
        return http_resp


class AssetListView(APIView):
    """Equipment list proxied from CMMS — with responsible names and photo URLs."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        params: dict = {}
        for key in _PASSTHROUGH_SINGLE:
            value = request.query_params.get(key)
            if value not in (None, "", "all"):
                params[key] = value
        for key in _PASSTHROUGH_MULTI:
            values = [v for v in request.query_params.getlist(key) if v not in ("", "all")]
            if values:
                params[key] = values

        # HR→CMMS міст: фільтр активів за HR-співробітником (профіль, вкладка «Активи»).
        hr_employee_id = request.query_params.get("hr_employee_id")
        if hr_employee_id:
            employee = Employee.objects.select_related("position", "department").filter(pk=hr_employee_id).first()
            try:
                cmms_id = cmms_client.find_employee_id(employee) if employee else None
            except CmmsError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
            if cmms_id is None:
                # Немає відповідника в CMMS → активів немає.
                return Response({"total": 0, "items": []})
            params["responsible_ids"] = [str(cmms_id)]
        # CMMS /api/assets/list paginates with skip/limit, not page/page_size.
        try:
            page = max(1, int(request.query_params.get("page", 1) or 1))
            page_size = max(1, min(200, int(request.query_params.get("page_size", 30) or 30)))
        except (TypeError, ValueError):
            page, page_size = 1, 30
        params["skip"] = (page - 1) * page_size
        params["limit"] = page_size

        try:
            data = cmms_client.list_assets(params)
        except CmmsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        try:
            refs = _load_reference_maps()
        except CmmsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        items = data.get("items", []) if isinstance(data, dict) else (data or [])
        for item in items:
            _enrich_asset(item, refs)
            item.pop("photos", None)  # список активів тримаємо тонким — тільки photo_url
        return Response(
            {
                "total": data.get("total", len(items)) if isinstance(data, dict) else len(items),
                "items": items,
            }
        )


class AssetDetailApiView(APIView):
    """Single asset for the /assets/:id page — enriched + full proxied photo gallery."""

    permission_classes = [IsAuthenticated]

    def get(self, request, asset_id: int):
        try:
            asset = cmms_client.get_asset(int(asset_id))
            refs = _load_reference_maps()
        except CmmsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        _enrich_asset(asset, refs)
        asset["photos"] = [
            {
                "id": photo.get("id"),
                "url": _proxy_photo(photo.get("url")),
                "thumbnail_url": _proxy_photo(photo.get("thumbnail_url") or photo.get("url")),
                "is_primary": bool(photo.get("is_primary")),
            }
            for photo in (asset.get("photos") or [])
        ]
        return Response(asset)


class AssetOwnershipHistoryView(APIView):
    """Ownership-history timeline for the /assets/:id page (proxied from CMMS)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, asset_id: int):
        try:
            rows = cmms_client.get_asset_ownership_history(int(asset_id))
        except CmmsError as exc:
            # Ендпоінт CMMS ще може бути не задеплоєний → не ламаємо сторінку активу.
            return Response({"items": [], "detail": str(exc)}, status=status.HTTP_200_OK)
        return Response({"items": rows if isinstance(rows, list) else []})


class AssetOptionsView(APIView):
    """Filter options for the assets page (locations tree, departments, types…)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            employees = [
                {"id": emp["id"], "full_name": emp.get("full_name") or emp.get("name")}
                for emp in cmms_client.list_employees()
            ]
            return Response(
                {
                    "statuses": _ASSET_STATUSES,
                    "asset_types": cmms_client.list_asset_types(),
                    "categories": cmms_client.list_categories(),
                    "locations": cmms_client.list_locations(),
                    "departments": cmms_client.list_departments(),
                    "employees": sorted(employees, key=lambda e: (e["full_name"] or "")),
                }
            )
        except CmmsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


class AssignResponsibleView(APIView):
    """Assign / clear an asset's responsible person using HR employees as the master."""

    permission_classes = [IsAuthenticated]

    def post(self, request, asset_id: int):
        employee_id = request.data.get("employee_id")
        employee = None
        try:
            if employee_id in (None, "", "null"):
                cmms_employee_id = None
            else:
                employee = Employee.objects.select_related("position", "department").get(pk=employee_id)
                cmms_employee_id = cmms_client.resolve_employee_id(employee)
            cmms_client.set_asset_responsible(int(asset_id), cmms_employee_id)
        except Employee.DoesNotExist:
            return Response({"detail": "Співробітника не знайдено"}, status=status.HTTP_404_NOT_FOUND)
        except CmmsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "asset_id": int(asset_id),
                "responsible_person_id": cmms_employee_id,
                "responsible_person_name": employee.full_name if employee else None,
            }
        )


# ---------------------------------------------------------------------------
# Зони відповідальності (Settings → Основні → «Активи»)
# ---------------------------------------------------------------------------

def _zone_to_dict(zone: AssetResponsibilityZone) -> dict:
    return {
        "id": zone.id,
        "name": zone.name,
        "scope_type": zone.scope_type,
        "location_id": zone.location_id,
        "location_name": zone.location_name,
        "department_id": zone.department_id,
        "department_name": zone.department_name,
        "engineer_user_id": zone.engineer_user_id,
        "engineer_name": zone.engineer_name,
        "last_applied_at": zone.last_applied_at,
        "last_applied_count": zone.last_applied_count,
    }


def _find_location_node(locations: list[dict], target_id: int) -> dict | None:
    for node in locations:
        if node.get("id") == target_id:
            return node
        found = _find_location_node(node.get("sublocations") or [], target_id)
        if found:
            return found
    return None


def _collect_subtree_ids(node: dict) -> list[int]:
    ids = [node["id"]]
    for child in node.get("sublocations") or []:
        ids.extend(_collect_subtree_ids(child))
    return ids


def _apply_zone_fields(zone: AssetResponsibilityZone, data: dict) -> AssetResponsibilityZone:
    zone.name = (data.get("name") or "").strip()
    zone.scope_type = data.get("scope_type") or AssetResponsibilityZone.SCOPE_LOCATION
    zone.location_id = data.get("location_id") or None
    zone.location_name = (data.get("location_name") or "").strip()
    zone.department_id = data.get("department_id") or None
    zone.department_name = (data.get("department_name") or "").strip()
    zone.engineer_user_id = data.get("engineer_user_id") or None
    zone.engineer_name = (data.get("engineer_name") or "").strip()
    zone.save()
    return zone


def _assets_in_scope(zone: AssetResponsibilityZone) -> list[int]:
    """Всі id активів CMMS у межах скоупу зони (субдерево локації або департамент)."""
    params: dict = {}
    if zone.scope_type == AssetResponsibilityZone.SCOPE_LOCATION and zone.location_id:
        node = _find_location_node(cmms_client.list_locations(), zone.location_id)
        ids = _collect_subtree_ids(node) if node else [zone.location_id]
        params["location_ids"] = [str(i) for i in ids]
    elif zone.scope_type == AssetResponsibilityZone.SCOPE_DEPARTMENT and zone.department_id:
        params["department_ids"] = [str(zone.department_id)]
    else:
        return []

    asset_ids: list[int] = []
    skip = 0
    while True:
        page = cmms_client.list_assets({**params, "skip": skip, "limit": 200})
        items = page.get("items", []) if isinstance(page, dict) else (page or [])
        asset_ids.extend(a["id"] for a in items if a.get("id") is not None)
        if len(items) < 200:
            break
        skip += 200
    return asset_ids


class AssetZoneOptionsView(APIView):
    """Довідники для сторінки зон: дерево локацій, департаменти, інженери (CMMS users)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            engineers = [
                {"id": u["id"], "full_name": u.get("full_name") or u.get("username")}
                for u in cmms_client.list_users()
            ]
            return Response(
                {
                    "locations": cmms_client.list_locations(),
                    "departments": cmms_client.list_departments(),
                    "engineers": sorted(engineers, key=lambda e: (e["full_name"] or "")),
                }
            )
        except CmmsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)


class AssetZoneListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        zones = AssetResponsibilityZone.objects.all()
        return Response({"items": [_zone_to_dict(z) for z in zones]})

    def post(self, request):
        zone = _apply_zone_fields(AssetResponsibilityZone(), request.data)
        return Response(_zone_to_dict(zone), status=status.HTTP_201_CREATED)


class AssetZoneDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, zone_id: int):
        zone = get_object_or_404(AssetResponsibilityZone, pk=zone_id)
        zone = _apply_zone_fields(zone, request.data)
        return Response(_zone_to_dict(zone))

    def delete(self, request, zone_id: int):
        AssetResponsibilityZone.objects.filter(pk=zone_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AssetZoneApplyView(APIView):
    """Застосувати зону: проставити engineer_id усім активам у скоупі.

    ?preview=1 → лише порахувати, скільки активів у скоупі (без запису).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, zone_id: int):
        zone = get_object_or_404(AssetResponsibilityZone, pk=zone_id)
        preview = request.query_params.get("preview") in ("1", "true", "yes")
        if not zone.engineer_user_id and not preview:
            return Response({"detail": "У зоні не призначено інженера"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            asset_ids = _assets_in_scope(zone)
            if preview:
                return Response({"count": len(asset_ids)})
            for asset_id in asset_ids:
                cmms_client.set_asset_engineer(asset_id, zone.engineer_user_id)
        except CmmsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        zone.last_applied_at = timezone.now()
        zone.last_applied_count = len(asset_ids)
        zone.save(update_fields=["last_applied_at", "last_applied_count"])
        return Response({"applied": len(asset_ids)})
