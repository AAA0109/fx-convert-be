import pandas as pd

from main.apps.dataprovider.scripts.patch_scripts.duplicates_removal.dst_violation import DstViolationRemover


def is_reuter(df: pd.DataFrame):
    df['is_reuter'] = ((df['depo_base'] == 0) & (df['depo_quote'] == 0))
    return df


class ReuterFxForwardRemover(DstViolationRemover):

    def _subprocess(self, ):
        if not self.df_all_duplicates['date_group'].is_unique:
            print("REMOVAL REUTERS DATA")
            self.df_all_duplicates = is_reuter(self.df_all_duplicates)
            df_reuters = self.df_all_duplicates[self.df_all_duplicates['is_reuter']]
            if not df_reuters.empty:
                print("Remove REUTERS from db")
                qs_removed = self.qs_each_kind.filter(id__in=df_reuters["marketdata_id"].tolist())
                qs_removed.delete()
