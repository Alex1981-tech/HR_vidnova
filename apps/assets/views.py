from urllib.parse import quote

import httpx
from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.employees.models import Employee

from .cmms_client import CmmsError, cmms_client

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
            employees = cmms_client.list_employees()
        except CmmsError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        name_by_id = {emp["id"]: emp.get("full_name") or emp.get("name") for emp in employees}
        items = data.get("items", []) if isinstance(data, dict) else (data or [])
        for item in items:
            item["responsible_person_name"] = name_by_id.get(item.get("responsible_person_id"))
            photos = item.get("photos") or []
            primary = photos[0] if photos else None
            item["photo_url"] = _proxy_photo((primary or {}).get("thumbnail_url") or (primary or {}).get("url"))
            item.pop("photos", None)  # keep payload lean
        return Response(
            {
                "total": data.get("total", len(items)) if isinstance(data, dict) else len(items),
                "items": items,
            }
        )


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
