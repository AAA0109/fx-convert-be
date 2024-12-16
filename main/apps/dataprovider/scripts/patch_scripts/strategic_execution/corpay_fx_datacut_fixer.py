import logging
from typing import List, Type
from django.db import connection
from django.db.utils import IntegrityError

from main.apps.marketdata.models import DataCut, MarketData

logger = logging.getLogger(__name__)


class CorpayFxDataCutFixer(object):

    def __init__(self, model_class: Type[MarketData]):
        self.model_class = model_class

    def get_unique_list(self, data: List[int]) -> List[int]:
        list_set = set(data)
        unique_list = (list(list_set))
        return unique_list

    def execute(self):
        logger.debug(f"Start fixing {self.model_class.objects.model._meta.db_table} datacut cut time")

        query = f"""
            SELECT string_agg(CAST(id as VARCHAR), ',') as ids, string_agg(CAST(data_cut_id as VARCHAR), ',') as datacut_ids, date
            FROM {self.model_class.objects.model._meta.db_table}
            GROUP BY date
            """

        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                marketdata_id_list: str = row[0]
                datacut_id_list: str = row[1]

                datacut_ids = self.get_unique_list([int(id) for id in datacut_id_list.split(",")])
                used_data_cut_id = None

                if len(datacut_ids) > 1:
                    # loop through datacut_ids to get an existing datacut
                    for datacut_id in datacut_ids:
                        try:
                            existing_datacut = DataCut.objects.get(id=datacut_id)
                            used_data_cut_id = existing_datacut.pk
                        except Exception as e:
                            used_data_cut_id = None

                    removed_datacut_ids = [id for id in datacut_ids if id != used_data_cut_id]

                    datacut = None

                    # update corpay fx data to use the first existing datacut_id
                    if used_data_cut_id:
                        datacut = DataCut.objects.get(id=used_data_cut_id)
                        ids_to_update = [int(id) for id in marketdata_id_list.split(",")]
                        self.model_class.objects.filter(id__in=ids_to_update).update(data_cut_id=datacut.pk)

                    # remove unused datacut
                    # if removed_datacut_ids:
                    #     DataCut.objects.filter(id__in=removed_datacut_ids).delete()

                    # replace seconds and microseconds part of the datacut cut_time
                    # if existing datacut cut_time exist update the corpay fx data to use that datacut instead
                    if datacut:
                        fixed_cut_time = datacut.cut_time.replace(second=0, microsecond=0)
                        try:
                            datacut.cut_time = fixed_cut_time
                            datacut.save()
                        except IntegrityError as ie:
                            conflicted_datacut = DataCut.objects.get(cut_time=fixed_cut_time)
                            self.model_class.objects.filter(data_cut=datacut).update(data_cut=conflicted_datacut)

        logger.debug(f"Finished fixing {self.model_class.objects.model._meta.db_table} datacut cut time")

