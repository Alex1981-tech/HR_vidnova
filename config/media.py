"""Защищённая раздача media (P2).

Файлы под MEDIA_ROOT (аватары, сертификаты, документы, knowledge) — это PII и
не должны быть доступны анонимно. Раздаём их через Django-view с проверкой
аутентификации.

В production (HR_MEDIA_X_ACCEL=True) view только авторизует запрос и отдаёт
байты через nginx `X-Accel-Redirect` (internal location /protected-media/) —
без копирования файла через Python. В dev (FileResponse) — отдаёт файл напрямую.
"""

from __future__ import annotations

import mimetypes
from urllib.parse import quote

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse, Http404, HttpResponse, HttpResponseForbidden
from django.utils._os import safe_join

# Внутренняя (internal) nginx-локация, которая физически отдаёт файлы.
X_ACCEL_PREFIX = "/protected-media/"

# Некоторые типы не всегда есть в системной mimetypes-базе (важно для dev
# FileResponse, чтобы webp/avif рендерились inline).
for _ext, _ctype in (
    (".webp", "image/webp"),
    (".avif", "image/avif"),
    (".heic", "image/heic"),
):
    mimetypes.add_type(_ctype, _ext)


def _is_allowed(request) -> bool:
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return True
    # В dev (или при явно открытом public read API) разрешаем анонимный доступ,
    # чтобы не требовать логина локально. В production HR_PUBLIC_READ_API=False.
    return bool(getattr(settings, "HR_PUBLIC_READ_API", False))


def protected_media(request, path: str):
    if not _is_allowed(request):
        return HttpResponseForbidden("Authentication required")

    try:
        full_path = safe_join(str(settings.MEDIA_ROOT), path)
    except (SuspiciousFileOperation, ValueError):
        raise Http404("Not found")

    content_type, _ = mimetypes.guess_type(path)
    content_type = content_type or "application/octet-stream"

    if getattr(settings, "HR_MEDIA_X_ACCEL", False):
        response = HttpResponse(content_type=content_type)
        # quote оставляет '/' — путь внутри internal-локации.
        response["X-Accel-Redirect"] = X_ACCEL_PREFIX + quote(path)
        response["Cache-Control"] = "private, max-age=86400"
        return response

    try:
        handle = open(full_path, "rb")
    except (FileNotFoundError, IsADirectoryError, OSError):
        raise Http404("Not found")
    response = FileResponse(handle, content_type=content_type)
    response["Cache-Control"] = "private, max-age=86400"
    return response
