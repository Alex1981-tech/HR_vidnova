from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("leave", "0008_normalize_legacy_leave_opening_dates"),
    ]

    operations = [
        migrations.AddField(
            model_name="leavepolicy",
            name="deduct_non_working_holidays",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leavepolicy",
            name="allow_on_demand_absence",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leavepolicy",
            name="on_demand_limit",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
        migrations.AddField(
            model_name="leavepolicy",
            name="allow_negative_balance",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="leavepolicy",
            name="limit_negative_balance",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leavepolicy",
            name="max_negative_balance",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
    ]
