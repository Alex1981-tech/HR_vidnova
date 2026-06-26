from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.employees.models import Employee

from .cmms_client import CmmsError, cmms_client

# Single-value and multi-value (repeatable) filter params forwarded to CMMS.
_PASSTHROUGH_SINGLE = ("page", "page_size", "search", "status", "asset_type_id", "tags")
_PASSTHROUGH_MULTI = ("location_ids", "department_ids", "category_ids", "responsible_ids", "engineer_ids")

# Asset statuses CMMS uses (for the status filter dropdown).
_ASSET_STATUSES = ["в експлуатації", "на складі", "у ремонті", "списаний", "резерв"]


def _absolutize_photo(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = (getattr(settings, "CMMS_PUBLIC_URL", "") or "").rstrip("/")
    return f"{base}{url}" if url.startswith("/") else f"{base}/{url}"


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
        params.setdefault("page", 1)
        params.setdefault("page_size", 30)

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
            item["photo_url"] = _absolutize_photo((primary or {}).get("thumbnail_url") or (primary or {}).get("url"))
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
            return Response(
                {
                    "statuses": _ASSET_STATUSES,
                    "asset_types": cmms_client.list_asset_types(),
                    "categories": cmms_client.list_categories(),
                    "locations": cmms_client.list_locations(),
                    "departments": cmms_client.list_departments(),
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
