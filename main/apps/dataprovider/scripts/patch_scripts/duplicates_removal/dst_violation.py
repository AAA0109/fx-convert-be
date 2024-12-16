from typing import Type

import pandas as pd

from main.apps.dataprovider.scripts.utils import get_revision_df, is_dst, extract_incorrect_date, remove_duplicates
from main.apps.marketdata.models import DataCut, MarketData

pd.options.mode.chained_assignment = None


class DstViolationRemover(object):

    def __init__(self, model_class: Type[MarketData], identifier: str):
        self.model_class = model_class
        self.identifier = identifier
        self.revision_df, df_sorted = get_revision_df()

    def execute(self):
        pair_ids = [i for i in range(1, 94)]
        # pair_ids = [8, ]
        for pair_id in pair_ids:
            qs_eod_pair = self.model_class.objects.filter(data_cut__cut_type=DataCut.CutType.EOD, pair_id=pair_id)
            identifiers = [item[self.identifier] for item in qs_eod_pair.values(self.identifier).distinct()]
            for t in identifiers:
                print("=======================================================")
                print(f"pair_id: {pair_id}, identifier: {t}")
                qs_each_kind = qs_eod_pair.filter(**{self.identifier: t})
                self._extractor(qs_each_kind)

    def _extractor(self, qs_each_kind):
        df = pd.DataFrame(list(qs_each_kind.values()))
        df.rename(columns={"id": "marketdata_id"}, inplace=True)
        datacut_df = pd.DataFrame(list(DataCut.objects.filter(cut_type=DataCut.CutType.EOD).values())).rename(
            columns={"id": "data_cut_id"})
        df = pd.merge(df, datacut_df, on='data_cut_id', how='left')
        df['hour'] = df["cut_time"].dt.hour
        df['date_group'] = df["cut_time"].dt.date
        df = df.sort_values(['date_group', 'hour'], ascending=[True, False])
        df.loc[:, 'is_dst'] = df["cut_time"].apply(is_dst)
        df_all_duplicates = df[df.duplicated(subset=['date_group'], keep=False)]
        df_test = df[['cut_time', 'data_cut_id']].set_index('cut_time')
        missing_days_df, non_bdays_df = extract_incorrect_date(df_test)
        print(f"missing_days_df : {missing_days_df.shape[0]}")
        print(f"non_bdays_df : {non_bdays_df.shape[0]}")

        self.df_all_duplicates = df_all_duplicates
        self.qs_each_kind = qs_each_kind
        self.df = df
        self._subprocess()

    def _subprocess(self, ):
        remove_duplicates(
            self.df_all_duplicates,
            self.qs_each_kind,
            self.df,
            self.revision_df,
        )
