from urllib.parse import quote

from django.db import migrations, models


def seed_company_links(apps, schema_editor):
    CompanyLink = apps.get_model("employees", "CompanyLink")
    defaults = [
        ("Vidnova", "https://vidnova.ua/"),
        ("Instagram Vidnova", "https://www.instagram.com/vidnova.clinic/"),
        ("CMMS система", "https://cmms.vidnova.app/"),
        ("Фотопротоколи", "https://photo.vidnova.app/"),
    ]
    for index, (title, url) in enumerate(defaults, start=1):
        CompanyLink.objects.get_or_create(
            title=title,
            defaults={
                "url": url,
                "icon_url": f"https://www.google.com/s2/favicons?domain_url={quote(url, safe='')}&sz=64",
                "order": index,
                "is_active": True,
            },
        )


def unseed_company_links(apps, schema_editor):
    CompanyLink = apps.get_model("employees", "CompanyLink")
    CompanyLink.objects.filter(title__in=["Vidnova", "Instagram Vidnova", "CMMS система", "Фотопротоколи"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0029_set_work_table_sync_targets"),
    ]

    operations = [
        migrations.CreateModel(
            name="CompanyLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("title", models.CharField(max_length=180)),
                ("url", models.URLField(max_length=1000)),
                ("icon_url", models.URLField(blank=True, max_length=1000)),
                ("order", models.PositiveIntegerField(db_index=True, default=0)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["order", "title"],
                "indexes": [models.Index(fields=["is_active", "order"], name="company_link_active_order_idx")],
            },
        ),
        migrations.RunPython(seed_company_links, unseed_company_links),
    ]
