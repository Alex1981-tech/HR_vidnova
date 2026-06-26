from __future__ import annotations

import mimetypes
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.text import slugify

from .models import Employee


MAX_AVATAR_BYTES = 8 * 1024 * 1024
AVATAR_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


@dataclass(frozen=True, slots=True)
class AvatarDownloadResult:
    status: str
    detail: str = ""


def download_employee_avatar(employee: Employee, *, force: bool = False, timeout: int = 30) -> AvatarDownloadResult:
    source_url = (employee.avatar_url or "").strip()
    if not source_url:
        return _store_avatar_error(employee, "", "no_source_url")
    if not source_url.startswith(("http://", "https://")):
        return _store_avatar_error(employee, source_url, "unsupported_source_url")
    if is_default_peopleforce_avatar(source_url):
        if employee.avatar_file:
            employee.avatar_file.delete(save=False)
        employee.avatar_file = ""
        employee.avatar_source_url = source_url
        employee.avatar_downloaded_at = None
        employee.avatar_download_error = "default_avatar"
        employee.save(update_fields=["avatar_file", "avatar_source_url", "avatar_downloaded_at", "avatar_download_error", "updated_at"])
        return AvatarDownloadResult("skipped", "default_avatar")
    if employee.avatar_file and employee.avatar_source_url == source_url and not force:
        return AvatarDownloadResult("skipped")

    try:
        response = _fetch_avatar(source_url, timeout=timeout)
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type not in AVATAR_CONTENT_TYPES:
            return _store_avatar_error(employee, source_url, f"unsupported_content_type:{content_type or 'unknown'}")
        content = response.content
        if not content:
            return _store_avatar_error(employee, source_url, "empty_response")
        if len(content) > MAX_AVATAR_BYTES:
            return _store_avatar_error(employee, source_url, "file_too_large")

        filename = employee_avatar_filename(employee, source_url, content_type)
        if employee.avatar_file and force:
            employee.avatar_file.delete(save=False)
        employee.avatar_file.save(filename, ContentFile(content), save=False)
        employee.avatar_source_url = source_url
        employee.avatar_downloaded_at = timezone.now()
        employee.avatar_download_error = ""
        employee.save(update_fields=["avatar_file", "avatar_source_url", "avatar_downloaded_at", "avatar_download_error", "updated_at"])
    except Exception as exc:
        return _store_avatar_error(employee, source_url, safe_avatar_error(exc))

    return AvatarDownloadResult("downloaded")


def _fetch_avatar(source_url: str, *, timeout: int) -> httpx.Response:
    headers = {"Accept": "image/avif,image/webp,image/png,image/jpeg,image/gif,image/*;q=0.8,*/*;q=0.5"}
    parsed = urlparse(source_url)
    if parsed.netloc.endswith("peopleforce.io") and settings.PEOPLEFORCE_API_KEY:
        headers["X-API-KEY"] = settings.PEOPLEFORCE_API_KEY
    if parsed.netloc.endswith("peopleforce.io") and getattr(settings, "PEOPLEFORCE_WEB_COOKIE", ""):
        headers["Cookie"] = settings.PEOPLEFORCE_WEB_COOKIE
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        response = client.get(source_url)
        response.raise_for_status()
        return response


def employee_avatar_filename(employee: Employee, source_url: str, content_type: str) -> str:
    ext = AVATAR_CONTENT_TYPES.get(content_type) or Path(urlparse(source_url).path).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
        guessed = mimetypes.guess_extension(content_type)
        ext = guessed if guessed in {".jpg", ".jpeg", ".png", ".gif", ".webp"} else ".jpg"
    stem = slugify(employee.full_name, allow_unicode=True) or f"employee-{employee.pk}"
    return f"{employee.pk}-{stem}{ext}"


def _store_avatar_error(employee: Employee, source_url: str, detail: str) -> AvatarDownloadResult:
    employee.avatar_source_url = source_url
    employee.avatar_download_error = detail[:1000]
    employee.save(update_fields=["avatar_source_url", "avatar_download_error", "updated_at"])
    return AvatarDownloadResult("error", detail[:1000])


def safe_avatar_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        return f"http_status_{exc.response.status_code}"
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.RequestError):
        return exc.__class__.__name__
    return exc.__class__.__name__


def is_default_peopleforce_avatar(source_url: str) -> bool:
    return "default_employee_thumbnail" in source_url or "default_employee_avatar" in source_url
