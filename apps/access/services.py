from __future__ import annotations

import re
import secrets
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import Group

from apps.employees.models import Employee

UA_PHONE_PREFIX = "+380"
EMPLOYEE_GROUP_NAME = "employee"


class PhoneMatchStatus:
    MATCHED = "matched"
    INVALID_PHONE = "invalid_phone"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    INACTIVE_USER = "inactive_user"


@dataclass(frozen=True)
class EmployeePhoneMatch:
    status: str
    phone_normalized: str = ""
    employee: Employee | None = None
    matches_count: int = 0

    @property
    def is_matched(self) -> bool:
        return self.status == PhoneMatchStatus.MATCHED and self.employee is not None


def normalize_phone(raw: object) -> str:
    """Return an E.164-like canonical phone value.

    Ukrainian local numbers are normalized to +380XXXXXXXXX. Other numbers are
    kept as digits with a leading plus so future integrations can still compare
    them deterministically.
    """
    if raw is None:
        return ""
    value = re.sub(r"[^\d+]", "", str(raw))
    if not value:
        return ""
    if value.startswith("0") and len(value) >= 10:
        return UA_PHONE_PREFIX + value[1:]
    if value.startswith("80") and len(value) == 11:
        return f"+3{value}"
    if value.startswith("380"):
        return f"+{value}"
    if value.startswith("+"):
        return value
    return f"+{value}"


def find_employee_by_phone(raw_phone: object) -> EmployeePhoneMatch:
    phone = normalize_phone(raw_phone)
    if not phone:
        return EmployeePhoneMatch(status=PhoneMatchStatus.INVALID_PHONE)

    employees = (
        Employee.objects.filter(status=Employee.Status.ACTIVE)
        .exclude(phone="", phone2="")
        .select_related("user")
        .only("id", "first_name", "last_name", "middle_name", "phone", "phone2", "status", "user__is_active")
    )
    matches: dict[int, Employee] = {}
    for employee in employees:
        if normalize_phone(employee.phone) == phone or normalize_phone(employee.phone2) == phone:
            matches[employee.pk] = employee

    if not matches:
        return EmployeePhoneMatch(status=PhoneMatchStatus.NOT_FOUND, phone_normalized=phone)
    if len(matches) > 1:
        return EmployeePhoneMatch(
            status=PhoneMatchStatus.CONFLICT,
            phone_normalized=phone,
            matches_count=len(matches),
        )

    employee = next(iter(matches.values()))
    if employee.user_id and employee.user and not employee.user.is_active:
        return EmployeePhoneMatch(
            status=PhoneMatchStatus.INACTIVE_USER,
            phone_normalized=phone,
            matches_count=1,
        )
    return EmployeePhoneMatch(
        status=PhoneMatchStatus.MATCHED,
        phone_normalized=phone,
        employee=employee,
        matches_count=1,
    )


def generate_login_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_login_code(code: str) -> str:
    return make_password(code)


def login_code_matches(code: str, code_hash: str) -> bool:
    return check_password(code, code_hash)


def ensure_employee_user(employee: Employee):
    if employee.user_id:
        user = employee.user
        if employee.email and not user.email:
            user.email = employee.email
            user.save(update_fields=["email"])
        employee_group, _ = Group.objects.get_or_create(name=EMPLOYEE_GROUP_NAME)
        user.groups.add(employee_group)
        return user

    user_model = get_user_model()
    base_username = f"employee-{employee.pk}"
    username = base_username
    suffix = 1
    while True:
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                "first_name": employee.first_name[:150],
                "last_name": employee.last_name[:150],
                "email": employee.email,
                "is_active": True,
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=["password"])
            break
        linked_employee_id = getattr(getattr(user, "employee_profile", None), "id", None)
        if linked_employee_id in (None, employee.id):
            break
        suffix += 1
        username = f"{base_username}-{suffix}"

    employee.user = user
    employee.save(update_fields=["user", "updated_at"])
    employee_group, _ = Group.objects.get_or_create(name=EMPLOYEE_GROUP_NAME)
    user.groups.add(employee_group)
    return user
