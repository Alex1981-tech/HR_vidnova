from __future__ import annotations

import hmac
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuthAuditEvent, EmployeeTelegramLink, TelegramLoginCode
from .services import (
    PhoneMatchStatus,
    ensure_employee_user,
    find_employee_by_phone,
    generate_login_code,
    hash_login_code,
    login_code_matches,
    normalize_phone,
)
from .telegram import TelegramSendError, send_login_code


def _client_ip(request) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip() or None
    return request.META.get("REMOTE_ADDR")


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _required_int(value: object) -> int | None:
    parsed = _optional_int(value)
    return parsed if parsed is not None else None


def _bot_secret_is_valid(request) -> bool:
    expected = settings.HR_BOT_API_SECRET
    provided = request.headers.get("X-Bot-Api-Secret", "")
    authorization = request.headers.get("Authorization", "")
    if not provided and authorization.startswith("Bearer "):
        provided = authorization.removeprefix("Bearer ").strip()
    return bool(expected and provided and hmac.compare_digest(provided, expected))


def _audit(
    request,
    *,
    event: str,
    result: str,
    employee=None,
    user=None,
    telegram_link=None,
    phone_normalized: str = "",
    telegram_chat_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    AuthAuditEvent.objects.create(
        employee=employee,
        user=user or (getattr(employee, "user", None) if employee else None),
        telegram_link=telegram_link,
        event=event,
        result=result,
        phone_normalized=phone_normalized,
        telegram_chat_id=telegram_chat_id,
        ip_address=_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
        metadata=metadata or {},
    )


def _neutral_code_response() -> Response:
    return Response({"status": "code_sent"})


def _rate_limit_key(phone_normalized: str, ip_address: str | None) -> str:
    ip_part = ip_address or "unknown"
    return f"hr_login_code_request:{phone_normalized}:{ip_part}"


def _is_rate_limited(phone_normalized: str, ip_address: str | None) -> bool:
    limit = settings.HR_LOGIN_CODE_REQUEST_LIMIT_PER_MINUTE
    if limit <= 0:
        return False
    key = _rate_limit_key(phone_normalized, ip_address)
    current = cache.get(key, 0)
    if current >= limit:
        return True
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, 60)
    else:
        cache.touch(key, 60)
    return False


def _employee_payload(employee):
    return {
        "id": employee.id,
        "full_name": employee.full_name,
        "status": employee.status,
    }


def _user_payload(user):
    return {
        "id": user.id,
        "username": user.get_username(),
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


class BotLinkByPhoneView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        phone = request.data.get("phone", "")
        phone_normalized = normalize_phone(phone)
        telegram_chat_id = _required_int(request.data.get("telegram_chat_id") or request.data.get("chat_id"))

        if not _bot_secret_is_valid(request):
            _audit(
                request,
                event=AuthAuditEvent.Event.ACCESS_DENIED,
                result=AuthAuditEvent.Result.DENIED,
                phone_normalized=phone_normalized,
                telegram_chat_id=telegram_chat_id,
                metadata={"reason": "invalid_bot_secret"},
            )
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        if not phone_normalized or telegram_chat_id is None:
            _audit(
                request,
                event=AuthAuditEvent.Event.TELEGRAM_LINK_REQUESTED,
                result=AuthAuditEvent.Result.FAILED,
                phone_normalized=phone_normalized,
                telegram_chat_id=telegram_chat_id,
                metadata={"reason": "invalid_payload"},
            )
            return Response({"detail": "phone and telegram_chat_id are required"}, status=status.HTTP_400_BAD_REQUEST)

        telegram_user_id = _optional_int(request.data.get("telegram_user_id"))
        telegram_username = str(request.data.get("telegram_username") or "").lstrip("@")[:160]
        match = find_employee_by_phone(phone)

        if match.status == PhoneMatchStatus.NOT_FOUND:
            _audit(
                request,
                event=AuthAuditEvent.Event.TELEGRAM_LINK_REQUESTED,
                result=AuthAuditEvent.Result.NOT_FOUND,
                phone_normalized=phone_normalized,
                telegram_chat_id=telegram_chat_id,
                metadata={"match_status": match.status},
            )
            return Response({"status": "not_found"}, status=status.HTTP_404_NOT_FOUND)
        if match.status == PhoneMatchStatus.CONFLICT:
            _audit(
                request,
                event=AuthAuditEvent.Event.TELEGRAM_LINK_REQUESTED,
                result=AuthAuditEvent.Result.CONFLICT,
                phone_normalized=phone_normalized,
                telegram_chat_id=telegram_chat_id,
                metadata={"match_status": match.status, "matches_count": match.matches_count},
            )
            return Response({"status": "conflict"}, status=status.HTTP_409_CONFLICT)
        if match.status != PhoneMatchStatus.MATCHED or match.employee is None:
            _audit(
                request,
                event=AuthAuditEvent.Event.TELEGRAM_LINK_REQUESTED,
                result=AuthAuditEvent.Result.DENIED,
                phone_normalized=phone_normalized,
                telegram_chat_id=telegram_chat_id,
                metadata={"match_status": match.status},
            )
            return Response({"status": "denied"}, status=status.HTTP_403_FORBIDDEN)

        employee = match.employee
        with transaction.atomic():
            conflicting_link = (
                EmployeeTelegramLink.objects.select_for_update()
                .filter(telegram_chat_id=telegram_chat_id, is_active=True)
                .exclude(employee=employee)
                .first()
            )
            if conflicting_link:
                _audit(
                    request,
                    event=AuthAuditEvent.Event.TELEGRAM_LINK_REQUESTED,
                    result=AuthAuditEvent.Result.CONFLICT,
                    phone_normalized=match.phone_normalized,
                    telegram_chat_id=telegram_chat_id,
                    metadata={"reason": "telegram_chat_id_already_linked"},
                )
                return Response({"status": "conflict"}, status=status.HTTP_409_CONFLICT)

            now = timezone.now()
            link, created = EmployeeTelegramLink.objects.select_for_update().get_or_create(
                employee=employee,
                defaults={
                    "telegram_chat_id": telegram_chat_id,
                    "telegram_user_id": telegram_user_id,
                    "telegram_username": telegram_username,
                    "phone_normalized": match.phone_normalized,
                    "linked_at": now,
                    "last_seen_at": now,
                },
            )
            if not created:
                relinked = not link.is_active
                link.telegram_chat_id = telegram_chat_id
                link.telegram_user_id = telegram_user_id
                link.telegram_username = telegram_username
                link.phone_normalized = match.phone_normalized
                link.is_active = True
                link.last_seen_at = now
                if relinked:
                    link.linked_at = now
                link.save(
                    update_fields=[
                        "telegram_chat_id",
                        "telegram_user_id",
                        "telegram_username",
                        "phone_normalized",
                        "is_active",
                        "linked_at",
                        "last_seen_at",
                        "updated_at",
                    ]
                )

            _audit(
                request,
                event=AuthAuditEvent.Event.TELEGRAM_LINKED,
                result=AuthAuditEvent.Result.OK,
                employee=employee,
                telegram_link=link,
                phone_normalized=match.phone_normalized,
                telegram_chat_id=telegram_chat_id,
                metadata={"created": created},
            )

        return Response({"status": "ok", "username": employee.full_name or employee.email or f"employee-{employee.pk}"})


class RequestLoginCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw_phone = request.data.get("phone", "")
        phone_normalized = normalize_phone(raw_phone)
        if not phone_normalized:
            return Response({"detail": "phone is required"}, status=status.HTTP_400_BAD_REQUEST)

        ip_address = _client_ip(request)
        if _is_rate_limited(phone_normalized, ip_address):
            _audit(
                request,
                event=AuthAuditEvent.Event.LOGIN_CODE_REQUESTED,
                result=AuthAuditEvent.Result.LOCKED,
                phone_normalized=phone_normalized,
                metadata={"reason": "rate_limited"},
            )
            return Response({"detail": "Too many requests"}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        match = find_employee_by_phone(raw_phone)
        if match.status != PhoneMatchStatus.MATCHED or match.employee is None:
            _audit(
                request,
                event=AuthAuditEvent.Event.LOGIN_CODE_REQUESTED,
                result=AuthAuditEvent.Result.DENIED,
                phone_normalized=phone_normalized,
                metadata={"match_status": match.status},
            )
            return _neutral_code_response()

        employee = match.employee
        link = getattr(employee, "telegram_link", None)
        if not link or not link.is_active:
            _audit(
                request,
                event=AuthAuditEvent.Event.LOGIN_CODE_REQUESTED,
                result=AuthAuditEvent.Result.DENIED,
                employee=employee,
                phone_normalized=match.phone_normalized,
                metadata={"reason": "no_active_telegram_link"},
            )
            return _neutral_code_response()

        code = generate_login_code()
        now = timezone.now()
        expires_at = now + timedelta(seconds=settings.HR_LOGIN_CODE_TTL_SECONDS)
        with transaction.atomic():
            TelegramLoginCode.objects.filter(
                employee=employee,
                consumed_at__isnull=True,
                expires_at__gt=now,
            ).update(consumed_at=now)
            login_code = TelegramLoginCode.objects.create(
                employee=employee,
                telegram_link=link,
                code_hash=hash_login_code(code),
                expires_at=expires_at,
                request_ip=ip_address,
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
            )

        try:
            send_login_code(link.telegram_chat_id, code, employee)
        except TelegramSendError:
            login_code.consumed_at = timezone.now()
            login_code.save(update_fields=["consumed_at", "updated_at"])
            _audit(
                request,
                event=AuthAuditEvent.Event.LOGIN_CODE_SENT,
                result=AuthAuditEvent.Result.FAILED,
                employee=employee,
                telegram_link=link,
                phone_normalized=match.phone_normalized,
                telegram_chat_id=link.telegram_chat_id,
                metadata={"reason": "telegram_send_failed"},
            )
            return _neutral_code_response()

        link.last_seen_at = timezone.now()
        link.save(update_fields=["last_seen_at", "updated_at"])
        _audit(
            request,
            event=AuthAuditEvent.Event.LOGIN_CODE_SENT,
            result=AuthAuditEvent.Result.OK,
            employee=employee,
            telegram_link=link,
            phone_normalized=match.phone_normalized,
            telegram_chat_id=link.telegram_chat_id,
            metadata={"expires_at": expires_at.isoformat()},
        )
        return _neutral_code_response()


class VerifyLoginCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        raw_phone = request.data.get("phone", "")
        code = str(request.data.get("code") or "").strip()
        phone_normalized = normalize_phone(raw_phone)
        if not phone_normalized or not code:
            return Response({"detail": "phone and code are required"}, status=status.HTTP_400_BAD_REQUEST)

        match = find_employee_by_phone(raw_phone)
        if match.status != PhoneMatchStatus.MATCHED or match.employee is None:
            _audit(
                request,
                event=AuthAuditEvent.Event.LOGIN_FAILED,
                result=AuthAuditEvent.Result.DENIED,
                phone_normalized=phone_normalized,
                metadata={"match_status": match.status},
            )
            return Response({"detail": "Invalid code"}, status=status.HTTP_401_UNAUTHORIZED)

        employee = match.employee
        now = timezone.now()
        max_attempts = settings.HR_LOGIN_CODE_MAX_ATTEMPTS
        with transaction.atomic():
            login_code = (
                TelegramLoginCode.objects.select_for_update(of=("self",))
                .select_related("telegram_link")
                .filter(employee=employee, consumed_at__isnull=True)
                .order_by("-created_at")
                .first()
            )
            if login_code is None:
                _audit(
                    request,
                    event=AuthAuditEvent.Event.LOGIN_FAILED,
                    result=AuthAuditEvent.Result.FAILED,
                    employee=employee,
                    phone_normalized=match.phone_normalized,
                    metadata={"reason": "code_not_found"},
                )
                return Response({"detail": "Invalid code"}, status=status.HTTP_400_BAD_REQUEST)
            if login_code.expires_at <= now:
                _audit(
                    request,
                    event=AuthAuditEvent.Event.LOGIN_FAILED,
                    result=AuthAuditEvent.Result.FAILED,
                    employee=employee,
                    telegram_link=login_code.telegram_link,
                    phone_normalized=match.phone_normalized,
                    metadata={"reason": "code_expired"},
                )
                return Response({"detail": "Code expired"}, status=status.HTTP_400_BAD_REQUEST)
            if login_code.failed_attempts >= max_attempts:
                _audit(
                    request,
                    event=AuthAuditEvent.Event.LOGIN_FAILED,
                    result=AuthAuditEvent.Result.LOCKED,
                    employee=employee,
                    telegram_link=login_code.telegram_link,
                    phone_normalized=match.phone_normalized,
                    metadata={"reason": "attempts_exceeded"},
                )
                return Response({"detail": "Too many attempts"}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            if not login_code_matches(code, login_code.code_hash):
                login_code.failed_attempts += 1
                login_code.save(update_fields=["failed_attempts", "updated_at"])
                remaining = max(0, max_attempts - login_code.failed_attempts)
                _audit(
                    request,
                    event=AuthAuditEvent.Event.LOGIN_FAILED,
                    result=AuthAuditEvent.Result.DENIED,
                    employee=employee,
                    telegram_link=login_code.telegram_link,
                    phone_normalized=match.phone_normalized,
                    metadata={"reason": "wrong_code", "attempts_remaining": remaining},
                )
                return Response(
                    {"detail": "Invalid code", "attempts_remaining": remaining},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if not login_code.telegram_link or not login_code.telegram_link.is_active:
                _audit(
                    request,
                    event=AuthAuditEvent.Event.LOGIN_FAILED,
                    result=AuthAuditEvent.Result.DENIED,
                    employee=employee,
                    telegram_link=login_code.telegram_link,
                    phone_normalized=match.phone_normalized,
                    metadata={"reason": "telegram_link_inactive"},
                )
                return Response({"detail": "Invalid code"}, status=status.HTTP_401_UNAUTHORIZED)

            user = ensure_employee_user(employee)
            if not user.is_active:
                _audit(
                    request,
                    event=AuthAuditEvent.Event.LOGIN_FAILED,
                    result=AuthAuditEvent.Result.DENIED,
                    employee=employee,
                    user=user,
                    telegram_link=login_code.telegram_link,
                    phone_normalized=match.phone_normalized,
                    metadata={"reason": "user_inactive"},
                )
                return Response({"detail": "Invalid code"}, status=status.HTTP_401_UNAUTHORIZED)

            login_code.consumed_at = now
            login_code.save(update_fields=["consumed_at", "updated_at"])

        django_login(request, user)
        _audit(
            request,
            event=AuthAuditEvent.Event.LOGIN_SUCCEEDED,
            result=AuthAuditEvent.Result.OK,
            employee=employee,
            user=user,
            telegram_link=login_code.telegram_link,
            phone_normalized=match.phone_normalized,
            telegram_chat_id=login_code.telegram_link.telegram_chat_id,
        )
        return Response({"status": "ok", "user": _user_payload(user), "employee": _employee_payload(employee)})


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        user = request.user if request.user.is_authenticated else None
        employee = None
        if user is not None:
            employee = getattr(user, "employee_profile", None)
            _audit(
                request,
                event=AuthAuditEvent.Event.LOGOUT,
                result=AuthAuditEvent.Result.OK,
                employee=employee,
                user=user,
            )
        django_logout(request)
        return Response({"status": "ok"})
