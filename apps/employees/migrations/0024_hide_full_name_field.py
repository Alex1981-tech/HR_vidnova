from django.db import migrations

# full_name — derived @property (last_name+first_name+middle_name). У per-block edit
# (image copy 39) показуємо лише Ідентифікатор(ro) + Прізвище/Ім'я/По батькові, тож
# окремий рядок «Повне ім'я» зайвий — вимикаємо його видимість.


def hide_full_name(apps, schema_editor):
    Field = apps.get_model("employees", "EmployeeField")
    Field.objects.filter(
        group__tab="personal",
        group__slug="personal",
        system_key="full_name",
    ).update(is_enabled=False)


def show_full_name(apps, schema_editor):
    Field = apps.get_model("employees", "EmployeeField")
    Field.objects.filter(
        group__tab="personal",
        group__slug="personal",
        system_key="full_name",
    ).update(is_enabled=True)


class Migration(migrations.Migration):
    dependencies = [("employees", "0023_seed_name_fields")]
    operations = [migrations.RunPython(hide_full_name, show_full_name)]
