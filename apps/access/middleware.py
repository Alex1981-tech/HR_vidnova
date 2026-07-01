"""Примусовий ліміт сесії: перелогін через N секунд від входу, з логуванням."""

import time

from django.conf import settings
from django.contrib.auth import logout as django_logout

from .models import AuthAuditEvent


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class SessionMaxAgeMiddleware:
    """Жорсткий максимальний вік сесії від моменту входу (`login_at`).

    Навіть якщо сесія безперервно активна — після ліміту користувача розлогінює
    й фіксує подію `session_expired` (видно в системному журналі).
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.max_age = int(getattr(settings, "SESSION_MAX_AGE_SECONDS", 3600) or 0)

    def __call__(self, request):
        user = getattr(request, "user", None)
        if self.max_age and user is not None and user.is_authenticated:
            login_at = request.session.get("login_at")
            if login_at and (time.time() - float(login_at)) > self.max_age:
                try:
                    AuthAuditEvent.objects.create(
                        employee=getattr(user, "employee_profile", None),
                        user=user,
                        event=AuthAuditEvent.Event.SESSION_EXPIRED,
                        result=AuthAuditEvent.Result.OK,
                        ip_address=_client_ip(request),
                        user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
                        metadata={"reason": "max_age", "max_age_seconds": self.max_age},
                    )
                except Exception:
                    pass
                django_logout(request)
        return self.get_response(request)
