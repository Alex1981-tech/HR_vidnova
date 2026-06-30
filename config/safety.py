"""Production safety gate (P0).

Чистая, тестируемая проверка небезопасной production-конфигурации. Используется
и в settings.py (hard fail на старте), и в unit-тестах. Активна только когда
ENVIRONMENT=production, чтобы dev оставался удобным.
"""

from __future__ import annotations

DEV_SECRET_FALLBACK = "dev-insecure-change-me"


def production_safety_problems(
    *,
    environment: str,
    debug: bool,
    secret_key: str,
    public_read: bool,
    public_write: bool,
    dev_secret_fallback: str = DEV_SECRET_FALLBACK,
) -> list[str]:
    """Возвращает список проблем небезопасного production-конфига (пусто = ок).

    Срабатывает только при environment == "production".
    """
    if (environment or "").strip().lower() != "production":
        return []
    problems: list[str] = []
    if debug:
        problems.append("DEBUG must be False in production")
    if not secret_key or secret_key == dev_secret_fallback:
        problems.append("SECRET_KEY must be set explicitly (dev fallback is not allowed in production)")
    if public_read:
        problems.append("HR_PUBLIC_READ_API must be False in production")
    if public_write:
        problems.append("HR_PUBLIC_WRITE_API must be False in production")
    return problems
