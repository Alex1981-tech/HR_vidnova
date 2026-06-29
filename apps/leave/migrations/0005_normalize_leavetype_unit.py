from django.db import migrations


def normalize_unit(apps, schema_editor):
    LeaveType = apps.get_model("leave", "LeaveType")
    for lt in LeaveType.objects.all():
        raw = (lt.unit or "").strip().lower()
        if not raw:
            new = "days"
        elif raw.startswith("hour") or raw.startswith("год"):
            new = "hours"
        elif raw.startswith("day") or raw.startswith("дн") or raw.startswith("ден"):
            new = "days"
        else:
            new = "days"
        if new != lt.unit:
            lt.unit = new
            lt.save(update_fields=["unit"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("leave", "0004_alter_leavetype_unit"),
    ]

    operations = [
        migrations.RunPython(normalize_unit, noop),
    ]
