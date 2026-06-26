from django.db import migrations, models


DEFAULT_TERMINATION_REASONS = (
    "Вибір іншої компанії",
    "Високий рівень стресу",
    "Відсутність перспективи кар'єрного зростання",
    "Відсутність похвали та заохочень",
    "Відсутність спілкування з керівництвом",
    "Конфлікти у колективі",
    "Не відповідає посаді",
    "Недостатня заробітна плата",
    "Незручно добиратися до роботи",
    "Очікування співробітника не виправдовуються",
    "Переїзд в іншу країну",
    "Погана продуктивність",
)


def seed_termination_reasons(apps, schema_editor):
    TerminationReason = apps.get_model("employees", "TerminationReason")
    for name in DEFAULT_TERMINATION_REASONS:
        TerminationReason.objects.get_or_create(name=name, defaults={"is_active": True})


def unseed_termination_reasons(apps, schema_editor):
    TerminationReason = apps.get_model("employees", "TerminationReason")
    TerminationReason.objects.filter(name__in=DEFAULT_TERMINATION_REASONS, external_peopleforce_id="").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0011_medicalspecialty_external_peopleforce_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="TerminationReason",
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
        migrations.RunPython(seed_termination_reasons, unseed_termination_reasons),
    ]
