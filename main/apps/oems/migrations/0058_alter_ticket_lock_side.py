# Generated by Django 4.2.11 on 2024-04-09 18:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0023_currency_populate_unit'),
        ('oems', '0057_alter_ticket_lock_side_alter_ticket_tenor'),
    ]

    operations = [
        # migrations.AlterField(
        #     model_name='ticket',
        #     name='lock_side',
        #     field=models.ForeignKey(blank=True, help_text='ISO 4217 Standard 3-Letter Currency Code used to reference the amount of currency.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lock_side_currency_ticket', to='currency.currency'),
        # ),
    ]
