import os, sys
import pandas as pd

from scripts.lib.only_local import only_allow_local


def run():
    from main.apps.currency.models import FxPair
    from main.apps.marketdata.models.fx.rate import FxSpot
    from main.apps.marketdata.models.fx.estimator import FxEstimator, FxSpotVol, FxSpotCovariance
    from main.apps.marketdata.services.fx.fx_provider import FxVolAndCorrelationProvider
    from hdlib.DateTime.Date import Date
    from main.apps.marketdata.services.data_cut_service import DataCutService
    import numpy as np

    dates = [20220420, 20220421, 20220422]

    spots_dates = {20220420:
                       {'GBP/USD': 1.3908, 'EUR/USD': 1.1845, 'AUD/USD': 0.7385, 'CAD/USD': 0.7976,
                        'JPY/USD': 0.00912},
                   20220421:
                       {'GBP/USD': 1.3910, 'EUR/USD': 1.1847, 'AUD/USD': 0.7381, 'CAD/USD': 0.7971,
                        'JPY/USD': 0.00914},
                   20220422:
                       {'GBP/USD': 1.3915, 'EUR/USD': 1.1842, 'AUD/USD': 0.7389, 'CAD/USD': 0.7961,
                        'JPY/USD': 0.00922}
                   }

    insert_spots = True
    insert_vols = True
    insert_corrs = True

    vol_corr_provider = FxVolAndCorrelationProvider()

    for date in dates:
        ref_date = Date.from_int(date)

        # action_status, data_cut = DataCutService.create_cut(date=ref_date, cut_type=DataCut.CutType.EOD)
        # if not data_cut and action_status.is_error():
        #     raise ValueError(f"Error adding the data cut: {action_status}")
        data_cut = DataCutService.get_eod_cut(date=ref_date)

        fx_names = ['GBP/USD', 'EUR/USD', 'AUD/USD', 'CAD/USD', 'JPY/USD']
        pairs = {pair.name: pair for pair in FxPair.get_pairs_by_name(fx_names=fx_names)}

        vol_estimator = FxEstimator.get_estimator(1)
        corr_estimator = FxEstimator.get_estimator(2)

        # status, vol_estimator = FxEstimator.create_estimator(
        #     tag="EWMA Vol Default Estimator",
        #     type=FxEstimator.EstimatorType.EWMA,
        #     parameters="0.98")
        # print(status)
        #
        # status, corr_estimator = FxEstimator.create_estimator(
        #     tag="EWMA Corr. Default Estimator",
        #     type=FxEstimator.EstimatorType.EWMA,
        #     parameters="0.98")
        # print(status)

        vols = {'GBP/USD': 0.004119, 'EUR/USD': 0.0033656, 'AUD/USD': 0.00523, 'CAD/USD': 0.004507, 'JPY/USD': 0.00346}
        for pair in vols.keys():
            vols[pair] *= np.sqrt(252)  # Annualize

        spots = spots_dates[date]

        for pair_name, pair in pairs.items():
            if insert_spots:
                try:
                    status, spot = FxSpot.add_spot(data_cut=data_cut, pair=pair, rate=spots[pair_name])
                    print(status)
                except Exception as e:
                    print(e)
            if insert_vols:
                try:
                    status, spot = FxSpotVol.add_spot_vol(fxpair=pair, vol=vols[pair_name],
                                                          estimator=vol_estimator, data_cut=data_cut)
                    print(f"From add spot vol {status}")

                except Exception as e:
                    print(e)

        if insert_corrs:
            corrs = pd.DataFrame(index=fx_names, columns=fx_names,
                                 data=[[1, 0.661896477, 0.738515018, 0.60465711, 0.33044534],
                                       [0.661896477, 1, 0.709700733, 0.523912497, 0.544184462],
                                       [0.738515018, 0.709700733, 1, 0.716205242, 0.418823212],
                                       [0.60465711, 0.523912497, 0.716205242, 1, 0.097597462],
                                       [0.33044534, 0.544184462, 0.418823212, 0.097597462, 1]])

            for pair_name_1, pair_1 in pairs.items():
                for pair_name_2, pair_2 in pairs.items():
                    try:
                        correl = corrs.loc[pair_name_1, pair_name_2]
                        covar = correl * vols[pair_name_1] * vols[pair_name_2]
                        status, _, _ = FxSpotCovariance.add_spot_covariance(pair1=pair_1, pair2=pair_2,
                                                                            estimator=corr_estimator,
                                                                            covariance=covar, data_cut=data_cut)
                        print(f"From add spot covar: {status}")

                    except Exception as ex:
                        print(f"Exception adding spot covar: {ex}")

        fx_pairs = list(pairs.values())

        data_cut = DataCutService.get_eod_cut(date=ref_date)
        corr = FxSpotCovariance.get_correlation(pair_1=pairs["GBP/USD"], pair_2=pairs["EUR/USD"], data_cut=data_cut)
        print(corr)

        corr_mat = FxVolAndCorrelationProvider().get_spot_correl_matrix(pairs=fx_pairs, data_cut=data_cut)
        print(f"\nCorrelations: \n {corr_mat}")

        vols = vol_corr_provider.get_vol_map(pairs=fx_pairs, data_cut=data_cut)
        print(f"\nVols: \n {vols}")


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
