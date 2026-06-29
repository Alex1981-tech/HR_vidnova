from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0030_companylink"),
    ]

    operations = [
        migrations.AddField(
            model_name="companylink",
            name="audience_type",
            field=models.CharField(
                choices=[("all", "Усі"), ("conditions", "Конкретні люди")],
                default="all",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="companylink",
            name="conditions",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
