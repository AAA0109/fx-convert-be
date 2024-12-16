# Generated by Django 4.2.3 on 2023-12-07 17:55

from django.db import migrations

import logging

logger = logging.getLogger(__name__)


def populate_ibkr_supported_fxpair(app, schema_editor):
    FxPair = app.get_model('currency', 'FxPair')
    SupportedFxPair = app.get_model('ibkr', 'SupportedFxPair')
    supported_pairs = [
        {"base_currency": "AUD", "quote_currencies": ["CAD", "CHF", "CNH", "HKD", "JPY", "NZD", "SGD", "USD", "ZAR"]},
        {"base_currency": "BGN", "quote_currencies": ["USD"]},
        {"base_currency": "CAD", "quote_currencies": ["CHF", "CNH", "JPY"]},
        {"base_currency": "CHF",
         "quote_currencies": ["CNH", "CZK", "DKK", "HUF", "JPY", "NOK", "PLN", "SEK", "TRY", "ZAR"]},
        {"base_currency": "CNH", "quote_currencies": ["HKD", "JPY"]},
        {"base_currency": "DKK", "quote_currencies": ["JPY", "NOK", "SEK"]},
        {"base_currency": "EUR",
         "quote_currencies": ["AED", "AUD", "CAD", "CHF", "CNH", "CZK", "DKK", "GBP", "HKD", "HUF", "ILS", "JPY", "MXN",
                              "NOK", "NZD", "PLN", "RUB", "SAR", "SEK", "SGD", "TRY", "USD", "ZAR"]},
        {"base_currency": "GBP",
         "quote_currencies": ["AUD", "CAD", "CHF", "CNH", "CZK", "DKK", "HKD", "HUF", "JPY", "MXN", "NOK", "NZD", "PLN",
                              "SEK", "SGD", "TRY", "USD", "ZAR"]},
        {"base_currency": "HKD", "quote_currencies": ["JPY"]},
        {"base_currency": "KRW", "quote_currencies": ["AUD", "CAD", "CHF", "EUR", "GBP", "HKD", "JPY", "USD"]},
        {"base_currency": "MXN", "quote_currencies": ["JPY"]},
        {"base_currency": "NOK", "quote_currencies": ["JPY", "SEK"]},
        {"base_currency": "NZD", "quote_currencies": ["CAD", "CHF", "JPY", "USD"]},
        {"base_currency": "RON", "quote_currencies": ["USD"]},
        {"base_currency": "SEK", "quote_currencies": ["JPY"]},
        {"base_currency": "SGD", "quote_currencies": ["CNH", "HKD", "JPY"]},
        {"base_currency": "USD",
         "quote_currencies": ["AED", "BGN", "CAD", "CHF", "CNH", "CZK", "DKK", "HKD", "HUF", "ILS", "JPY", "KRW", "MXN",
                              "NOK", "PLN", "RON", "RUB", "SAR", "SEK", "SGD", "TRY", "ZAR"]},
        {"base_currency": "ZAR", "quote_currencies": ["JPY"]}
    ]
    pairs_to_create = []
    for supported_pair in supported_pairs:
        base_currency = supported_pair['base_currency']
        for quote_currency in supported_pair['quote_currencies']:
            pair = FxPair.objects.get(base_currency__mnemonic=base_currency, quote_currency__mnemonic=quote_currency)
            _pair = SupportedFxPair(fxpair=pair)
            logger.debug(f"Adding {base_currency}/{quote_currency} to IBKR supported list")
            pairs_to_create.append(_pair)
    SupportedFxPair.objects.bulk_create(pairs_to_create)


class Migration(migrations.Migration):
    dependencies = [
        ('ibkr', '0029_supportedfxpair'),
    ]

    operations = [
        migrations.RunPython(populate_ibkr_supported_fxpair)
    ]