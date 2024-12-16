# Generated by Django 4.2.11 on 2024-05-03 14:04

from django.db import migrations
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('broker', '0002_alter_broker_supported_instruments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='broker',
            name='supported_instruments',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('fxrate', 'FxRate'), ('forward', 'Forward'), ('future', 'Future'), ('base_future', 'BaseFuture'), ('continuous_future', 'ContinuousFuture'), ('cash_equity', 'CashEquity'), ('option', 'Option'), ('spot', 'Spot'), ('window_forward', 'Window Forward'), ('ndf', 'Ndf'), ('swap', 'Swap'), ('nds', 'Nds'), ('rtp', 'Realtime Payment'), ('continuous_spot', 'Continuous Spot'), ('currency', 'Currency')], help_text='Supported instrument', max_length=132, null=True),
        ),
    ]
