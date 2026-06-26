from __future__ import annotations

import hashlib
import ipaddress
import json
import math
from datetime import datetime, timezone as datetime_timezone
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.employees.models import Employee, ExternalEmployeeLink
from apps.skud.models import AttendancePeriod

from .models import PeopleForceCompatRequest, PeopleForceCompatTimesheetEntry


def _configured_api_key() -> str:
    return str(getattr(settings, "PEOPLEFORCE_COMPAT_API_KEY", "") or "").strip()


def _provided_api_key(request) -> str:
    api_key = request.headers.get("X-API-KEY", "").strip()
    if api_key:
        return api_key

    authorization = request.headers.get("Authorization", "").strip()
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def _query_params_to_dict(request) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in request.query_params:
        values = request.query_params.getlist(key)
        result[key] = values if len(values) > 1 else values[0]
    return result


def _request_payload(request) -> Any:
    if request.method == "GET":
        return {}
    data = request.data
    if data in (None, ""):
        return {}
    return data


def _payload_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _remote_addr(request) -> str | None:
    raw = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    raw = raw or request.META.get("REMOTE_ADDR", "").strip()
    if not raw:
        return None
    try:
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None


def _parse_datetime_value(value: Any) -> datetime:
    if value is None or value == "":
        raise ValueError("datetime value is required")

    if isinstance(value, (int, float)) or str(value).strip().lstrip("-").isdigit():
        timestamp = float(value)
        if abs(timestamp) > 9999999999:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp, tz=datetime_timezone.utc)

    parsed = parse_datetime(str(value))
    if parsed is None:
        raise ValueError(f"invalid datetime value: {value}")
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_default_timezone())
    return parsed.astimezone(datetime_timezone.utc)


def _entry_date(starts_at: datetime) -> datetime.date:
    return starts_at.astimezone(timezone.get_default_timezone()).date()


def _duration_minutes(starts_at: datetime, ends_at: datetime) -> int:
    return max(0, int(round((ends_at - starts_at).total_seconds() / 60)))


def _coerce_int(value: Any) -> int | str:
    text = str(value)
    if text.isdigit():
        return int(text)
    return text


def _employee_queryset() -> QuerySet[Employee]:
    return (
        Employee.objects.select_related("division", "department", "position")
        .exclude(status=Employee.Status.DISMISSED)
        .order_by("last_name", "first_name", "middle_name")
    )


def _find_employee_by_peopleforce_id(employee_id: Any) -> Employee | None:
    legacy_id = str(employee_id)
    employee = Employee.objects.filter(legacy_peopleforce_id=legacy_id).first()
    if employee:
        return employee

    link = (
        ExternalEmployeeLink.objects.select_related("employee")
        .filter(
            source=ExternalEmployeeLink.Source.PEOPLEFORCE_LEGACY,
            external_id=legacy_id,
            is_active=True,
        )
        .first()
    )
    return link.employee if link else None


def _employee_peopleforce_id(employee: Employee) -> int | str:
    if employee.legacy_peopleforce_id:
        return _coerce_int(employee.legacy_peopleforce_id)
    return employee.id


def _peopleforce_status(employee: Employee) -> str:
    if employee.status == Employee.Status.DISMISSED:
        return "deleted"
    if employee.peopleforce_status:
        return employee.peopleforce_status
    return "employed"


def _field_value(fields: dict[str, Any], key: str) -> Any:
    value = fields.get(key, "")
    if isinstance(value, dict):
        return value.get("value", "")
    return value


def _employee_payload(employee: Employee) -> dict[str, Any]:
    fields = employee.peopleforce_fields if isinstance(employee.peopleforce_fields, dict) else {}

    employee_number = employee.employee_number or _field_value(fields, "employee_number")
    mobile_number = employee.phone or _field_value(fields, "mobile_number")
    work_phone = employee.phone2 or _field_value(fields, "work_phone_number")

    return {
        "id": _employee_peopleforce_id(employee),
        "status": _peopleforce_status(employee),
        "full_name": employee.full_name,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "middle_name": employee.middle_name,
        "email": employee.email,
        "personal_email": employee.personal_email,
        "date_of_birth": employee.birth_date.isoformat() if employee.birth_date else None,
        "avatar_url": employee.avatar_url,
        "division": {"name": employee.division.name} if employee.division else {},
        "department": {"name": employee.department.name} if employee.department else {},
        "position": {"name": employee.position.name} if employee.position else {},
        "fields": {
            "employee_number": {"value": employee_number or ""},
            "mobile_number": {"value": mobile_number or ""},
            "work_phone_number": {"value": work_phone or ""},
        },
    }


def _period_type(comment: str) -> str:
    normalized = comment.lower()
    if "нічна" in normalized or "night" in normalized:
        return AttendancePeriod.PeriodType.NIGHT
    if "виправ" in normalized or "missing" in normalized:
        return AttendancePeriod.PeriodType.ERROR
    if comment:
        return AttendancePeriod.PeriodType.MANUAL
    return AttendancePeriod.PeriodType.REGULAR


def _serialize_timesheet_entry(entry: PeopleForceCompatTimesheetEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "legacy_peopleforce_entry_id": entry.legacy_peopleforce_entry_id or None,
        "employee_id": _coerce_int(entry.legacy_peopleforce_employee_id),
        "starts_at": int(entry.starts_at.timestamp()),
        "ends_at": int(entry.ends_at.timestamp()),
        "starts_on": entry.date.isoformat(),
        "ends_on": entry.ends_at.astimezone(timezone.get_default_timezone()).date().isoformat(),
        "minutes": entry.minutes,
        "status": entry.status,
        "type": entry.entry_type,
        "comment": entry.comment,
    }


class PeopleForceCompatAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def _auth_error(self, request) -> Response | None:
        expected = _configured_api_key()
        if not expected:
            return Response(
                {"error": "PeopleForce-compatible API key is not configured"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        provided = _provided_api_key(request)
        if not provided or not constant_time_compare(provided, expected):
            return Response({"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)
        return None

    def _create_request_log(self, request, payload: Any) -> PeopleForceCompatRequest:
        return PeopleForceCompatRequest.objects.create(
            method=request.method,
            path=request.path,
            query_params=_query_params_to_dict(request),
            request_payload=payload,
            payload_hash=_payload_hash({"query": _query_params_to_dict(request), "body": payload}),
            remote_addr=_remote_addr(request),
            user_agent=request.headers.get("User-Agent", "")[:300],
        )

    def _finalize_request_log(
        self,
        request_log: PeopleForceCompatRequest,
        *,
        status_code: int,
        response_payload: Any,
        processed_status: str = PeopleForceCompatRequest.ProcessedStatus.PROCESSED,
        error_message: str = "",
    ) -> None:
        request_log.status_code = status_code
        request_log.response_payload = response_payload
        request_log.processed_status = processed_status
        request_log.error_message = error_message
        request_log.save(
            update_fields=[
                "status_code",
                "response_payload",
                "processed_status",
                "error_message",
                "updated_at",
            ]
        )


class PeopleForceCompatEmployeesView(PeopleForceCompatAPIView):
    def get(self, request):
        auth_error = self._auth_error(request)
        if auth_error:
            return auth_error

        payload = {}
        request_log = self._create_request_log(request, payload)

        page = max(1, int(request.query_params.get("page", 1)))
        per_page = min(100, max(1, int(request.query_params.get("per_page", 100))))
        qs = _employee_queryset()

        if request.query_params.get("status") == "all":
            qs = Employee.objects.select_related("division", "department", "position").order_by("last_name", "first_name", "middle_name")

        total = qs.count()
        pages = max(1, math.ceil(total / per_page)) if total else 1
        offset = (page - 1) * per_page
        employees = [_employee_payload(employee) for employee in qs[offset : offset + per_page]]

        response_payload = {
            "data": employees,
            "meta": {"total": total},
            "metadata": {
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "pages": pages,
                    "total": total,
                }
            },
        }
        self._finalize_request_log(request_log, status_code=200, response_payload=response_payload)
        return Response(response_payload)


class PeopleForceCompatEmployeeDetailView(PeopleForceCompatAPIView):
    def get(self, request, employee_id: str):
        auth_error = self._auth_error(request)
        if auth_error:
            return auth_error

        payload = {}
        request_log = self._create_request_log(request, payload)
        employee = _find_employee_by_peopleforce_id(employee_id)
        if not employee and employee_id.isdigit():
            employee = Employee.objects.filter(pk=employee_id).first()

        if not employee:
            response_payload = {"error": "Employee not found"}
            self._finalize_request_log(
                request_log,
                status_code=404,
                response_payload=response_payload,
                processed_status=PeopleForceCompatRequest.ProcessedStatus.FAILED,
                error_message="Employee not found",
            )
            return Response(response_payload, status=status.HTTP_404_NOT_FOUND)

        response_payload = {"data": _employee_payload(employee)}
        self._finalize_request_log(request_log, status_code=200, response_payload=response_payload)
        return Response(response_payload)


def _upsert_timesheet_entry(payload: dict[str, Any], request_log: PeopleForceCompatRequest) -> tuple[PeopleForceCompatTimesheetEntry | None, list[str]]:
    employee_id = payload.get("employee_id")
    if employee_id in (None, ""):
        return None, ["employee_id is required"]

    try:
        starts_at = _parse_datetime_value(payload.get("starts_at"))
        ends_at = _parse_datetime_value(payload.get("ends_at"))
    except ValueError as exc:
        return None, [str(exc)]

    if starts_at >= ends_at:
        return None, ["starts_at must be earlier than ends_at"]

    legacy_employee_id = str(employee_id)
    legacy_entry_id = str(
        payload.get("legacy_peopleforce_entry_id")
        or payload.get("peopleforce_entry_id")
        or payload.get("external_id")
        or ""
    )
    employee = _find_employee_by_peopleforce_id(legacy_employee_id)
    comment = str(payload.get("comment") or "")
    minutes = _duration_minutes(starts_at, ends_at)
    entry_date = _entry_date(starts_at)

    with transaction.atomic():
        active_entries = PeopleForceCompatTimesheetEntry.objects.select_for_update().filter(
            legacy_peopleforce_employee_id=legacy_employee_id,
            deleted_at__isnull=True,
        )
        exact_entry = active_entries.filter(starts_at=starts_at, ends_at=ends_at).first()
        if exact_entry:
            exact_entry.employee = employee or exact_entry.employee
            if legacy_entry_id and not exact_entry.legacy_peopleforce_entry_id:
                exact_entry.legacy_peopleforce_entry_id = legacy_entry_id
            exact_entry.date = entry_date
            exact_entry.minutes = minutes
            exact_entry.entry_type = str(payload.get("type") or "working")
            exact_entry.comment = comment
            exact_entry.raw_payload = payload
            exact_entry.request = request_log
            exact_entry.save(
                update_fields=[
                    "employee",
                    "legacy_peopleforce_entry_id",
                    "date",
                    "minutes",
                    "entry_type",
                    "comment",
                    "raw_payload",
                    "request",
                    "updated_at",
                ]
            )
            _ensure_attendance_period(exact_entry, employee, starts_at, ends_at, entry_date, minutes, comment)
            return exact_entry, []

        overlap = active_entries.filter(starts_at__lt=ends_at, ends_at__gt=starts_at).first()
        if overlap:
            return None, [f"overlaps with existing timesheet entry {overlap.id}"]

        attendance_period = None
        if employee:
            attendance_period = AttendancePeriod.objects.create(
                employee=employee,
                date=entry_date,
                start_at=starts_at,
                end_at=ends_at,
                duration_minutes=minutes,
                period_type=_period_type(comment),
                comment=comment,
            )

        entry = PeopleForceCompatTimesheetEntry.objects.create(
            employee=employee,
            legacy_peopleforce_entry_id=legacy_entry_id,
            legacy_peopleforce_employee_id=legacy_employee_id,
            attendance_period=attendance_period,
            request=request_log,
            starts_at=starts_at,
            ends_at=ends_at,
            date=entry_date,
            minutes=minutes,
            entry_type=str(payload.get("type") or "working"),
            comment=comment,
            raw_payload=payload,
        )
        return entry, []


def _ensure_attendance_period(
    entry: PeopleForceCompatTimesheetEntry,
    employee: Employee | None,
    starts_at: datetime,
    ends_at: datetime,
    entry_date: datetime.date,
    minutes: int,
    comment: str,
) -> None:
    if not employee:
        return

    if entry.attendance_period_id:
        period = entry.attendance_period
        period.employee = employee
        period.date = entry_date
        period.start_at = starts_at
        period.end_at = ends_at
        period.duration_minutes = minutes
        period.period_type = _period_type(comment)
        period.comment = comment
        period.save(
            update_fields=[
                "employee",
                "date",
                "start_at",
                "end_at",
                "duration_minutes",
                "period_type",
                "comment",
                "updated_at",
            ]
        )
        return

    entry.attendance_period = AttendancePeriod.objects.create(
        employee=employee,
        date=entry_date,
        start_at=starts_at,
        end_at=ends_at,
        duration_minutes=minutes,
        period_type=_period_type(comment),
        comment=comment,
    )
    entry.save(update_fields=["attendance_period", "updated_at"])


class PeopleForceCompatTimesheetEntriesView(PeopleForceCompatAPIView):
    def get(self, request):
        auth_error = self._auth_error(request)
        if auth_error:
            return auth_error

        payload = {}
        request_log = self._create_request_log(request, payload)

        qs = PeopleForceCompatTimesheetEntry.objects.filter(deleted_at__isnull=True)
        employee_ids = request.query_params.getlist("employee_ids[]")
        employee_ids = employee_ids or request.query_params.getlist("employee_ids")
        employee_id = request.query_params.get("employee_id")
        if employee_id:
            employee_ids.append(employee_id)
        if employee_ids:
            qs = qs.filter(legacy_peopleforce_employee_id__in=[str(value) for value in employee_ids])

        starts_on = request.query_params.get("starts_on")
        if starts_on:
            parsed = parse_date(starts_on)
            if parsed:
                qs = qs.filter(date__gte=parsed)

        ends_on = request.query_params.get("ends_on")
        if ends_on:
            parsed = parse_date(ends_on)
            if parsed:
                qs = qs.filter(date__lte=parsed)

        statuses = request.query_params.getlist("status[]")
        status_value = request.query_params.get("status")
        if status_value:
            statuses.append(status_value)
        if statuses:
            qs = qs.filter(status__in=statuses)

        page = max(1, int(request.query_params.get("page", 1)))
        per_page = min(100, max(1, int(request.query_params.get("per_page", 100))))
        total = qs.count()
        pages = max(1, math.ceil(total / per_page)) if total else 1
        offset = (page - 1) * per_page
        entries = [_serialize_timesheet_entry(entry) for entry in qs.order_by("starts_at", "id")[offset : offset + per_page]]

        response_payload = {
            "data": entries,
            "metadata": {
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "pages": pages,
                    "total": total,
                }
            },
        }
        self._finalize_request_log(request_log, status_code=200, response_payload=response_payload)
        return Response(response_payload)

    def post(self, request):
        auth_error = self._auth_error(request)
        if auth_error:
            return auth_error

        payload = _request_payload(request)
        request_log = self._create_request_log(request, payload)
        if not isinstance(payload, dict):
            response_payload = {"errors": {"count": 1, "data": [{"messages": ["JSON object body is required"]}]}}
            self._finalize_request_log(
                request_log,
                status_code=422,
                response_payload=response_payload,
                processed_status=PeopleForceCompatRequest.ProcessedStatus.FAILED,
                error_message="JSON object body is required",
            )
            return Response(response_payload, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        entry, errors = _upsert_timesheet_entry(payload, request_log)
        if errors:
            response_payload = {
                "errors": {
                    "count": 1,
                    "data": [{"employee_id": payload.get("employee_id"), "messages": errors}],
                }
            }
            self._finalize_request_log(
                request_log,
                status_code=422,
                response_payload=response_payload,
                processed_status=PeopleForceCompatRequest.ProcessedStatus.FAILED,
                error_message="; ".join(errors),
            )
            return Response(response_payload, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        response_payload = {"data": _serialize_timesheet_entry(entry)}
        processed_status = (
            PeopleForceCompatRequest.ProcessedStatus.PROCESSED
            if entry.employee_id
            else PeopleForceCompatRequest.ProcessedStatus.PARTIAL
        )
        self._finalize_request_log(
            request_log,
            status_code=201,
            response_payload=response_payload,
            processed_status=processed_status,
            error_message="" if entry.employee_id else "Employee mapping not found",
        )
        return Response(response_payload, status=status.HTTP_201_CREATED)


class PeopleForceCompatTimesheetEntryDetailView(PeopleForceCompatAPIView):
    def delete(self, request, entry_id: int):
        auth_error = self._auth_error(request)
        if auth_error:
            return auth_error

        payload = _request_payload(request)
        request_log = self._create_request_log(request, payload)
        entry = PeopleForceCompatTimesheetEntry.objects.filter(pk=entry_id, deleted_at__isnull=True).first()
        if not entry:
            entry = PeopleForceCompatTimesheetEntry.objects.filter(
                legacy_peopleforce_entry_id=str(entry_id),
                deleted_at__isnull=True,
            ).first()

        if not entry:
            response_payload = {"error": "Timesheet entry not found"}
            self._finalize_request_log(
                request_log,
                status_code=404,
                response_payload=response_payload,
                processed_status=PeopleForceCompatRequest.ProcessedStatus.FAILED,
                error_message="Timesheet entry not found",
            )
            return Response(response_payload, status=status.HTTP_404_NOT_FOUND)

        self._soft_delete_entry(entry)
        response_payload = {"data": {"id": entry_id, "deleted": True}}
        self._finalize_request_log(request_log, status_code=200, response_payload=response_payload)
        return Response(response_payload)

    @staticmethod
    def _soft_delete_entry(entry: PeopleForceCompatTimesheetEntry) -> None:
        period = entry.attendance_period
        entry.deleted_at = timezone.now()
        entry.attendance_period = None
        entry.save(update_fields=["deleted_at", "attendance_period", "updated_at"])
        if period:
            period.delete()


class PeopleForceCompatTimesheetEntriesBulkView(PeopleForceCompatAPIView):
    def post(self, request):
        auth_error = self._auth_error(request)
        if auth_error:
            return auth_error

        payload = _request_payload(request)
        request_log = self._create_request_log(request, payload)
        blocks = payload.get("data", []) if isinstance(payload, dict) else []

        records: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        if not isinstance(blocks, list):
            errors.append({"messages": ["data must be a list"]})
        else:
            for block in blocks:
                employee_id = block.get("employee_id") if isinstance(block, dict) else None
                entries = block.get("entries", []) if isinstance(block, dict) else []
                if not employee_id:
                    errors.append({"employee_id": employee_id, "messages": ["employee_id is required"]})
                    continue
                if not isinstance(entries, list):
                    errors.append({"employee_id": employee_id, "messages": ["entries must be a list"]})
                    continue
                for entry_payload in entries:
                    if not isinstance(entry_payload, dict):
                        errors.append({"employee_id": employee_id, "messages": ["entry must be an object"]})
                        continue
                    normalized_payload = {**entry_payload, "employee_id": employee_id}
                    entry, entry_errors = _upsert_timesheet_entry(normalized_payload, request_log)
                    if entry_errors:
                        errors.append({"employee_id": employee_id, "messages": entry_errors})
                    else:
                        records.append(_serialize_timesheet_entry(entry))

        response_payload: dict[str, Any] = {"records": {"count": len(records), "data": records}}
        if errors:
            response_payload["errors"] = {"count": len(errors), "data": errors}

        processed_status = PeopleForceCompatRequest.ProcessedStatus.PROCESSED
        if errors and records:
            processed_status = PeopleForceCompatRequest.ProcessedStatus.PARTIAL
        elif errors:
            processed_status = PeopleForceCompatRequest.ProcessedStatus.FAILED

        self._finalize_request_log(
            request_log,
            status_code=200,
            response_payload=response_payload,
            processed_status=processed_status,
            error_message=f"{len(errors)} errors" if errors else "",
        )
        return Response(response_payload)

    def delete(self, request):
        auth_error = self._auth_error(request)
        if auth_error:
            return auth_error

        payload = _request_payload(request)
        request_log = self._create_request_log(request, payload)
        employee_ids = [str(value) for value in payload.get("employee_ids", [])] if isinstance(payload, dict) else []

        try:
            starts_at = _parse_datetime_value(payload.get("starts_at")) if isinstance(payload, dict) else None
            ends_at = _parse_datetime_value(payload.get("ends_at")) if isinstance(payload, dict) else None
        except ValueError as exc:
            response_payload = {"errors": {"count": 1, "data": [{"messages": [str(exc)]}]}}
            self._finalize_request_log(
                request_log,
                status_code=422,
                response_payload=response_payload,
                processed_status=PeopleForceCompatRequest.ProcessedStatus.FAILED,
                error_message=str(exc),
            )
            return Response(response_payload, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if not employee_ids or not starts_at or not ends_at:
            response_payload = {"errors": {"count": 1, "data": [{"messages": ["employee_ids, starts_at and ends_at are required"]}]}}
            self._finalize_request_log(
                request_log,
                status_code=422,
                response_payload=response_payload,
                processed_status=PeopleForceCompatRequest.ProcessedStatus.FAILED,
                error_message="employee_ids, starts_at and ends_at are required",
            )
            return Response(response_payload, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        qs = PeopleForceCompatTimesheetEntry.objects.filter(
            legacy_peopleforce_employee_id__in=employee_ids,
            deleted_at__isnull=True,
            starts_at__lt=ends_at,
            ends_at__gt=starts_at,
        )
        entries = list(qs.select_related("attendance_period"))
        for entry in entries:
            PeopleForceCompatTimesheetEntryDetailView._soft_delete_entry(entry)

        response_payload = {"count": len(entries)}
        self._finalize_request_log(request_log, status_code=200, response_payload=response_payload)
        return Response(response_payload)
