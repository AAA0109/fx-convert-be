# Generated by Django 4.2.11 on 2024-06-03 14:39

from django.db import migrations, models
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ("dataprovider", "0036_alter_profile_extract_for_profile_ids"),
    ]

    operations = [
        migrations.CreateModel(
            name="CollectorConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name="modified"
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("active", models.BooleanField(default=True)),
                ("collector", models.CharField(max_length=255)),
                ("write_to_bq", models.BooleanField(default=False)),
                ("kwargs", models.JSONField(default=dict)),
            ],
            options={"get_latest_by": "modified", "abstract": False,},
        ),
    ]
