import logging
from typing import List, Type
from django.db import connection

from main.apps.marketdata.models import DataCut, MarketData
from main.apps.marketdata.models.fx.rate import CorpayFxForward

logger = logging.getLogger(__name__)


class CorpayFxDuplicateDataRemover(object):

    def __init__(self, model_class: Type[MarketData]):
        self.model_class = model_class

    def execute(self):
        logger.debug(f"Start removing duplicated data from {self.model_class.objects.model._meta.db_table}")

        tenor_groupby = ", tenor" if isinstance(self.model_class(), CorpayFxForward) else ""

        query = f"""
            SELECT * FROM (
                SELECT string_agg(CAST(id as VARCHAR), ',') as ids, COUNT(id) as count, date, pair_id {tenor_groupby}
                FROM {self.model_class.objects.model._meta.db_table}
                GROUP BY date, pair_id {tenor_groupby}
            ) a
            WHERE a.count > 1
        """

        with connection.cursor() as cursor:
            removed_ids: List[int] = []
            removed_data_cut_ids: List[int] = []
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                ids = row[0].split(',')
                for id in ids[1:]:
                    removed_ids.append(id)
                    corpay_fx_data = self.model_class.objects.get(id=id)
                    removed_data_cut_ids.append(corpay_fx_data.data_cut.pk)

            self.model_class.objects.filter(id__in=removed_ids).delete()
            # DataCut.objects.filter(id__in=removed_data_cut_ids).delete()

            logger.debug(f"{len(removed_ids)} duplicated data removed")


