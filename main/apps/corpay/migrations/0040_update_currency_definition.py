from django.db import migrations


def update_currency_definition(apps, schema_editor):
    CurrencyDefinition = apps.get_model('corpay', 'CurrencyDefinition')
    symbol_list = [
        'ARS', 'BHD', 'BRL', 'CLP', 'CNY', 'COP', 'IDR', 'ILS',
        'INR', 'JOD', 'KES', 'KRW', 'KWD', 'MAD', 'MYR', 'OMR',
        'PEN', 'PHP', 'QAR', 'RON', 'SAR', 'TRY', 'TWD', 'UGX'
    ]

    qs = CurrencyDefinition.objects.filter(currency__mnemonic__in=symbol_list)

    for instance in qs:
        instance.fwd_delivery_buying = False
        instance.fwd_delivery_selling = False
        instance.save()


class Migration(migrations.Migration):
    dependencies = [
        ('corpay', '0039_merge_0037_spotrate_0038_corpaysettings_max_horizon'),
    ]

    operations = [
        migrations.RunPython(update_currency_definition)
    ]
