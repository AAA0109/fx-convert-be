# Generated by Django 4.2.15 on 2024-08-25 07:52

from django.db import migrations

def add_missing_instruments(apps, schema_editor):
    spot_instruments = [
        'CADUGX',
        'USDETB',
        'USDMWK',
        'USDTZS',
        'USDXOF'
    ]
    fwd_instruments = [
        'CADUGX'
    ]
    tenors = [
        'FWD',
        'ON',
        'TN',
        'SN',
        'SW',
        '1W',
        '2W',
        '3W',
        '1M',
        '2M',
        '3M',
        '4M',
        '5M',
        '6M',
        '7M',
        '8M',
        '9M',
        '1Y',
        'IMM1',
        'IMM2',
        'IMM3',
        'IMM4',
        'EOM1',
        'EOM2',
        'EOM3',
        'EOM4',
        'EOM5',
        'EOM6',
        'EOM7',
        'EOM8',
        'EOM9',
        'EOM10',
        'EOM11',
        'EOM12',
    ]
    Instrument = apps.get_model('marketdata', 'Instrument')
    for spot_instrument in spot_instruments:
        Instrument.objects.get_or_create(
            name=f"{spot_instrument}-SPOT",
            defaults={
                "instrument_type": 'spot',
                "tradable_instrument": True,
                "base_instrument": spot_instrument
            }

        )
    for fwd_instrument in fwd_instruments:
        for tenor in tenors:
            Instrument.objects.get_or_create(
                name=f"{fwd_instrument}-{tenor}",
                defaults={
                    "instrument_type": 'ndf',
                    "tradable_instrument": True,
                    "base_instrument": fwd_instrument,
                }

            )

class Migration(migrations.Migration):

    dependencies = [
        ('marketdata', '0043_change_instr_name_again'),
    ]

    operations = [
        migrations.RunPython(add_missing_instruments),
    ]
