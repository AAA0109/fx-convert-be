# Generated by Django 3.2.8 on 2023-08-08 20:53
import logging
from django.db import migrations

logger = logging.getLogger(__name__)


def seed_data(apps, schema_editor):
    currencies_settings = {
        'p10': [
            'CAD', 'MXN', 'CNY', 'CNH', 'EUR', 'JPY', 'KRW', 'GBP', 'TWD', 'INR', 'VND', 'USD'
        ],
        'wallet': [
            'JPY', 'CAD', 'USD', 'GHS', 'AUD', 'MXN', 'TWD', 'GBP', 'ILS', 'INR', 'EUR', 'CZK', 'HKD',
            'BGN', 'BHD', 'BRL', 'BWP', 'CHF', 'CNH', 'DKK', 'HUF', 'IDR', 'JOD', 'KES', 'KWD', 'LSL',
            'NOK', 'NZD', 'OMR', 'PLN', 'QAR', 'RON', 'SAR', 'SEK', 'SGD', 'THB', 'TND', 'TRY', 'UGX',
            'ZAR', 'AED'
        ],
        'wallet_api': [
            'AED', 'AUD', 'MXN', 'BGN', 'NOK', 'BHD', 'NZD', 'OMR', 'CAD', 'CHF', 'PLN', 'CNH', 'QAR',
            'CZK', 'RON', 'DKK', 'EUR', 'GBP', 'SEK', 'SGD', 'HKD', 'THB', 'HUF', 'TND', 'ILS', 'TRY',
            'UGX', 'JPY', 'USD', 'KES', 'ZAR', 'KWD', 'SAR'
        ],
        'ndf': [
            'ARS', 'BRL', 'CLP', 'CNH', 'CNY', 'COP', 'IDR', 'INR', 'KES', 'KRW', 'KWD', 'MAD', 'MYR',
            'PHP', 'TWD', 'ZMW'
        ]
    }

    transformed_data = {}

    for currency in set(sum(currencies_settings.values(), [])):
        transformed_data[currency] = {setting: currency in currencies_settings.get(setting, []) for setting in
                                      currencies_settings}

    CurrencyDefinition = apps.get_model('corpay', 'CurrencyDefinition')
    Currency = apps.get_model('currency', 'Currency')

    currency_definitions_to_create = []

    for mnemonic, settings in transformed_data.items():
        try:
            currency = Currency.objects.get(mnemonic=mnemonic)
            currency_definitions_to_create.append(CurrencyDefinition(currency=currency, **settings))
        except Currency.DoesNotExist:
            logger.error(f"{mnemonic} does not exist, unable to add currency definition")
            continue
    CurrencyDefinition.objects.bulk_create(currency_definitions_to_create)




class Migration(migrations.Migration):
    dependencies = [
        ('corpay', '0016_currencydefinition'),
        ('currency', '0007_auto_20230808_2148')
    ]

    operations = [
        migrations.RunPython(seed_data),
    ]
