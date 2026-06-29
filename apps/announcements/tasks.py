"""Фонова розсилка оголошень у Telegram через спільного бота."""

from __future__ import annotations

import logging
import re
import time
from html import unescape

from celery import shared_task
from django.utils import timezone

from apps.access.models import EmployeeTelegramLink
from apps.access.telegram import TelegramSendError, send_message

from .audience import resolve_audience
from .models import Announcement

logger = logging.getLogger(__name__)

# Telegram sendMessage HTML підтримує лише обмежений набір тегів.
_TG_KEEP_TAGS = ("b", "strong", "i", "em", "u", "s", "code", "pre", "a")


def html_to_telegram(html: str, title: str) -> str:
    """Конвертує tiptap-HTML у безпечний для Telegram HTML (обмежений набір тегів)."""
    text = html or ""
    # Блокові межі → переноси рядків.
    text = re.sub(r"(?i)</p\s*>", "\n", text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</h[1-6]\s*>", "\n", text)
    text = re.sub(r"(?i)<li[^>]*>", "• ", text)
    text = re.sub(r"(?i)</li\s*>", "\n", text)
    # Нормалізуємо емфазу під TG-теги.
    text = re.sub(r"(?i)<strong[^>]*>", "<b>", text).replace("</strong>", "</b>")
    text = re.sub(r"(?i)<em[^>]*>", "<i>", text).replace("</em>", "</i>")
    # Зберігаємо href у посиланнях, прибираємо інші атрибути.
    text = re.sub(r'(?i)<a\s+[^>]*href="([^"]*)"[^>]*>', r'<a href="\1">', text)
    # Викидаємо всі інші теги, лишаючи дозволені.
    keep = "|".join(_TG_KEEP_TAGS)
    text = re.sub(rf"(?is)<(?!/?(?:{keep})\b)[^>]+>", "", text)
    text = unescape(re.sub(r"\n{3,}", "\n\n", text)).strip()

    safe_title = re.sub(r"(?is)<[^>]+>", "", title or "").strip()
    header = f"<b>📢 {safe_title}</b>" if safe_title else "<b>📢 Нове оголошення</b>"
    body = f"{header}\n\n{text}" if text else header
    return body[:4000]


def announcement_to_telegram(announcement: Announcement) -> str:
    if announcement.kind == Announcement.Kind.POLL:
        safe_title = re.sub(r"(?is)<[^>]+>", "", announcement.title or "").strip()
        header = f"<b>📊 Нове опитування: {safe_title}</b>" if safe_title else "<b>📊 Нове опитування</b>"
        options = [
            re.sub(r"(?is)<[^>]+>", "", str(option or "")).strip()
            for option in (announcement.poll_options or [])
        ]
        options_text = "\n".join(f"• {option}" for option in options if option)
        intro = "Голосування доступне в HR Vidnova."
        body = f"{header}\n\n{intro}\n\n{options_text}" if options_text else f"{header}\n\n{intro}"
        return body[:4000]
    return html_to_telegram(announcement.body_html, announcement.title)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def send_announcement_telegram(self, announcement_id: int) -> dict:
    try:
        announcement = Announcement.objects.get(pk=announcement_id)
    except Announcement.DoesNotExist:
        return {"error": "not_found"}

    if not announcement.notify_telegram:
        return {"skipped": "telegram_disabled"}

    audience = resolve_audience(announcement.audience_type, announcement.conditions)
    links = EmployeeTelegramLink.objects.filter(
        employee__in=audience, is_active=True
    ).exclude(telegram_chat_id=None)

    message = announcement_to_telegram(announcement)
    reply_markup = {"inline_keyboard": [[{"text": "Відкрити HR Vidnova", "url": "https://hr.vidnova.app/"}]]}
    sent = failed = 0
    for link in links.iterator():
        try:
            send_message(link.telegram_chat_id, message, reply_markup=reply_markup)
            sent += 1
        except TelegramSendError:
            failed += 1
            logger.warning("Announcement %s: TG send failed for chat %s", announcement_id, link.telegram_chat_id)
        time.sleep(0.05)  # лагідний throttle (~20 msg/s, нижче ліміту Telegram)

    Announcement.objects.filter(pk=announcement_id).update(
        tg_sent_count=sent, tg_failed_count=failed, tg_dispatched_at=timezone.now()
    )
    return {"sent": sent, "failed": failed}
