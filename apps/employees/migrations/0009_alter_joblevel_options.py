from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0008_joblevel_sort_order"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="joblevel",
            options={"ordering": ["sort_order", "name"]},
        ),
    ]
