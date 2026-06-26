from django.db import migrations, models


def seed_joblevel_sort_order(apps, schema_editor):
    JobLevel = apps.get_model("employees", "JobLevel")
    for index, level in enumerate(JobLevel.objects.order_by("name", "id"), start=1):
        level.sort_order = index * 10
        level.save(update_fields=["sort_order"])


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0007_gender"),
    ]

    operations = [
        migrations.AddField(
            model_name="joblevel",
            name="sort_order",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.RunPython(seed_joblevel_sort_order, migrations.RunPython.noop),
    ]
