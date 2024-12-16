# Generated by Django 4.2.10 on 2024-03-27 16:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0023_currency_populate_unit'),
        ('cashflow', '0009_cashflowgenerator_periodicity_end_date'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cashflowgenerator',
            old_name='from_currency',
            new_name='buy_currency',
        ),
        migrations.RenameField(
            model_name='cashflowgenerator',
            old_name='to_currency',
            new_name='sell_currency',
        ),
        migrations.AlterField(
            model_name='cashflowgenerator',
            name='lock_side',
            field=models.ForeignKey(blank=True, help_text="The side of the transaction being locked, either 'buy' or 'sell'.", null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_lock_side', to='currency.currency'),
        ),
    ]