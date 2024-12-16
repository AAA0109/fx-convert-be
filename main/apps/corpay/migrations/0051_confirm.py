import django.db.models.deletion
import django_extensions.db.fields
from django.db import migrations, models


def create_gmail_config(apps, *_):
    Config = apps.get_model('core', 'Config')
    Config.objects.update_or_create(
        defaults={
            'path': 'vendor/google/gmail',
        },
        value={
            "web": {
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "client_id": "576427127304-47amhjpa91e1kao09lo2pgftqdgahnap.apps.googleusercontent.com",
                "token_uri": "https://oauth2.googleapis.com/token",
                "project_id": "pangea-development",
                "client_secret": "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",
                "redirect_uris": [
                    "https://api.internal.dev.pangea.io",
                    "https://app.dev.pangea.io",
                    "http://127.0.0.1:8000/api/gmail/authenticate"
                ],
                "javascript_origins": [
                    "https://api.internal.dev.pangea.io",
                    "https://app.dev.pangea.io",
                    "http://127.0.0.1:8000"
                ],
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
            }
        }
    )


class Migration(migrations.Migration):
    dependencies = [
        ("corpay", "0050_merge_20240408_1627"),
    ]

    operations = [
        migrations.CreateModel(
            name="Confirm",
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
                (
                    "confirm_type",
                    models.CharField(
                        choices=[("forward", "Forward"), ("spot", "Spot")], max_length=7
                    ),
                ),
                ("deal_number", models.CharField(max_length=15)),
                (
                    "order_number",
                    models.CharField(blank=True, max_length=15, null=True),
                ),
                ("content", models.JSONField()),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="account.company",
                    ),
                ),
            ],
            options={
                "get_latest_by": "modified",
                "abstract": False,
            },
        ),
        migrations.RunPython(create_gmail_config)
    ]
