# Generated by Django 4.2.15 on 2024-11-08 09:16

from django.db import migrations


import logging
from django.apps.registry import Apps
from django.db import migrations

from main.apps.marketdata.models import InstrumentTypes
from main.apps.oems.backend.utils import load_yml, Expand


logger = logging.getLogger(__name__)


def update_sec_master(apps:Apps, schema_editor):
    INSTRUMENTS_TO_UPDATE = [
        'CADGHS', 'GHSCAD'
    ]
    path = Expand(__file__) + '/../../oems/cfgs/CCY_REFERENCE.yml'
    ref_data = load_yml(path)
    Instrument = apps.get_model('marketdata', 'Instrument')

    for mkt, data in ref_data.items():
        if mkt not in INSTRUMENTS_TO_UPDATE:
            continue
        instrument, created = Instrument.objects.get_or_create(name=mkt)

        symbology = data.pop('SYMBOLOGY')
        instrument.name = mkt
        instrument.instrument_type = InstrumentTypes.FXRATE
        instrument.tradable_instrument = False
        instrument.base_instrument = None
        instrument.reference = data
        instrument.symbology = symbology
        instrument.save()
        logger.debug(f"Creating {mkt}!")

        for tenor in ('RTP', 'SPOT', 'FWD', 'WINDOW'):

            mkt_nm = f'{mkt}-{tenor}'
            sub_instr, created = Instrument.objects.get_or_create(name=mkt_nm)
            sub_instr.name = mkt_nm
            sub_instr.tradable_instrument = True
            sub_instr.base_instrument = mkt

            if tenor == 'SPOT':
                sub_instr.instrument_type = InstrumentTypes.SPOT
            elif tenor == 'RTP':
                sub_instr.instrument_type = InstrumentTypes.RTP
            elif tenor == 'FWD':
                if data['CCY_TYPE'] == 'Spot':
                    sub_instr.instrument_type = InstrumentTypes.FORWARD
                elif data['CCY_TYPE'] == 'NDF':
                    sub_instr.instrument_type = InstrumentTypes.NDF
                else:
                    print(data['CCY_TYPE'])
                    raise
            elif tenor == 'WINDOW':
                if data['CCY_TYPE'] == 'Spot':
                    sub_instr.instrument_type = InstrumentTypes.WINDOW_FORWARD
                else:
                    continue

            logger.debug(f"Creating {mkt_nm}!")
            sub_instr.save()
        if "TENORS" in data:
            for tenor in data['TENORS']:

                if tenor == 'SPOT': continue

                mkt_nm = f'{mkt}-{tenor}'
                sub_instr, created = Instrument.objects.get_or_create(name=mkt_nm)
                sub_instr.name = mkt_nm
                sub_instr.tradable_instrument = True
                sub_instr.base_instrument = mkt

                if data['CCY_TYPE'] == 'Spot':
                    sub_instr.instrument_type = InstrumentTypes.FORWARD
                elif data['CCY_TYPE'] == 'NDF':
                    sub_instr.instrument_type = InstrumentTypes.NDF
                else:
                    print(data['CCY_TYPE'])
                    raise

                logger.debug(f"Creating {mkt_nm}!")
                sub_instr.save()

        else:
            instrument.reference = data
            instrument.save()

def remove_cad_ghs_instrument(apps:Apps, schema_editor):
    Instrument = apps.get_model('marketdata', 'Instrument')
    INSTRUMENTS_TO_DELETE = [
        'CADGHS', 'GHSCAD'
    ]
    for pair in INSTRUMENTS_TO_DELETE:
        instruments = Instrument.objects.filter(name__contains=pair).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('marketdata', '0047_add_instrument_data_for_sle_and_rwf'),
    ]

    operations = [
        migrations.RunPython(update_sec_master, remove_cad_ghs_instrument)
    ]
