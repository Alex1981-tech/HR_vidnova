from django.db import migrations, models


DEFAULT_TERMINATION_TYPES = (
    "За власним бажанням",
    "За згодою сторін",
    "Не за власним бажанням",
)


def seed_termination_types(apps, schema_editor):
    TerminationType = apps.get_model("employees", "TerminationType")
    for name in DEFAULT_TERMINATION_TYPES:
        TerminationType.objects.get_or_create(name=name, defaults={"is_active": True})


def unseed_termination_types(apps, schema_editor):
    TerminationType = apps.get_model("employees", "TerminationType")
    TerminationType.objects.filter(name__in=DEFAULT_TERMINATION_TYPES, external_peopleforce_id="").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0012_terminationreason"),
    ]

    operations = [
        migrations.CreateModel(
            name="TerminationType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=180, unique=True)),
                ("external_peopleforce_id", models.CharField(blank=True, db_index=True, max_length=120)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.RunPython(seed_termination_types, unseed_termination_types),
    ]
