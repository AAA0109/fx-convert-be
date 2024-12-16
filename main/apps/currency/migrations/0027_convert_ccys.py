# Generated by Django 4.2.10 on 2024-03-11 18:51

from django.db import migrations

from main.apps.currency.models import Currency

def update_currencies(app, schema_editor):

    update = {
        'KRF': 0,
        'XAF': 0,
        'XOF': 0,
        'MWK': 0,
        'TZS': 0,
        'NPR': 0,
        'CNH': 2,
    }

    for ccy in Currency.objects.iterator():
        if ccy.unit is None:
            ccy.unit = update.get(ccy.mnemonic, 2)
            ccy.save()


class Migration(migrations.Migration):
    dependencies = [
        ('currency', '0026_alter_currency_country_alter_currency_unit'),
    ]

    operations = [
        migrations.RunPython(update_currencies),
    ]
