from django.db import migrations, models
import django.db.models.deletion


NEW_HIRE_SECTIONS = [
    {
        "id": "work_details",
        "name": "Деталі роботи",
        "fields": [
            {"id": "photo", "name": "Фото", "field_type": "photo", "required": False},
            {"id": "hired_on", "name": "Дата прийому на роботу", "field_type": "date", "required": True},
            {"id": "employment_history", "name": "Досвід до прийому на роботу", "field_type": "textarea", "required": False},
            {"id": "position", "name": "Посада", "field_type": "select", "required": True},
            {"id": "work", "name": "Робота", "field_type": "group", "required": True},
            {"id": "teams", "name": "Команди", "field_type": "multi_select", "required": False},
        ],
    }
]


DEFAULT_FORM_TEMPLATES = [
    (
        "new_hire",
        "Повна зайнятість Vidnova Clinic Запоріжжя",
        "Базова форма найму для повної зайнятості у Запоріжжі.",
        NEW_HIRE_SECTIONS,
    ),
    (
        "new_hire",
        "Повна зайнятість Vidnova Clinic Львів",
        "Базова форма найму для повної зайнятості у Львові.",
        NEW_HIRE_SECTIONS,
    ),
    (
        "new_hire",
        "Часткова зайнятість Vidnova Clinic Запоріжжя",
        "Базова форма найму для часткової зайнятості у Запоріжжі.",
        NEW_HIRE_SECTIONS,
    ),
    (
        "new_hire",
        "Часткова зайнятість Vidnova Clinic Львів",
        "Базова форма найму для часткової зайнятості у Львові.",
        NEW_HIRE_SECTIONS,
    ),
    ("preboarding", "Пребординг", "Підготовка працівника до першого робочого дня.", []),
    ("people_data_change", "Оновлення особистих даних", "Запит на зміну персональних даних працівника.", []),
    ("people_data_change", "Зміна контактів", "Запит на оновлення контактної інформації.", []),
    ("people_data_change", "Зміна адреси", "Запит на оновлення адреси працівника.", []),
    ("self_service", "Запит на самообслуговування", "Самостійне оновлення особистих даних працівником.", []),
    ("custom_request", "Запит активів", "Кастомний запит на видачу або повернення активів.", []),
    ("custom_request", "Відшкодування витрат", "Кастомний запит на компенсацію витрат.", []),
    ("custom_request", "Довідка", "Кастомний запит на підготовку довідки.", []),
    ("custom_request", "Обладнання", "Кастомний запит щодо робочого обладнання.", []),
    ("custom_request", "Кастомний запит", "Загальна форма для нетипових HR-запитів.", []),
    ("termination", "Звільнення", "Запит на звільнення працівника.", []),
]


def seed_form_templates(apps, schema_editor):
    EmployeeFormTemplate = apps.get_model("employees", "EmployeeFormTemplate")
    for form_type, name, description, sections in DEFAULT_FORM_TEMPLATES:
        EmployeeFormTemplate.objects.get_or_create(
            form_type=form_type,
            name=name,
            defaults={
                "description": description,
                "sections": sections,
                "allow_employee_access": True,
                "is_active": True,
            },
        )


def unseed_form_templates(apps, schema_editor):
    EmployeeFormTemplate = apps.get_model("employees", "EmployeeFormTemplate")
    names = [name for _, name, _, _ in DEFAULT_FORM_TEMPLATES]
    EmployeeFormTemplate.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0017_holidaypolicy_clinic_holiday_policy_ref_holiday"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmployeeFormTemplate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "form_type",
                    models.CharField(
                        choices=[
                            ("new_hire", "New hire"),
                            ("preboarding", "Preboarding"),
                            ("people_data_change", "People data change"),
                            ("self_service", "Self service"),
                            ("custom_request", "Custom request"),
                            ("termination", "Termination"),
                        ],
                        db_index=True,
                        max_length=40,
                    ),
                ),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("allow_employee_access", models.BooleanField(default=True)),
                ("workflow_name", models.CharField(blank=True, max_length=180)),
                ("allow_requester_disable_workflow", models.BooleanField(default=False)),
                ("absence_policy_names", models.JSONField(blank=True, default=list)),
                ("sections", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "preboarding_form",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="hire_form_templates",
                        to="employees.employeeformtemplate",
                    ),
                ),
            ],
            options={
                "ordering": ["form_type", "name"],
                "indexes": [
                    models.Index(fields=["form_type", "is_active"], name="employee_form_type_active_idx"),
                    models.Index(fields=["is_active", "name"], name="employee_form_active_name_idx"),
                ],
            },
        ),
        migrations.RunPython(seed_form_templates, unseed_form_templates),
    ]
