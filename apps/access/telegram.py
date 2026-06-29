from __future__ import annotations

import json
import urllib.parse
import urllib.request
from html import escape

from django.conf import settings

from apps.employees.models import Employee


class TelegramSendError(RuntimeError):
    pass


def build_login_code_text(code: str, employee: Employee) -> str:
    employee_name = escape(employee.full_name or "співробітник")
    safe_code = escape(code)
    hr_url = "https://hr.vidnova.app/"
    return (
        "Ви входите в систему HR Vidnova:\n"
        f'<a href="{hr_url}">{hr_url}</a>\n\n'
        "Код входу:\n"
        f"<code>{safe_code}</code>\n\n"
        f"{employee_name}\n"
        "Дійсний 5 хвилин. Нікому не передавайте цей код."
    )


def send_message(telegram_chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    """Універсальне надсилання HTML-повідомлення через сконфігурований бекенд."""
    backend = settings.HR_TELEGRAM_SENDER_BACKEND
    if backend == "telegram_bot_api":
        _send_via_telegram_bot_api(telegram_chat_id, text, reply_markup=reply_markup)
        return
    raise TelegramSendError("Unsupported Telegram sender backend")


def send_login_code(telegram_chat_id: int, code: str, employee: Employee) -> None:
    backend = settings.HR_TELEGRAM_SENDER_BACKEND
    if backend == "telegram_bot_api":
        _send_via_telegram_bot_api(telegram_chat_id, build_login_code_text(code, employee))
        return
    raise TelegramSendError("Unsupported Telegram sender backend")


def _send_via_telegram_bot_api(telegram_chat_id: int, text: str, reply_markup: dict | None = None) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise TelegramSendError("TELEGRAM_BOT_TOKEN is not configured")

    payload = {
        "chat_id": telegram_chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    data = urllib.parse.urlencode(payload).encode()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        request = urllib.request.Request(url, data=data, method="POST")
        urllib.request.urlopen(request, timeout=10)
    except Exception as exc:  # noqa: BLE001
        raise TelegramSendError("Telegram sendMessage failed") from exc
