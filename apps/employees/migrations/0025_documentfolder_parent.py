import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("employees", "0024_hide_full_name_field")]

    operations = [
        migrations.AddField(
            model_name="employeedocumentfolder",
            name="parent",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="children",
                to="employees.employeedocumentfolder",
            ),
        ),
    ]
