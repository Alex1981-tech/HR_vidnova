from django.db import migrations


def names(model):
    return list(model.objects.values_list("name", flat=True))


def seed(apps, schema_editor):
    Group = apps.get_model("employees", "EmployeeFieldGroup")
    Table = apps.get_model("employees", "EmployeeFieldTable")
    Position = apps.get_model("employees", "Position")
    Department = apps.get_model("employees", "Department")
    Division = apps.get_model("employees", "Division")
    Clinic = apps.get_model("employees", "Clinic")
    JobLevel = apps.get_model("employees", "JobLevel")
    EmploymentType = apps.get_model("employees", "EmploymentType")
    WorkingPattern = apps.get_model("employees", "WorkingPattern")

    # «Робота» = лише таблиці (PF-стиль). Прибираємо старі work-групи з полями.
    Group.objects.filter(tab="work", slug__in=["position", "team"]).delete()

    work_group, _ = Group.objects.get_or_create(
        tab="work",
        slug="job",
        defaults={"name": "Робота", "is_system": True, "order": 0},
    )

    posady_columns = [
        {"key": "die_z", "label": "Діє з", "type": "date"},
        {"key": "menedzher", "label": "Менеджер", "type": "employee"},
        {"key": "riven", "label": "Рівень посади", "type": "select", "options": names(JobLevel)},
        {"key": "posada", "label": "Посада", "type": "select", "options": names(Position)},
        {"key": "departament", "label": "Департамент", "type": "select", "options": names(Department)},
        {"key": "pidrozdil", "label": "Підрозділ", "type": "select", "options": names(Division)},
        {"key": "lokatsiya", "label": "Локація", "type": "select", "options": names(Clinic)},
        {"key": "yur_osoba", "label": "Юридична особа", "type": "text"},
    ]
    robota_columns = [
        {"key": "die_z", "label": "Діє з", "type": "date"},
        {"key": "tip_roboti", "label": "Тип роботи", "type": "select", "options": names(EmploymentType)},
        {"key": "grafik", "label": "Графік роботи", "type": "select", "options": names(WorkingPattern)},
        {"key": "vypr_termin", "label": "Випробний термін", "type": "text"},
        {"key": "vypr_kinec", "label": "Випр. термін закінчується", "type": "date"},
        {"key": "komentar", "label": "Коментар", "type": "textarea"},
    ]
    Table.objects.get_or_create(
        group=work_group, name="Посади", defaults={"columns": posady_columns, "is_enabled": True, "order": 0}
    )
    Table.objects.get_or_create(
        group=work_group, name="Робота", defaults={"columns": robota_columns, "is_enabled": True, "order": 1}
    )

    comp_group = Group.objects.filter(tab="compensation", slug="compensation").order_by("order").first()
    if comp_group is None:
        comp_group = Group.objects.create(tab="compensation", slug="compensation", name="Компенсація", is_system=True, order=0)

    currencies = ["UAH", "USD", "EUR", "PLN"]
    bazova_columns = [
        {"key": "die_z", "label": "Діє з", "type": "date"},
        {"key": "suma", "label": "Сума", "type": "number"},
        {"key": "valyuta", "label": "Валюта", "type": "select", "options": currencies},
        {"key": "period", "label": "Період", "type": "select", "options": ["На годину", "На день", "На місяць", "На рік"]},
        {"key": "grafik_oplaty", "label": "Графік оплати", "type": "select", "options": ["Щомісяця", "Двічі на місяць", "Щотижня"]},
        {"key": "pereprac", "label": "Перепрацювання", "type": "boolean"},
        {"key": "komentar", "label": "Коментар", "type": "textarea"},
    ]
    dodatkovi_columns = [
        {"key": "vyd", "label": "Вид компенсації", "type": "select", "options": ["Бонус", "Премія", "Надбавка", "Інше"]},
        {"key": "opys", "label": "Опис", "type": "text"},
        {"key": "tip_vyplaty", "label": "Тип виплати", "type": "select", "options": ["Разова", "Регулярна"]},
        {"key": "chastota", "label": "Частота", "type": "select", "options": ["Разово", "Щомісяця", "Щокварталу", "Щороку"]},
        {"key": "pochynaetsya", "label": "Починається", "type": "date"},
        {"key": "data_zavershennya", "label": "Дата завершення", "type": "date"},
        {"key": "suma", "label": "Сума", "type": "number"},
        {"key": "valyuta", "label": "Валюта", "type": "select", "options": currencies},
    ]
    Table.objects.get_or_create(
        group=comp_group, name="Базова компенсація", defaults={"columns": bazova_columns, "is_enabled": True, "order": 0}
    )
    Table.objects.get_or_create(
        group=comp_group, name="Додаткові компенсації", defaults={"columns": dodatkovi_columns, "is_enabled": True, "order": 1}
    )


def unseed(apps, schema_editor):
    Table = apps.get_model("employees", "EmployeeFieldTable")
    Group = apps.get_model("employees", "EmployeeFieldGroup")
    Table.objects.filter(name__in=["Посади", "Робота", "Базова компенсація", "Додаткові компенсації"]).delete()
    Group.objects.filter(tab="work", slug="job").delete()


class Migration(migrations.Migration):
    dependencies = [("employees", "0021_employee_social_telegram_fields")]
    operations = [migrations.RunPython(seed, unseed)]
