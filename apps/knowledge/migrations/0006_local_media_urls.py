from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("knowledge", "0005_restore_peopleforce_category_tree"),
    ]

    operations = [
        migrations.AlterField(
            model_name="knowledgedocument",
            name="cover_url",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AlterField(
            model_name="knowledgeattachment",
            name="source_url",
            field=models.URLField(blank=True, max_length=1000),
        ),
    ]
