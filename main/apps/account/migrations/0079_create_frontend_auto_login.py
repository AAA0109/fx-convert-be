from django.db import migrations

from main.apps.core.models import Config


def create_frontend_auto_login(app, schema_editor):
    Config.objects.update_or_create(
        defaults={
            'path': 'admin/frontend/login_path',
        },
        value={
            'path': 'auto',
            'token_param': 'token',
            'extra_query_params': {}
        })


class Migration(migrations.Migration):
    dependencies = [
        ('account', '0078_alter_cashflow_currency_alter_draftcashflow_currency'),
    ]

    operations = [
        migrations.RunPython(create_frontend_auto_login)
    ]
