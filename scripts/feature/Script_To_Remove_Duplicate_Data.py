import os
import sys

import numpy as np
import pandas as pd
from pytz import timezone

utc_tz = timezone('UTC')
eastern_tz = timezone('US/Eastern')


def _get_fx_pair_name_map() -> dict:
    fx_pairs = FxPair.objects.all()
    mappings = {}
    for fx_pair in fx_pairs:
        mappings[fx_pair.id] = fx_pair.name
    return mappings


if __name__ == '__main__':
    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()
    from main.apps.marketdata.models import FxSpot, DataCut
    from main.apps.currency.models import FxPair
    from scripts.feature.utils import extract_incorrect_date

    cut_type = DataCut.CutType.EOD

    datacut_df = pd.DataFrame(list(DataCut.objects.filter(cut_type=cut_type).values())).rename(
        columns={"id": "data_cut_id"})
    fxspot_df = pd.DataFrame(list(FxSpot.objects.filter(data_cut__cut_type=cut_type).values()))

    fx_pair_name_map = _get_fx_pair_name_map()
    fxspot_df["asset"] = fxspot_df["pair_id"].apply(lambda x: fx_pair_name_map[x])

    fxspot_cut_df = pd.merge(fxspot_df, datacut_df, on='data_cut_id', how='left')
    fxspot_cut_df = fxspot_cut_df.rename(columns={"id": "fxspot_id"})

    # fxspot_cut_df['is_dst'] = fxspot_cut_df['cut_time'].apply(is_dst)

    pair_ids = [i for i in range(1,94)]
    for pair_id in pair_ids:
        fxspot_cut_pair_df = fxspot_cut_df[fxspot_cut_df['pair_id'] == pair_id].copy()
        if fxspot_cut_pair_df.empty:
            continue
        fxspot_cut_pair_df.reset_index(inplace=True, drop=True)
        # added columns required for selection
        fxspot_cut_pair_df = fxspot_cut_pair_df.copy()
        fxspot_cut_pair_df['hour'] = fxspot_cut_pair_df["cut_time"].dt.hour
        fxspot_cut_pair_df['date_group'] = fxspot_cut_pair_df["cut_time"].dt.date

        fxspot_cut_pair_df['is_rate_distance_close'] = fxspot_cut_pair_df.apply(
            lambda row: np.isclose(row['rate'], row['rate_bid'], rtol=1e-07, atol=1e-07)
                        and np.isclose(row['rate_bid'], row['rate_ask'], rtol=1e-07,
                                       atol=1e-07), axis=1)
        fxspot_cut_pair_df['is_rate_distance_close'] = fxspot_cut_pair_df['is_rate_distance_close'].astype(int)
        # Sort values
        df_sorted = fxspot_cut_pair_df.sort_values(['date_group', 'hour', 'is_rate_distance_close', 'fxspot_id'],
                                                   ascending=[True, False, False, False])
        if not df_sorted.index.is_unique:
            raise ValueError("Index is not unique")

        # Drop duplicates
        df_kept = df_sorted.drop_duplicates(subset=['date_group'], keep='first')

        df_removed = df_sorted.loc[~df_sorted.index.isin(df_kept.index)]
        if df_removed.empty:
            continue

        asset = FxPair.get_pair(pair_id)
        print(f"===============asset no {asset.name} ({asset.id})=====================")
        print("================Before Cleaning=====================")
        duplicated_dates = fxspot_cut_pair_df['date_group'].duplicated()
        print(f"# of duplicated dates before cleaning is {duplicated_dates.sum()}")

        df_test = fxspot_cut_pair_df[['cut_time', 'fxspot_id']].set_index('cut_time')
        missing_days_df, non_bdays_df = extract_incorrect_date(df_test)
        print(f"missing_days_df before cleaning : {missing_days_df.shape[0]}")
        print(f"non_bdays_df before cleaning : {non_bdays_df.shape[0]}")

        print("=====================================")
        print(f"{len(df_removed)} duplicated dates for pair {pair_id}")
        print(df_removed)
        print("================After Cleaning=====================")
        duplicated_dates = df_kept['date_group'].duplicated()
        print(f"# of duplicated dates after cleaning is {duplicated_dates.sum()}")

        df_test = df_kept[['cut_time', 'fxspot_id']].set_index('cut_time')
        missing_days_df, non_bdays_df = extract_incorrect_date(df_test)
        print(f"missing_days_df after cleaning : {missing_days_df.shape[0]}")
        print(f"non_bdays_df after cleaning : {non_bdays_df.shape[0]}")
        # FxSpot.objects.filter(id__in=df_removed["fxspot_id"].tolist()).delete()
