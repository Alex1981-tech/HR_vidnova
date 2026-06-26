from django.db import migrations, models


def seed_genders(apps, schema_editor):
    Employee = apps.get_model("employees", "Employee")
    Gender = apps.get_model("employees", "Gender")
    labels = {
        "female": "Жінка",
        "male": "Чоловік",
        "woman": "Жінка",
        "man": "Чоловік",
    }
    values = (
        Employee.objects.exclude(gender="")
        .values_list("gender", flat=True)
        .distinct()
    )
    for value in values:
        code = str(value).strip()
        if not code:
            continue
        name = labels.get(code.lower(), code)
        base_name = name
        suffix = 2
        while Gender.objects.filter(name=name).exclude(code=code).exists():
            name = f"{base_name} {suffix}"
            suffix += 1
        Gender.objects.get_or_create(code=code, defaults={"name": name, "is_active": True})


def unseed_genders(apps, schema_editor):
    Gender = apps.get_model("employees", "Gender")
    Gender.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0006_alter_employee_avatar_url"),
    ]

    operations = [
        migrations.CreateModel(
            name="Gender",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=80, unique=True)),
                ("name", models.CharField(max_length=160, unique=True)),
                ("external_peopleforce_id", models.CharField(blank=True, db_index=True, max_length=120)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.RunPython(seed_genders, unseed_genders),
    ]
