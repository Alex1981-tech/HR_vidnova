from django.db import migrations, models

# Бекофіл порядку й іконки для імпортованих типів відсутностей (за назвою).
NAME_META = {
    "Відпустка": (1, "plane"),
    "Лікарняний": (2, "briefcase"),
    "За власний рахунок": (3, "handshake"),
    "Віддалена робота": (4, "home"),
    "Особисті події": (5, "heart"),
    "Декретна відпустка": (6, "baby"),
    "Неробоча зміна (згідно графіку)": (7, "moon"),
}


def backfill(apps, schema_editor):
    LeaveType = apps.get_model("leave", "LeaveType")
    extra = 100
    for lt in LeaveType.objects.all().order_by("name"):
        order, icon = NAME_META.get(lt.name, (None, "calendar"))
        if order is None:
            extra += 1
            order = extra
        lt.order = order
        if not lt.icon:
            lt.icon = icon
        lt.save(update_fields=["order", "icon", "updated_at"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("leave", "0002_leavebalance_leaverequest_amount_and_more")]

    operations = [
        migrations.AddField(
            model_name="leavetype",
            name="icon",
            field=models.CharField(blank=True, help_text="Ключ іконки (frontend)", max_length=40),
        ),
        migrations.AddField(
            model_name="leavetype",
            name="order",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AlterModelOptions(
            name="leavetype",
            options={"ordering": ["order", "name"]},
        ),
        migrations.RunPython(backfill, noop),
    ]
