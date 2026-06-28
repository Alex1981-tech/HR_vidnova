from django.db import migrations, models


# Системні поля, які додаємо в наявні групи: (slug групи, label, system_key, summary, order)
SEED_SYSTEM_FIELDS = [
    ("social", "URL-адреса Facebook", "facebook_url", False, 0),
    ("social", "URL-адреса Instagram", "instagram_url", False, 1),
    ("contacts", "Telegram ID", "telegram_id", False, 2),
]


def seed(apps, schema_editor):
    Group = apps.get_model("employees", "EmployeeFieldGroup")
    Field = apps.get_model("employees", "EmployeeField")
    for slug, name, key, summary, order in SEED_SYSTEM_FIELDS:
        group = Group.objects.filter(tab="personal", slug=slug).order_by("order").first()
        if group is None:
            continue
        Field.objects.get_or_create(
            group=group,
            system_key=key,
            defaults={
                "name": name,
                "field_type": "system",
                "is_system": True,
                "is_enabled": True,
                "show_in_summary": summary,
                "order": order,
            },
        )


def unseed(apps, schema_editor):
    Field = apps.get_model("employees", "EmployeeField")
    Field.objects.filter(
        is_system=True,
        system_key__in=["facebook_url", "instagram_url", "telegram_id"],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("employees", "0020_seed_field_config")]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="telegram_id",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="employee",
            name="facebook_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="employee",
            name="instagram_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.RunPython(seed, unseed),
    ]
