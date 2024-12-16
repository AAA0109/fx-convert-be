"""
Script that deletes duplicated marketdata_corpayfxspot and marketdata_corpayfxforward and change the datacut cut time second and microseconds to 0
"""

import os
import sys

from scripts.lib.only_local import only_allow_local


def run():
    from main.apps.dataprovider.scripts.patch_scripts.strategic_execution.corpay_fx_datacut_fixer import CorpayFxDataCutFixer
    from main.apps.dataprovider.scripts.patch_scripts.strategic_execution.corpay_fx_duplicate_remover import CorpayFxDuplicateDataRemover
    from main.apps.marketdata.models.fx.rate import CorpayFxForward, CorpayFxSpot

    for model_class in [CorpayFxForward, CorpayFxSpot]:
        duplicate_remover = CorpayFxDuplicateDataRemover(model_class=model_class)
        duplicate_remover.execute()
        datacut_fixer = CorpayFxDataCutFixer(model_class=model_class)
        datacut_fixer.execute()

    print("Corpay fx forward and spot duplicated data removed and datacut seconds and microseconds set to 0")


if __name__ == '__main__':
    # If the connected DB is the remote (real) server, do not allow the program to run.
    only_allow_local()

    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()

    run()
