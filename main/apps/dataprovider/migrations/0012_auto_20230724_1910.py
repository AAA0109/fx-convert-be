# Generated by Django 3.2.8 on 2023-07-24 19:10

from django.db import migrations

from main.apps.dataprovider.scripts.patch_scripts.data_cut_fixer import DataCutFixer
from main.apps.dataprovider.scripts.patch_scripts.duplicates_removal.dst_violation import DstViolationRemover
from main.apps.dataprovider.scripts.patch_scripts.duplicates_removal.reuters_fxforward import ReuterFxForwardRemover
from main.apps.dataprovider.scripts.patch_scripts.incorrect_cut_remover import IncorrectCutRemover

"""remove_reuter (when there are duplicates, remove the reuter ones)"""


def remove_reuter_fxforward(apps, schema_editor):
    FxForward = apps.get_model('marketdata', 'FxForward')
    ReuterFxForwardRemover(FxForward, 'tenor').execute()


"""fix_dst_violation (when there are duplicates, choose the one that follows DST rule)"""


def fix_dst_violation_fxforward(apps, schema_editor):
    FxForward = apps.get_model('marketdata', 'FxForward')
    DstViolationRemover(FxForward, 'tenor').execute()


def fix_dst_violation_fxspotvol(apps, schema_editor):
    FxSpotVol = apps.get_model('marketdata', 'FxSpotVol')
    DstViolationRemover(FxSpotVol, 'estimator_id').execute()


"""fix_datacut (re-assign datacut and date to the correct one if there are still incorrect date after step 1 and 2)"""


def fix_datacut_fxforward(apps, schema_editor):
    FxForward = apps.get_model('marketdata', 'FxForward')
    DataCutFixer(FxForward).execute()


def fix_datacut_fxspot(apps, schema_editor):
    FxSpot = apps.get_model('marketdata', 'FxSpot')
    DataCutFixer(FxSpot).execute()


def fix_datacut_fxspotvol(apps, schema_editor):
    FxSpotVol = apps.get_model('marketdata', 'FxSpotVol')
    DataCutFixer(FxSpotVol).execute()


"""remove_incorrect_datacut"""


def remove_incorrect_cuts(apps, schema_editor):
    IncorrectCutRemover().execute()


class Migration(migrations.Migration):
    dependencies = [
        ('dataprovider', '0011_auto_20230619_2046'),
    ]

    operations = [
        migrations.RunPython(remove_reuter_fxforward),
        migrations.RunPython(fix_dst_violation_fxforward),
        migrations.RunPython(fix_dst_violation_fxspotvol),
        migrations.RunPython(fix_datacut_fxforward),
        migrations.RunPython(fix_datacut_fxspot),
        migrations.RunPython(fix_datacut_fxspotvol),
        migrations.RunPython(remove_incorrect_cuts),
    ]
