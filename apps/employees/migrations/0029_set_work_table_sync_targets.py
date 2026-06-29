from django.db import migrations


def set_targets(apps, schema_editor):
    Table = apps.get_model("employees", "EmployeeFieldTable")
    Table.objects.filter(group__tab="work", name="Посади").update(sync_target="positions")
    Table.objects.filter(group__tab="work", name="Робота").update(sync_target="employment")


def unset_targets(apps, schema_editor):
    Table = apps.get_model("employees", "EmployeeFieldTable")
    Table.objects.filter(group__tab="work", name__in=["Посади", "Робота"]).update(sync_target="")


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0028_employeefieldtable_sync_target"),
    ]

    operations = [
        migrations.RunPython(set_targets, unset_targets),
    ]
