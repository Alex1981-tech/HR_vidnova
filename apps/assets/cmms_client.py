"""Thin client for the CMMS (vidnova-cmms FastAPI) asset API.

HR Vidnova is the employee master: when assigning an asset's responsible person
we map the HR employee onto a CMMS ``employees`` row (matched by PeopleForce id
or email, created on demand) and then PUT the asset's ``responsible_person_id``.
"""

from __future__ import annotations

import threading
import time

import httpx
from django.conf import settings


class CmmsError(Exception):
    pass


class CmmsClient:
    def __init__(self) -> None:
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        self._lock = threading.Lock()

    @property
    def base(self) -> str:
        return (getattr(settings, "CMMS_API_BASE_URL", "") or "").rstrip("/")

    def _login(self) -> str:
        if not self.base:
            raise CmmsError("CMMS_API_BASE_URL is not configured")
        resp = httpx.post(
            f"{self.base}/api/auth/login",
            json={
                "username": settings.CMMS_API_USERNAME,
                "password": settings.CMMS_API_PASSWORD,
            },
            timeout=settings.CMMS_API_TIMEOUT,
        )
        if resp.status_code != 200:
            raise CmmsError(f"CMMS login failed ({resp.status_code})")
        token = resp.json().get("access_token")
        if not token:
            raise CmmsError("CMMS login returned no token")
        self._token = token
        # CMMS tokens last ~hours; refresh proactively well before expiry.
        self._token_expires_at = time.time() + 50 * 60
        return token

    def _auth_header(self) -> dict[str, str]:
        with self._lock:
            if not self._token or time.time() > self._token_expires_at:
                self._login()
            return {"Authorization": f"Bearer {self._token}"}

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        url = f"{self.base}{path}"
        for attempt in (1, 2):
            resp = httpx.request(
                method,
                url,
                headers=self._auth_header(),
                timeout=settings.CMMS_API_TIMEOUT,
                **kwargs,
            )
            if resp.status_code == 401 and attempt == 1:
                with self._lock:
                    self._token = None  # force re-login and retry once
                continue
            if resp.status_code >= 400:
                raise CmmsError(f"CMMS {method} {path} -> {resp.status_code}: {resp.text[:200]}")
            return resp
        raise CmmsError(f"CMMS {method} {path} failed after re-auth")

    # ---- assets -----------------------------------------------------------
    def list_assets(self, params: dict | None = None) -> dict:
        return self._request("GET", "/api/assets/list", params=params or {}).json()

    def get_asset(self, asset_id: int) -> dict:
        return self._request("GET", f"/api/assets/{asset_id}").json()

    def get_asset_ownership_history(self, asset_id: int) -> list[dict]:
        # Таблиця історії володіння — CMMS збирає її з location/responsibility/engineer історій.
        return self._request("GET", f"/api/assets/{asset_id}/ownership-history").json()

    def set_asset_responsible(self, asset_id: int, cmms_employee_id: int | None) -> dict:
        # PUT is a partial update (exclude_unset) on the CMMS side and records
        # responsibility history, so sending only this field is safe.
        return self._request(
            "PUT",
            f"/api/assets/{asset_id}",
            json={"responsible_person_id": cmms_employee_id},
        ).json()

    def set_asset_engineer(self, asset_id: int, engineer_user_id: int | None) -> dict:
        # engineer_id → CMMS users; partial PUT records engineer history on the CMMS side.
        return self._request(
            "PUT",
            f"/api/assets/{asset_id}",
            json={"engineer_id": engineer_user_id},
        ).json()

    # ---- filter options ---------------------------------------------------
    def list_categories(self) -> list[dict]:
        return self._request("GET", "/api/categories/").json()

    def list_locations(self) -> list[dict]:
        return self._request("GET", "/api/locations/").json()

    def list_departments(self) -> list[dict]:
        return self._request("GET", "/api/departments/").json()

    def list_asset_types(self) -> list[dict]:
        return self._request("GET", "/api/asset-types/").json()

    # ---- employees / users ------------------------------------------------
    def list_employees(self) -> list[dict]:
        data = self._request("GET", "/api/employees/").json()
        return data if isinstance(data, list) else data.get("items", [])

    def list_users(self) -> list[dict]:
        # Інженери активів — це CMMS users (не employees).
        data = self._request("GET", "/api/users/").json()
        return data if isinstance(data, list) else data.get("items", [])

    def create_employee(self, payload: dict) -> dict:
        return self._request("POST", "/api/employees/", json=payload).json()

    def find_employee_id(self, hr_employee) -> int | None:
        """Map an HR Employee onto an existing CMMS employee id without creating one."""
        peopleforce_id = None
        raw_pf = (getattr(hr_employee, "legacy_peopleforce_id", "") or "").strip()
        if raw_pf.isdigit():
            peopleforce_id = int(raw_pf)
        email = (getattr(hr_employee, "email", "") or getattr(hr_employee, "personal_email", "") or "").strip().lower()

        employees = self.list_employees()
        if peopleforce_id is not None:
            for emp in employees:
                if emp.get("peopleforce_id") == peopleforce_id:
                    return emp["id"]
        if email:
            for emp in employees:
                if (emp.get("email") or "").strip().lower() == email:
                    return emp["id"]
        return None

    def resolve_employee_id(self, hr_employee) -> int:
        """Map an HR Employee onto a CMMS employee id (find or create)."""
        found = self.find_employee_id(hr_employee)
        if found is not None:
            return found
        email = (getattr(hr_employee, "email", "") or getattr(hr_employee, "personal_email", "") or "").strip().lower()
        peopleforce_id = None
        raw_pf = (getattr(hr_employee, "legacy_peopleforce_id", "") or "").strip()
        if raw_pf.isdigit():
            peopleforce_id = int(raw_pf)
        position = getattr(getattr(hr_employee, "position", None), "name", None)
        department = getattr(getattr(hr_employee, "department", None), "name", None)
        created = self.create_employee(
            {
                "full_name": hr_employee.full_name,
                "email": email or None,
                "position": position,
                "department": department,
                "source": "hr",
                "peopleforce_id": peopleforce_id,
            }
        )
        return created["id"]


cmms_client = CmmsClient()
