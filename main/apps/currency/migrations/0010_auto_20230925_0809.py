# Generated by Django 4.2 on 2023-09-25 08:09

from django.db import migrations

from main.apps.currency.scripts.create_currencies import create_fx_pairs


def add_fxpairs(apps, schema_editor):
    """
    Adds a set of Fx pairs, and currencies to support them, to the DB.

    See https://docs.djangoproject.com/en/4.1/ref/migration-operations/ for information on RunPython.
    """
    fxpairs = ["AUDCAD", "AUDCHF", "AUDCNH", "AUDHKD", "AUDJPY", "AUDNZD", "AUDSGD", "AUDZAR", "BGNUSD",
               "CADCHF", "CADCNH", "CADJPY", "CHFCNH", "CHFCZK", "CHFDKK", "CHFHUF", "CHFJPY", "CHFNOK",
               "CHFPLN", "CHFSEK", "CHFTRY", "CHFZAR", "CNHHKD", "CNHJPY", "DKKJPY", "DKKNOK", "DKKSEK",
               "EURAUD", "EURCAD", "EURCHF", "EURCNH", "EURCZK", "EURDKK", "EURGBP", "EURHKD", "EURHUF",
               "EURJPY", "EURMXN", "EURNOK", "EURNZD", "EURPLN", "EURRUB", "EURSAR", "EURSEK", "EURSGD",
               "EURZAR", "GBPAUD", "GBPCAD", "GBPCHF", "GBPCNH", "GBPCZK", "GBPDKK", "GBPHKD", "GBPHUF",
               "GBPJPY", "GBPMXN", "GBPNOK", "GBPNZD", "GBPPLN", "GBPSEK", "GBPSGD", "GBPTRY", "EURAED",
               "GBPZAR", "HKDJPY", "KRWAUD", "KRWCAD", "KRWCHF", "KRWEUR", "KRWGBP", "KRWHKD", "EURILS",
               "KRWJPY", "MXNJPY", "NOKJPY", "NOKSEK", "NZDCAD", "NZDCHF", "NZDJPY", "RONUSD", "EURTRY",
               "SARUSD", "SEKJPY", "SGDCNH", "SGDHKD", "SGDJPY", "ZARJPY"]
    create_fx_pairs(fxpairs=fxpairs, allow_cross_currency_pairs=True, add_reverse_pairs=True)


class Migration(migrations.Migration):
    dependencies = [
        ('currency', '0009_merge_20230907_1337'),
    ]

    operations = [
        migrations.RunPython(add_fxpairs)
    ]