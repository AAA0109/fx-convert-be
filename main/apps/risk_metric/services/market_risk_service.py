from typing import List, Iterable, Set

import numpy as np
from hdlib.DateTime.DayCounter import DayCounter_HD

from hdlib.DateTime.Date import Date
from main.apps.account.models import CompanyTypes, Company, Account
from main.apps.account.services.cashflow_provider import CashFlowProviderService

from main.apps.currency.models import FxPair, FxPairTypes
from main.apps.marketdata.models import FxSpotVol, FxSpot


class MarketRiskService:
    @staticmethod
    def get_market_changes(reference_time: Date, fxpairs: Iterable[FxPair], lookback_windows=None,
                           estimator_id: int = 3):
        output = {}
        for fxpair in fxpairs:
            changes_response = MarketRiskService.get_market_changes_for_fxpair(reference_time=reference_time,
                                                                               fxpair=fxpair,
                                                                               lookback_windows=lookback_windows,
                                                                               estimator_id=estimator_id)
            output[str(fxpair)] = changes_response
        return output

    @staticmethod
    def get_market_changes_for_company(reference_time: Date, company: CompanyTypes,
                                       estimator_id: int = 3):
        """
        Get the market changes for all the FX pairs that a company has exposure to.
        Calls the get_market_changes function after determining the nonzero exposures of a company.
        """
        company = Company.get_company(company)

        accounts = Account.get_active_accounts(company=company, live_only=True)
        provider = CashFlowProviderService()
        fxpairs: Set[FxPair] = set()
        for account in accounts:
            exposures = provider.get_cash_exposures_for_account(time=reference_time, account=account).net_exposures()
            for fxpair, _ in exposures.items():
                fxpairs.add(fxpair)

        return MarketRiskService.get_market_changes(reference_time=reference_time,
                                                    fxpairs=fxpairs,
                                                    estimator_id=estimator_id)

    @staticmethod
    def get_market_changes_for_fxpair(reference_time: Date, fxpair: FxPairTypes, lookback_windows=None,
                                      estimator_id: int = 3):
        """
        Returns data on how the market prices and volatility for an FxPair have changed over several lookback windows.

        Example output format:
            {
                "1D": {
                    "data": [
                        "price: {
                            "topday": [date],
                            "lookback_date": [date],
                            "std": [VALUE],
                            "percentage": [VALUE]
                        },
                        "vol: {
                            "topday": [date],
                            "lookback_date": [date],
                            "vol_points": [VALUE],
                            "percentage": [VALUE]
                        }
                    ]
                },
                .... (other lookback windows)
            }
        """
        dc = DayCounter_HD()

        fxpair = FxPair.get_pair(fxpair)

        if lookback_windows is None:
            lookback_windows = ["1D", "1W", "1M", "3M"]

        # Get spot and vol as of reference time.
        opt = FxSpotVol.get_spot_vol(fxpair=fxpair, estimator=estimator_id, date=reference_time)
        if not opt:
            raise ValueError(f"no vol data for {fxpair} at reference time {reference_time}.")
        vol_value, vol_topday = opt

        opt = FxSpot.get_spot(fxpair=fxpair, date=reference_time)
        if not opt:
            raise ValueError(f"no spot data for {fxpair} at reference time {reference_time}.")
        spot_value, spot_topday = opt

        # Get the EWMA vol for the lookback windows
        output = {}
        for lookback in lookback_windows:
            lookback_days = MarketRiskService._period_string_to_days(period=lookback)

            vol_lookback_date = spot_topday - lookback_days
            opt = FxSpotVol.get_spot_vol(fxpair, estimator=estimator_id, date=vol_lookback_date)
            if not opt:
                continue
            vol, vol_date = opt

            spot_lookback_date = vol_topday - lookback_days
            opt = FxSpot.get_spot(fxpair, date=spot_lookback_date)
            if not opt:
                continue
            spot, spot_date = opt

            # Compute the percentage change in spot.
            spot_percentage = 100 * (spot - spot_value) / spot_value

            # Compute the change in spot as a standard deviation with respect to vol
            spot_time = dc.year_fraction(start=spot_date, end=spot_topday)
            spot_sigma = vol_value * np.sqrt(spot_time)
            spot_std = np.log(spot / spot_value) / spot_sigma

            # Compute the percentage change in vol.
            vol_percentage = 100 * (vol - vol_value) / vol_value

            # Compute vol time - we will need this for doing a vol "sigma" change calculation.
            # vol_time = dc.year_fraction(start=vol_date, end=vol_topday)

            # Compute absolute difference in vol, i.e. vol change measured in vol points.
            vol_points = vol - vol_value

            output[lookback] = {
                "price": {
                    "topday": spot_topday,
                    "lookback_date": spot_date,
                    "std": spot_std,
                    "percentage": spot_percentage,
                },
                "vol": {
                    "topday": vol_topday,
                    "lookback_date": vol_date,
                    "vol_points": vol_points,
                    "percentage": vol_percentage,
                },
            }
        return output

    @staticmethod
    def _period_string_to_days(period: str):
        """
        Convert a string representing a period of time to a number of days. For example, "1D" -> 1 day, "1W" -> 7 days,
        "1M" -> 30 days, "1Y" -> 365 days.
        """

        # Extract the number from the string.
        number = int(period[:-1])
        # Extract the unit from the string.
        unit = period[-1]

        units_to_days = {"D": 1, "W": 7, "M": 30, "Y": 365}
        # Get the unit from the units_to_days dictionary, if it exists.
        if unit not in units_to_days:
            raise ValueError(f"unit {unit} not recognized.")
        return number * units_to_days[unit]
