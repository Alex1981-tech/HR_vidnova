from django.db import migrations

# (tab, group name, slug, [ (name, type, system_key, enabled, summary, required) ... ])
SEED = [
    ("personal", "Особисте", "personal", [
        ("Ідентифікатор працівника", "system", "employee_number", True, False, False),
        ("Ім'я", "system", "full_name", True, False, True),
        ("Електронна пошта", "system", "email", True, True, False),
        ("Особиста ел. пошта", "system", "personal_email", True, False, False),
        ("Дата народження", "system", "birth_date", True, False, False),
        ("Стать", "system", "gender", True, False, False),
    ]),
    ("personal", "Контакти", "contacts", [
        ("Мобільний телефон", "system", "phone", True, True, False),
        ("Номер робочого телефону", "system", "phone2", True, True, False),
        ("Telegram ID", "system", "telegram_id", True, False, False),
    ]),
    ("personal", "Соціальні мережі", "social", [
        ("URL-адреса Facebook", "system", "facebook_url", True, False, False),
        ("URL-адреса Instagram", "system", "instagram_url", True, False, False),
    ]),
    ("personal", "Додаткове керівництво", "extra-management", []),
    ("work", "Посада", "position", [
        ("Посада", "system", "position", True, True, False),
        ("Рівень посади", "system", "job_level", True, True, False),
        ("Тип роботи", "system", "employment_type", True, True, False),
        ("Дата початку", "system", "hired_on", True, True, False),
    ]),
    ("work", "Команда", "team", [
        ("Департамент", "system", "department", True, True, False),
        ("Підрозділ", "system", "division", True, True, False),
        ("Локація", "system", "clinic", True, True, False),
    ]),
    ("compensation", "Компенсація", "compensation", []),
]


def seed(apps, schema_editor):
    Group = apps.get_model("employees", "EmployeeFieldGroup")
    Field = apps.get_model("employees", "EmployeeField")
    if Group.objects.exists():
        return
    for g_order, (tab, gname, slug, fields) in enumerate(SEED):
        group = Group.objects.create(tab=tab, name=gname, slug=slug, is_system=True, order=g_order)
        for f_order, (fname, ftype, key, enabled, summary, required) in enumerate(fields):
            Field.objects.create(
                group=group,
                name=fname,
                field_type=ftype,
                is_system=True,
                system_key=key,
                is_enabled=enabled,
                show_in_summary=summary,
                is_required=required,
                order=f_order,
            )


def unseed(apps, schema_editor):
    Group = apps.get_model("employees", "EmployeeFieldGroup")
    Group.objects.filter(is_system=True).delete()


class Migration(migrations.Migration):
    dependencies = [("employees", "0019_field_groups")]
    operations = [migrations.RunPython(seed, unseed)]
