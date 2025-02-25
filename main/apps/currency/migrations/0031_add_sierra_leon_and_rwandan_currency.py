# Generated by Django 4.2.15 on 2024-10-22 02:10
import logging
from django.db import migrations
from django.apps.registry import Apps


logger = logging.getLogger(__name__)


def add_sierra_leon_n_rwandan_currency_pairs(app:Apps, schema_editor):
    currencies_data = {
        "SLE": {
            "name": "Sierra Leonean Leone",
            "symbol": "Le",
            "mnemonic": "SLE",
            "numeric_code": 925,
            "unit": 2,
            "country": "Sierra Leone"

        },
        "RWF": {
            "name": "Rwandan franc",
            "symbol": "FRw",
            "mnemonic": "RWF",
            "numeric_code": 646,
            "unit": 0,
            "country": "Rwanda"
        }
    }

    Currency = app.get_model("currency", "Currency")
    FxPair = app.get_model('currency', 'FxPair')

    for mnemonic, currency_data in currencies_data.items():
        currency, created = Currency.objects.get_or_create(
            mnemonic=mnemonic,
            defaults={
                "name": currency_data["name"],
                "symbol": currency_data["symbol"],
                "mnemonic": currency_data["mnemonic"],
                "numeric_code": currency_data["numeric_code"],
                "unit": currency_data["unit"],
                "country": currency_data["country"],
                "category": "other"
            }
        )

    base_currencies = Currency.objects.all()
    currencies = Currency.objects.all()

    pairs_to_create = []

    for base_currency in base_currencies:
        for quote_currency in currencies:
            if not FxPair.objects.filter(base_currency=base_currency, quote_currency=quote_currency).exists():
                logger.debug(f"Pair missing {base_currency.mnemonic}/{quote_currency.mnemonic}, creating new pair!")
                pair = FxPair(
                    base_currency=base_currency,
                    quote_currency=quote_currency
                )
                pairs_to_create.append(pair)
    FxPair.objects.bulk_create(pairs_to_create)


class Migration(migrations.Migration):

    dependencies = [
        ('currency', '0030_country'),
    ]

    operations = [
        migrations.RunPython(add_sierra_leon_n_rwandan_currency_pairs,
                             migrations.RunPython.noop)
    ]
