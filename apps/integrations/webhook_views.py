"""Приймач вебхуків PeopleForce.

Вебхук слугує тригером: ми лише валідуємо підпис, логуємо подію і запускаємо
(із дебаунсом) наявний light-sync importer-а. Так дані застосовує перевірений
мапінг, а ми не залежимо від точного формату payload PeopleForce.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.core.cache import cache
from django.utils.encoding import force_bytes
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PeopleForceWebhookEvent

logger = logging.getLogger(__name__)

# Заголовки, в яких PeopleForce/проксі можуть передати підпис (пробуємо по черзі).
SIGNATURE_HEADERS = ("X-PeopleForce-Signature", "X-Signature", "X-Hub-Signature-256", "X-Webhook-Signature")
# Дебаунс: один light-sync максимум раз на стільки секунд на сплеск вебхуків.
DEBOUNCE_KEY = "peopleforce:webhook:debounce"
DEBOUNCE_TTL = 120
DEBOUNCE_COUNTDOWN = 90


def _verify_signature(raw_body: bytes, headers) -> bool:
    secret = (getattr(settings, "PEOPLEFORCE_WEBHOOK_SECRET", "") or "").strip()
    if not secret:
        return False
    provided = ""
    for name in SIGNATURE_HEADERS:
        value = headers.get(name, "")
        if value:
            provided = value.strip()
            break
    if not provided:
        return False
    provided = provided.split("=", 1)[1].strip() if provided.lower().startswith("sha256=") else provided
    digest = hmac.new(force_bytes(secret), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, provided)


def _extract_topic(payload) -> tuple[str, str]:
    if not isinstance(payload, dict):
        return "", ""
    topic = payload.get("action") or payload.get("event") or payload.get("topic") or payload.get("type") or ""
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    event_id = str(payload.get("id") or data.get("id") or "")
    return str(topic), event_id


class PeopleForceWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        raw_body = request.body or b""
        try:
            payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
        except (ValueError, UnicodeDecodeError):
            payload = {}

        signature_valid = _verify_signature(raw_body, request.headers)
        topic, event_id = _extract_topic(payload)

        event = PeopleForceWebhookEvent.objects.create(
            topic=topic,
            event_id=event_id,
            payload=payload if isinstance(payload, (dict, list)) else {},
            # Зберігаємо всі заголовки (без cookie) — щоб звірити реальну схему підпису PeopleForce.
            headers={k: v for k, v in request.headers.items() if k.lower() != "cookie"},
            signature_valid=signature_valid,
            remote_addr=(request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR", ""))[:80],
        )

        # Строгий режим (за прапорцем): відхиляти невалідний підпис. За замовчуванням —
        # дорадчий: обробляємо завжди (вебхук лише тригерить синк, дані тягне importer із PF).
        secret_configured = bool((getattr(settings, "PEOPLEFORCE_WEBHOOK_SECRET", "") or "").strip())
        enforce = bool(getattr(settings, "PEOPLEFORCE_WEBHOOK_ENFORCE", False))
        if enforce and secret_configured and not signature_valid:
            event.status = PeopleForceWebhookEvent.Status.SKIPPED
            event.error = "Invalid signature"
            event.save(update_fields=["status", "error", "updated_at"])
            logger.warning("PeopleForce webhook rejected (bad signature): topic=%s", topic)
            return Response({"status": "invalid_signature"}, status=status.HTTP_200_OK)

        # Дебаунс-тригер light-sync (коалесить сплеск подій в один синк).
        queued = False
        if cache.add(DEBOUNCE_KEY, "1", DEBOUNCE_TTL):
            try:
                from .tasks import sync_peopleforce_light

                sync_peopleforce_light.apply_async(countdown=DEBOUNCE_COUNTDOWN)
                queued = True
            except Exception as exc:  # noqa: BLE001 — не валимо вебхук через помилку черги
                logger.warning("PeopleForce webhook: failed to enqueue light sync: %s", exc)

        event.status = PeopleForceWebhookEvent.Status.QUEUED if queued else PeopleForceWebhookEvent.Status.RECEIVED
        event.save(update_fields=["status", "updated_at"])
        return Response({"status": "ok", "queued": queued}, status=status.HTTP_200_OK)
