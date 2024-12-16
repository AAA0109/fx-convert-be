# Generated by Django 4.2.11 on 2024-05-03 14:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketdata', '0035_init2_secmaster'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instrument',
            name='instrument_type',
            field=models.CharField(blank=True, choices=[('fxrate', 'FxRate'), ('forward', 'Forward'), ('future', 'Future'), ('base_future', 'BaseFuture'), ('continuous_future', 'ContinuousFuture'), ('cash_equity', 'CashEquity'), ('option', 'Option'), ('spot', 'Spot'), ('window_forward', 'Window Forward'), ('ndf', 'Ndf'), ('swap', 'Swap'), ('nds', 'Nds'), ('rtp', 'Realtime Payment'), ('continuous_spot', 'Continuous Spot'), ('currency', 'Currency')], help_text='instrument type', null=True),
        ),
    ]