# Generated by Django 4.2.7 on 2024-02-21 23:08

from django.db import migrations


def add_fx_pair(apps, schema_editor):
    Currency = apps.get_model('currency', 'Currency')
    FxPair = apps.get_model('currency', 'FxPair')

    eur = Currency.objects.get(mnemonic='EUR')
    saf = Currency.objects.get(mnemonic='SAF')

    FxPair.objects.get_or_create(
        base_currency=eur,
        quote_currency=saf
    )
    FxPair.objects.get_or_create(
        base_currency=saf,
        quote_currency=eur
    )


class Migration(migrations.Migration):
    dependencies = [
        ('dataprovider', '0025_added_usdsaf_to_fxpair'),
    ]

    operations = [
        migrations.RunPython(add_fx_pair),
    ]
