import os
import sys

import matplotlib.pyplot as plt
import pandas as pd
from hdlib.AppUtils.log_util import get_logger, logging

logger = get_logger(level=logging.INFO)

if __name__ == '__main__':
    # Setup environ
    sys.path.append(os.getcwd())
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings.local")

    # Setup django
    import django

    django.setup()
    from main.apps.currency.models import FxPair
    from scripts.feature.utils import _get_filters, get_data_anomaly, _extend_with_datacut, _get_ai_forecaster_pairs
    from main.apps.marketdata.models import DataCut, FxEstimator, FxSpotVol

    cut_type_list = [
        DataCut.CutType.EOD,
        # DataCut.CutType.BENCHMARK
    ]
    start_date = "2022-01-01"
    end_date = None  # "2023-07-01"  # Date.to_date("2021-01-01")
    list_of_pairs = _get_ai_forecaster_pairs()
    for i in list_of_pairs:
        try:
            _asset = FxPair.get_pair(i)
            list_ = []
            for est in ["Covar-Prod", "AI Vol Forecaster"]:
                estimator = FxEstimator.get_estimator(est)
                filters = _get_filters(start_date, end_date, cut_type_list)
                filters['estimator'] = estimator
                filters['pair_id'] = _asset.id

                qs = FxSpotVol.objects.filter(**filters)
                df_fxspotvol = pd.DataFrame(list(qs.all().values()))
                df_fxspotvol.set_index("date", inplace=True)
                df_fxspotvol.sort_index(inplace=True)
                df_fxspotvol = _extend_with_datacut(df_fxspotvol)
                aa = df_fxspotvol[['vol']]
                aa.columns = [est]
                list_.append(aa)

                # indentify missing days and anomaly
                missing_days_df, non_bdays_df, duplicated_dates = get_data_anomaly(df_fxspotvol)

            if duplicated_dates.sum() > 0:
                print("Duplicated dates found:")
                print(df_fxspotvol[duplicated_dates])
            # plot data
            df_combined = pd.merge(list_[0], list_[1], left_index=True, right_index=True, how='left')
            df_combined.plot()
            plt.title(f'asset no {_asset.name} ({_asset.id})')
            # plt.savefig(f'/home/victor/victor/pangea/hedgedesk_dashboard/scripts/feature/plots/{_asset.id}_{_asset.name.replace("/","")}.png')
            plt.show()
            print("done")

        except:
            logger.warning(f"Error in asset {i}")
            continue
