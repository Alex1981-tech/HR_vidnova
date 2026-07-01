from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("leave", "0009_leave_policy_detail_rules"),
    ]

    operations = [
        migrations.AddField(
            model_name="leavepolicyaccrualrule",
            name="seniority_bonus_levels",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
