from django.core.management.base import BaseCommand

from main.apps.dataprovider.scripts.patch_scripts.strategic_execution.corpay_fx_datacut_fixer import CorpayFxDataCutFixer
from main.apps.dataprovider.scripts.patch_scripts.strategic_execution.corpay_fx_duplicate_remover import CorpayFxDuplicateDataRemover
from main.apps.marketdata.models.fx.rate import CorpayFxForward, CorpayFxSpot


class Command(BaseCommand):
    help = 'Corpay fx datacut fixer and duplicated data remover'

    def handle(self, *args, **options):
        for model_class in [CorpayFxForward, CorpayFxSpot]:
            duplicate_remover = CorpayFxDuplicateDataRemover(model_class=model_class)
            duplicate_remover.execute()
            datacut_fixer = CorpayFxDataCutFixer(model_class=model_class)
            datacut_fixer.execute()
