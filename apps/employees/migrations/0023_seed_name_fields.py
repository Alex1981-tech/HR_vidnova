from django.db import migrations
from django.db.models import F

# Системні поля-частини імені у групі «Особисте». full_name лишається read-only
# («Повне ім'я»), а Прізвище/Ім'я/По батькові стають редагованими (per-block edit, Фаза 2).
NAME_FIELDS = [
    ("Прізвище", "last_name"),
    ("Ім'я", "first_name"),
    ("По батькові", "middle_name"),
]


def add_name_fields(apps, schema_editor):
    Group = apps.get_model("employees", "EmployeeFieldGroup")
    Field = apps.get_model("employees", "EmployeeField")
    group = Group.objects.filter(tab="personal", slug="personal", is_system=True).first()
    if group is None:
        return
    if Field.objects.filter(group=group, system_key="last_name").exists():
        return
    # «Ім'я» (full_name) → «Повне ім'я», лишається read-only показовим полем.
    Field.objects.filter(group=group, system_key="full_name").update(name="Повне ім'я")
    # Звільняємо порядкові місця після full_name (order=1) під 3 нові поля.
    Field.objects.filter(group=group, order__gte=2).update(order=F("order") + 3)
    for i, (name, key) in enumerate(NAME_FIELDS):
        Field.objects.create(
            group=group,
            name=name,
            field_type="system",
            is_system=True,
            system_key=key,
            is_enabled=True,
            show_in_summary=False,
            is_required=False,
            order=2 + i,
        )


def remove_name_fields(apps, schema_editor):
    Group = apps.get_model("employees", "EmployeeFieldGroup")
    Field = apps.get_model("employees", "EmployeeField")
    group = Group.objects.filter(tab="personal", slug="personal", is_system=True).first()
    if group is None:
        return
    Field.objects.filter(group=group, system_key__in=["last_name", "first_name", "middle_name"]).delete()
    Field.objects.filter(group=group, system_key="full_name").update(name="Ім'я")
    Field.objects.filter(group=group, order__gte=5).update(order=F("order") - 3)


class Migration(migrations.Migration):
    dependencies = [("employees", "0022_seed_work_compensation_tables")]
    operations = [migrations.RunPython(add_name_fields, remove_name_fields)]
