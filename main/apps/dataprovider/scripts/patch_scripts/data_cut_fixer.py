from typing import Type

from main.apps.dataprovider.scripts.utils import get_revision_df
from main.apps.marketdata.models import DataCut, MarketData


class DataCutFixer(object):

    def __init__(self, model_class: Type[MarketData]):
        self.model_class = model_class
        self.revision_df, _ = get_revision_df()

    def execute(self):
        for idx, row in self.revision_df.iterrows():
            new_cut = DataCut.objects.get(id=row["correct_datacut_id"])
            qs = self.model_class.objects.filter(data_cut_id=row["data_cut_id"])
            print(f"revised {self.model_class._meta.model_name} count={qs.count()}: ", row["data_cut_id"], "->",
                  row["correct_datacut_id"])
            qs.update(data_cut=new_cut, date=new_cut.cut_time)
