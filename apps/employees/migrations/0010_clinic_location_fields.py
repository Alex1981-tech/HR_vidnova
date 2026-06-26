from django.db import migrations, models


def policy_name(policy_id):
    return "Vidnova" if str(policy_id or "") == "15490" else ""


def seed_clinic_location_fields(apps, schema_editor):
    Clinic = apps.get_model("employees", "Clinic")
    PeopleForceEntity = apps.get_model("integrations", "PeopleForceEntity")
    for entity in PeopleForceEntity.objects.filter(entity_type="locations"):
        payload = entity.payload or {}
        external_id = str(payload.get("id") or entity.external_id or "")
        if not external_id:
            continue
        clinic = Clinic.objects.filter(external_peopleforce_id=external_id).first()
        if not clinic:
            continue
        holiday_policy_id = str(payload.get("holiday_policy_id") or "")
        clinic.country_code = str(payload.get("country_code") or "")[:8]
        clinic.address = str(payload.get("address") or "")[:260]
        clinic.holiday_policy_id = holiday_policy_id[:120]
        clinic.holiday_policy_name = policy_name(holiday_policy_id)
        clinic.time_zone = str(payload.get("time_zone") or "Kyiv")[:80]
        clinic.save(
            update_fields=[
                "country_code",
                "address",
                "holiday_policy_id",
                "holiday_policy_name",
                "time_zone",
            ],
        )


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0001_initial"),
        ("employees", "0009_alter_joblevel_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="clinic",
            name="country_code",
            field=models.CharField(blank=True, max_length=8),
        ),
        migrations.AddField(
            model_name="clinic",
            name="address",
            field=models.CharField(blank=True, max_length=260),
        ),
        migrations.AddField(
            model_name="clinic",
            name="holiday_policy_id",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="clinic",
            name="holiday_policy_name",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="clinic",
            name="time_zone",
            field=models.CharField(blank=True, default="Kyiv", max_length=80),
        ),
        migrations.RunPython(seed_clinic_location_fields, migrations.RunPython.noop),
    ]
