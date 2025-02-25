# Generated by Django 4.2.11 on 2024-04-18 16:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0023_currency_populate_unit'),
        ('cashflow', '0016_cashflowgenerator_cntr_amount_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cashflowgenerator',
            name='hedge_strategy',
        ),
        migrations.RemoveField(
            model_name='cashflowgenerator',
            name='self_directed',
        ),
        migrations.AlterField(
            model_name='cashflowgenerator',
            name='lock_side',
            field=models.ForeignKey(blank=True, help_text='ISO 4217 Standard 3-Letter Currency Code used to indicate which amount you are defining the value of. The non-Lockside amount will be calculated.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_lock_side', to='currency.currency'),
        ),
        migrations.AlterField(
            model_name='cashflowgenerator',
            name='value_date',
            field=models.DateField(help_text='The date when the transaction will settle. Defaults to the following business day if settlement cannot occur on the provided value_date.', null=True),
        ),
        migrations.AlterField(
            model_name='singlecashflow',
            name='lock_side',
            field=models.ForeignKey(blank=True, help_text='ISO 4217 Standard 3-Letter Currency Code used to indicate which amount you are defining the value of. The non-Lockside amount will be calculated.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='%(class)s_lock_side', to='currency.currency'),
        ),
    ]
