# Generated by Django 4.2.7 on 2024-02-17 03:54

from django.db import migrations


def populate_config(apps, schema_editor):
    Config = apps.get_model('core', 'Config')

    config = {
        "currencies": ["USD", "EUR"],
        "mode": "quote"
    }

    obj, created = Config.objects.update_or_create(
        path='system/fxpair/supported_home_currencies',
        defaults={'value': config}
    )


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0002_populate_config_table'),
    ]

    operations = [
        migrations.RunPython(populate_config),
    ]
