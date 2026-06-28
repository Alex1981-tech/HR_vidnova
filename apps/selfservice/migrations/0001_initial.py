from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserPreference",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("language", models.CharField(choices=[("en", "English"), ("uk", "Українська"), ("pl", "Polski")], default="uk", max_length=8)),
                ("theme", models.CharField(choices=[("light", "Light"), ("dark", "Dark"), ("auto", "Auto")], default="light", max_length=12)),
                ("time_zone", models.CharField(default="Europe/Kyiv", max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="hr_preferences", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["user_id"],
            },
        ),
    ]
