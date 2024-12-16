from django.db import migrations


def create_config(apps, schema_editor):
    Config = apps.get_model('core', 'Config')
    Config.objects.update_or_create(
        path='volatility/movement/threshold',
        defaults=dict(
            value={
                "1D": {"vol": {"percentage": 20}, "price": {"std": 3, "percentage": 1}},
                "1W": {"vol": {"percentage": 20}, "price": {"std": 3, "percentage": 2}},
                "1M": {"vol": {"percentage": 20}, "price": {"std": 3, "percentage": 3}},
                "3M": {"vol": {"percentage": 20}, "price": {"std": 3, "percentage": 5}}
            }
        )
    )


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_config)
    ]
