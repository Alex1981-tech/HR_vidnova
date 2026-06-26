from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0014_departmentlevel_department_manager_level"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkingPattern",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=180, unique=True)),
                ("external_peopleforce_id", models.CharField(blank=True, db_index=True, max_length=120)),
                ("monday_hours", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("tuesday_hours", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("wednesday_hours", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("thursday_hours", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("friday_hours", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("saturday_hours", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("sunday_hours", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("uses_time_range", models.BooleanField(default=True)),
                ("is_default", models.BooleanField(default=False)),
                ("schedule", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.AddIndex(
            model_name="workingpattern",
            index=models.Index(fields=["is_active", "name"], name="working_pattern_active_idx"),
        ),
    ]
