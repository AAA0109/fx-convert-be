# Generated by Django 4.2.10 on 2024-03-11 18:51

from django.db import migrations
from django.conf import settings

from main.apps.oems.backend.utils import load_yml, Expand
from main.apps.marketdata.models.ref.instrument import InstrumentTypes
from main.apps.marketdata.models.ref.instrument import Instrument

import logging

logger = logging.getLogger(__name__)

"""
class InstrumentTypes(models.TextChoices):
    FXRATE = "fxrate", _("FxRate")
    FORWARD = "forward", _("Forward")
    FUTURE = 'future', _("Future")
    BASE_FUTURE = 'base_future', _("BaseFuture")
    CONTINUOUS_FUTURE = 'continuous_future', _("ContinuousFuture")
    CASH_EQUITY = 'cash_equity','CashEquity'
    OPTION = "option", _("Option")
    SPOT = "spot", _("Spot")
    WINDOW_FORWARD = "window_forward","Window Forward"
    NDF = "ndf", _("Ndf")
    SWAP = "swap", _("Swap")
    NDS = "nds", _("Nds")
    RTP = "rtp", _("Realtime Payment")
    CONTINUOUS_SPOT = 'continuous_spot', 'Continuous Spot'
"""

def update_sec_master(app, schema_editor):

    for instrument in Instrument.objects.iterator():
        if '-BROKEN' in instrument.name:
            instrument.name = instrument.name.replace('BROKEN','FORWARD')
            instrument.save()

# ====================

class Migration(migrations.Migration):
    dependencies = [
        ('marketdata', '0041_remove_optionstrategy_data_cut_and_more'),
    ]

    operations = [
        migrations.RunPython(update_sec_master),
    ]