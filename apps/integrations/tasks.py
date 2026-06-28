"""Періодичний імпорт даних з PeopleForce (Celery beat).

Легкий нічний синк тримає свіжими людей/дані-людей/відсутності/посещаемість за
останні дні; повний тижневий синк додатково тягне timesheet за весь період,
документи та базу знань із завантаженням файлів.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from apps.integrations.peopleforce.importer import PeopleForceLegacyImporter

logger = logging.getLogger(__name__)

# Свіже вікно посещаемості (timesheet) для легкого нічного синку.
LIGHT_TIMESHEET_DAYS = 14
# Захист від накладання запусків (light/full).
SYNC_LOCK_KEY = "peopleforce:sync:lock"
SYNC_LOCK_TTL = 60 * 60 * 3  # 3 год


def _run_import(label: str, **kwargs) -> dict | None:
    if not settings.PEOPLEFORCE_API_KEY:
        logger.warning("PeopleForce %s sync skipped: PEOPLEFORCE_API_KEY is not configured.", label)
        return None
    # Неблокуючий лок: якщо вже йде синк — пропускаємо цей запуск.
    if not cache.add(SYNC_LOCK_KEY, label, SYNC_LOCK_TTL):
        logger.warning("PeopleForce %s sync skipped: another sync (%s) is running.", label, cache.get(SYNC_LOCK_KEY))
        return None
    try:
        result = PeopleForceLegacyImporter(**kwargs).sync()
        logger.info("PeopleForce %s sync run #%s: %s, issues=%s", label, result.run_id, result.status, result.issues_count)
        return {"run_id": result.run_id, "status": result.status, "issues": result.issues_count, "counters": result.counters}
    except ImproperlyConfigured as exc:
        logger.warning("PeopleForce %s sync skipped: %s", label, exc)
        return None
    finally:
        cache.delete(SYNC_LOCK_KEY)


@shared_task(name="integrations.sync_peopleforce_light", time_limit=60 * 60, soft_time_limit=60 * 55)
def sync_peopleforce_light() -> dict | None:
    """Нічний легкий синк: люди + дані-людей + відсутності + свіжа посещаемість."""
    start = timezone.localdate() - timedelta(days=LIGHT_TIMESHEET_DAYS)
    return _run_import(
        "light",
        skip_per_employee=False,
        skip_leave=False,
        skip_knowledge=True,
        skip_documents=True,
        skip_timesheet=False,
        download_document_files=False,
        download_knowledge_attachments=False,
        timesheet_start=start,
        timesheet_end=timezone.localdate(),
    )


@shared_task(name="integrations.sync_peopleforce_full", time_limit=60 * 60 * 3, soft_time_limit=60 * 60 * 3 - 300)
def sync_peopleforce_full() -> dict | None:
    """Тижневий повний синк: усе, включно з timesheet/документами/knowledge + файли."""
    return _run_import(
        "full",
        skip_per_employee=False,
        skip_leave=False,
        skip_knowledge=False,
        skip_documents=False,
        skip_timesheet=False,
        download_document_files=True,
        download_knowledge_attachments=True,
    )
