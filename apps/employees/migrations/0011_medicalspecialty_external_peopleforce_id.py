from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0010_clinic_location_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="medicalspecialty",
            name="external_peopleforce_id",
            field=models.CharField(blank=True, db_index=True, max_length=120),
        ),
    ]
