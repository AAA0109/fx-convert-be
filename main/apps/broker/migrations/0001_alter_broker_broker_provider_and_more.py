# Generated by Django 4.2.11 on 2024-05-02 00:10

from django.db import migrations, models
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('broker', 'auto_20240501_4567'),
    ]

    operations = [
        migrations.AlterField(
            model_name='broker',
            name='broker_provider',
            field=models.CharField(blank=True, choices=[('CORPAY', 'CORPAY'), ('IBKR', 'IBKR'), ('CORPAY_MP', 'CORPAY_MP'), ('VERTO', 'VERTO'), ('NIUM', 'NIUM'), ('AZA', 'AZA'), ('MONEX', 'MONEX'), ('CONVERA', 'CONVERA'), ('OFX', 'OFX'), ('XE', 'XE'), ('OANDA', 'OANDA'), ('AIRWALLEX', 'AIRWALLEX')], max_length=50),
        ),
        migrations.AlterField(
            model_name='broker',
            name='execution_method',
            field=models.CharField(choices=[('asynchronous', 'Asynchronous'), ('synchronous', 'Synchronous'), ('manual', 'Manual')], max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='broker',
            name='maximum_rfq_expiry',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='broker',
            name='minimum_rfq_expiry',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='broker',
            name='supported_execution_types',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('rfq', 'rfq'), ('quote_lock', 'quote_lock'), ('limit', 'limit'), ('market', 'market'), ('twap', 'twap'), ('vwap', 'vwap'), ('voice', 'voice')], help_text='Supported execution types', max_length=43, null=True),
        ),
        migrations.AlterField(
            model_name='broker',
            name='supported_instruments',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('forward', 'Forward'), ('future', 'Future'), ('base_future', 'BaseFuture'), ('continuous_future', 'ContinuousFuture'), ('cash_equity', 'CashEquity'), ('option', 'Option'), ('spot', 'Spot'), ('window_forward', 'Window Forward'), ('ndf', 'Ndf'), ('swap', 'Swap'), ('nds', 'Nds'), ('rtp', 'Realtime Payment'), ('continuous_spot', 'Continuous Spot')], help_text='Supported instrument', max_length=116, null=True),
        ),
    ]
