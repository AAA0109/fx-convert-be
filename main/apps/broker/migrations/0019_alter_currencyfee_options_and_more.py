# Generated by Django 4.2.15 on 2024-09-19 14:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0029_auto_20240825_0646'),
        ('broker', '0018_remove_configurationtemplate_broker_markup'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='currencyfee',
            options={'ordering': ['buy_currency__mnemonic'], 'verbose_name': 'Broker Fees'},
        ),
        migrations.RenameField(
            model_name='currencyfee',
            old_name='currency',
            new_name='buy_currency',
        ),
        migrations.AlterUniqueTogether(
            name='currencyfee',
            unique_together={('broker', 'buy_currency')},
        ),
        migrations.AddField(
            model_name='currencyfee',
            name='instrument_type',
            field=models.CharField(choices=[('fxrate', 'FxRate'), ('forward', 'Forward'), ('future', 'Future'), ('base_future', 'BaseFuture'), ('continuous_future', 'ContinuousFuture'), ('cash_equity', 'CashEquity'), ('option', 'Option'), ('spot', 'Spot'), ('window_forward', 'Window Forward'), ('ndf', 'Ndf'), ('swap', 'Swap'), ('nds', 'Nds'), ('rtp', 'Realtime Payment'), ('continuous_spot', 'Continuous Spot'), ('currency', 'Currency')], max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='currencyfee',
            name='sell_currency',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='broker_fee_sell_currency', to='currency.currency'),
        ),
    ]
