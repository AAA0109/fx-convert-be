import os
import sys
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd
from hdlib.AppUtils.log_util import get_logger, logging

logger = get_logger(level=logging.INFO)


def get_data(
    asset,
    cut_types: list,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    _filter_params = _get_filters(start_date, end_date, cut_types)

    qs = asset.fxspotrange_set.filter(**_filter_params)
    if not qs.exists():
        return pd.DataFrame()
    df = pd.DataFrame(list(qs.all().values()))
    return df


if __name__ == '__main__':
    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()
    from main.apps.currency.models import FxPair
    from scripts.feature.utils import _extend_with_datacut, get_data_anomaly, _get_filters, get_dir_to_store_plot, \
        convert_missing_dates_to_ranges
    from main.apps.marketdata.models import DataCut

    cut_types = [
        DataCut.CutType.EOD,
    ]
    start_date = None  # "2022-09-01"
    end_date = None  # "2023-07-01"
    pair_ids = [i for i in range(1, 94)]
    # pair_ids = [1]
    for i in pair_ids:
        try:
            asset = FxPair.get_pair(i)
            df_out = get_data(
                asset=asset,
                cut_types=cut_types,
                start_date=start_date,
                end_date=end_date,
            )
            if df_out.empty:
                continue

            df_out = _extend_with_datacut(df_out)
            df_out[["close"]].plot(marker='.', ms=5)
            plt.title(f'asset: {asset.name}')

            dir_name = get_dir_to_store_plot('fxspotrange', start_date, end_date)

            fig_name = f'{asset.id}_{asset.name.replace("/", "")}.png'
            plt.savefig(dir_name + fig_name)
            plt.show()
            print(f'asset no {asset.id} {asset.name}')
            missing_days_df, non_bdays_df, duplicated_dates = get_data_anomaly(df_out)
            missing_data_range_df = convert_missing_dates_to_ranges(missing_days_df)
            print(missing_data_range_df)
            missing_data_name = f'missing_range_{asset.id}_{asset.name.replace("/", "")}.csv'
            missing_data_range_df.to_csv(dir_name + missing_data_name)
            print('=======================================================')
        except:
            logger.warning(f"Error in asset {i}")
            continue
