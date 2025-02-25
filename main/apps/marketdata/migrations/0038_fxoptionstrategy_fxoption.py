# Generated by Django 4.2.11 on 2024-05-22 12:45

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("currency", "0025_auto_20240514"),
        ("marketdata", "0037_fxforward_delivery_days_fxforward_expiry_days_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="FxOptionStrategy",
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
                ("date", models.DateTimeField()),
                (
                    "file",
                    models.FileField(
                        blank=True,
                        default=None,
                        null=True,
                        upload_to="data_store/option_strategy_by_date_and_pair",
                    ),
                ),
                (
                    "data_cut",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="marketdata.datacut",
                    ),
                ),
            ],
            options={"abstract": False,},
        ),
        migrations.CreateModel(
            name="FxOption",
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
                ("date", models.DateTimeField()),
                ("acquired_date", models.DateField(default=django.utils.timezone.now)),
                (
                    "file",
                    models.FileField(
                        blank=True,
                        default=None,
                        null=True,
                        upload_to="data_store/option_by_date_and_pair",
                    ),
                ),
                (
                    "storage_type",
                    models.CharField(
                        choices=[
                            ("local_storage", "Local Storage"),
                            ("sftp", "SFTP"),
                            ("gcs", "Google Cloud Storage"),
                        ],
                        max_length=255,
                    ),
                ),
                (
                    "data_cut",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="marketdata.datacut",
                    ),
                ),
                (
                    "pair",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="currency.fxpair",
                    ),
                ),
            ],
            options={"abstract": False,},
        ),
    ]
