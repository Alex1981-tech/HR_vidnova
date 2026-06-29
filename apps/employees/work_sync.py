"""Синхронізація рядків PF-подібних таблиць «Посади»/«Робота» у доменні моделі.

Таблиці лишаються UI-шаром (рядки в Employee.custom_fields), але при збереженні
рядка ми дзеркалимо дані у нормалізовані моделі, з яких читають SKUD/звіти:
  - Посади  → Employee.position/department/division/clinic/job_level + ManagerAssignment + EmployeePositionHistory
  - Робота  → Employee.employment_type + EmployeeEmploymentStatus

Резолв select-колонок — за назвою (опції генеруються з назв довідників, які унікальні).
Колонка типу employee зберігає id. Кожен рядок отримує стабільний синтетичний ключ
`hrtable:<row_id>` у legacy_peopleforce_id історії — це робить sync ідемпотентним і
дозволяє оновлювати/видаляти конкретний історичний запис разом із рядком.
"""

from __future__ import annotations

from .models import (
    Clinic,
    Department,
    Division,
    Employee,
    EmployeeEmploymentStatus,
    EmployeePositionHistory,
    EmploymentType,
    JobLevel,
    ManagerAssignment,
    Position,
)

SYNTHETIC_KEY_PREFIX = "hrtable:"

# Ключ колонки (seed) → доменне поле Employee + довідник для резолву за назвою.
POSITION_FIELD_RESOLVERS = {
    "posada": ("position", Position),
    "departament": ("department", Department),
    "pidrozdil": ("division", Division),
    "lokatsiya": ("clinic", Clinic),
    "riven": ("job_level", JobLevel),
}


def _row_key(row):
    rid = row.get("row_id")
    return f"{SYNTHETIC_KEY_PREFIX}{rid}" if rid else ""


def _parse_date(value):
    """ISO 'YYYY-MM-DD' → date | None (мовчки ігнорує невалідне)."""
    if not value or not isinstance(value, str):
        return None
    from datetime import date

    parts = value.split("-")
    if len(parts) != 3:
        return None
    try:
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, TypeError):
        return None


def _resolve_by_name(model, name):
    name = (name or "").strip() if isinstance(name, str) else ""
    if not name:
        return None
    return model.objects.filter(name=name).first()


def _resolve_employee(value):
    if value in (None, "", 0):
        return None
    try:
        return Employee.objects.filter(pk=int(value)).first()
    except (ValueError, TypeError):
        return None


def _rows_of(employee, table):
    rows = (employee.custom_fields or {}).get(f"table_{table.id}", [])
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _latest_row(rows):
    """Останній за датою 'die_z' рядок (ISO сортується лексикографічно); порожні → найстаріші."""
    if not rows:
        return None
    return sorted(rows, key=lambda r: (str(r.get("die_z") or ""), str(r.get("row_id") or "")))[-1]


def sync_positions(employee, table):
    rows = _rows_of(employee, table)
    have_keys = {c.get("key") for c in (table.columns or [])}

    # 1. Дзеркалимо КОЖЕН рядок у EmployeePositionHistory (повна хронологія), keyed by row_id.
    seen_keys = set()
    for row in rows:
        key = _row_key(row)
        if not key:
            continue
        seen_keys.add(key)
        defaults = {"effective_on": _parse_date(row.get("die_z")), "raw_payload": {"source": "hr_table", "table_id": table.id}}
        for col_key, (attr, model) in POSITION_FIELD_RESOLVERS.items():
            if col_key in have_keys:
                defaults[attr] = _resolve_by_name(model, row.get(col_key))
        if "menedzher" in have_keys:
            defaults["manager"] = _resolve_employee(row.get("menedzher"))
        EmployeePositionHistory.objects.update_or_create(
            employee=employee, legacy_peopleforce_id=key, defaults=defaults,
        )
    # Прибираємо історичні записи видалених рядків (тільки наші синтетичні).
    EmployeePositionHistory.objects.filter(
        employee=employee, legacy_peopleforce_id__startswith=SYNTHETIC_KEY_PREFIX,
    ).exclude(legacy_peopleforce_id__in=seen_keys).delete()

    # 2. Поточні поля Employee — з останнього рядка.
    latest = _latest_row(rows)
    if latest is None:
        return
    update_fields = []
    for col_key, (attr, model) in POSITION_FIELD_RESOLVERS.items():
        if col_key not in have_keys:
            continue
        raw = latest.get(col_key)
        # Порожнє значення очищає поле; непорожнє, але нерезолвлене — не чіпаємо (щоб не втратити дані).
        if isinstance(raw, str) and not raw.strip():
            setattr(employee, f"{attr}_id", None)
            update_fields.append(attr)
        else:
            obj = _resolve_by_name(model, raw)
            if obj is not None:
                setattr(employee, attr, obj)
                update_fields.append(attr)
    if update_fields:
        employee.save(update_fields=[f"{f}_id" for f in update_fields] + ["updated_at"])

    # 3. ManagerAssignment з останнього рядка.
    if "menedzher" in have_keys:
        manager = _resolve_employee(latest.get("menedzher"))
        eff = _parse_date(latest.get("die_z"))
        if manager and manager.pk != employee.pk and eff:
            ManagerAssignment.objects.update_or_create(
                employee=employee, manager=manager, valid_from=eff, defaults={"is_primary": True},
            )


def sync_employment(employee, table):
    rows = _rows_of(employee, table)
    have_keys = {c.get("key") for c in (table.columns or [])}

    seen_keys = set()
    for row in rows:
        key = _row_key(row)
        if not key:
            continue
        seen_keys.add(key)
        defaults = {
            "effective_from": _parse_date(row.get("die_z")),
            "raw_payload": {"source": "hr_table", "table_id": table.id},
        }
        if "tip_roboti" in have_keys:
            defaults["employment_type"] = _resolve_by_name(EmploymentType, row.get("tip_roboti"))
        if "grafik" in have_keys:
            defaults["working_pattern_name"] = (row.get("grafik") or "").strip() if isinstance(row.get("grafik"), str) else ""
        if "komentar" in have_keys:
            defaults["comment"] = (row.get("komentar") or "") if isinstance(row.get("komentar"), str) else ""
        EmployeeEmploymentStatus.objects.update_or_create(
            employee=employee, legacy_peopleforce_id=key, defaults=defaults,
        )
    EmployeeEmploymentStatus.objects.filter(
        employee=employee, legacy_peopleforce_id__startswith=SYNTHETIC_KEY_PREFIX,
    ).exclude(legacy_peopleforce_id__in=seen_keys).delete()

    latest = _latest_row(rows)
    if latest is None:
        return
    if "tip_roboti" in have_keys:
        raw = latest.get("tip_roboti")
        if isinstance(raw, str) and not raw.strip():
            employee.employment_type_id = None
            employee.save(update_fields=["employment_type_id", "updated_at"])
        else:
            obj = _resolve_by_name(EmploymentType, raw)
            if obj is not None:
                employee.employment_type = obj
                employee.save(update_fields=["employment_type_id", "updated_at"])


def sync_table(employee, table):
    """Точка входу: викликати після зміни рядків таблиці з sync_target."""
    target = getattr(table, "sync_target", "") or ""
    if target == "positions":
        sync_positions(employee, table)
    elif target == "employment":
        sync_employment(employee, table)
