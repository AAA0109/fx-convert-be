# Generated by Django 3.2.8 on 2023-03-19 03:43

from django.db import migrations, models

from main.apps.broker.models import BrokerAccountCapability


def seed_broker_account_capabilities(apps, schema_editor):
    model = apps.get_model('account', 'BrokerAccountCapability')
    backtest = model(type=BrokerAccountCapability.Types.BACKTEST)
    backtest.save()
class Migration(migrations.Migration):

    dependencies = [
        ('account', '0073_auto_20230316_2331'),
    ]

    operations = [
        migrations.AlterField(
            model_name='brokeraccountcapability',
            name='type',
            field=models.CharField(choices=[('trade', 'Trade'), ('fund', 'Fund'), ('backtest', 'Backtest')], max_length=10, unique=True),
        ),
        migrations.RunPython(seed_broker_account_capabilities)
    ]
