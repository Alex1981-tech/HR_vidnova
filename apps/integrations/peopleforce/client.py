from __future__ import annotations

import time
from typing import Any

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class PeopleForceClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
        min_interval_seconds: float = 0.22,
    ) -> None:
        self.api_key = api_key or settings.PEOPLEFORCE_API_KEY
        if not self.api_key:
            raise ImproperlyConfigured("PEOPLEFORCE_API_KEY is not configured.")
        self.base_url = (base_url or settings.PEOPLEFORCE_API_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.PEOPLEFORCE_TIMEOUT_SECONDS
        self.min_interval_seconds = min_interval_seconds
        self._last_request_at = 0.0

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._throttle()
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"X-API-KEY": self.api_key, "Accept": "application/json"}
        with httpx.Client(timeout=self.timeout, headers=headers) as client:
            for attempt in range(1, 4):
                response = client.get(url, params=params)
                if response.status_code == 429 and attempt < 3:
                    retry_after = parse_retry_after(response.headers.get("Retry-After"))
                    time.sleep(retry_after or attempt * 2)
                    continue
                response.raise_for_status()
                return response.json()
        raise RuntimeError(f"PeopleForce request failed after retries: {path}")

    def iter_pages(self, path: str, params: dict[str, Any] | None = None):
        page = 1
        while True:
            payload = self.get(path, {**(params or {}), "page": page})
            yield payload
            metadata = payload.get("metadata") or {}
            pagination = metadata.get("pagination") or {}
            pages = pagination.get("pages") or metadata.get("pages") or 1
            if page >= int(pages):
                break
            page += 1

    def list_all(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for page in self.iter_pages(path, params=params):
            data = page.get("data") or []
            if isinstance(data, list):
                rows.extend([item for item in data if isinstance(item, dict)])
        return rows

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_request_at = time.monotonic()


def parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
