from collections import defaultdict

from hdlib.Universe.FX.FxUniverseCounterSwitcher import FxUniverseCounterSwitcher
from main.apps.account.models import CashFlow, iter_active_cashflows
from main.apps.currency.models import FxPair, FxPairTypes
from main.apps.marketdata.services.data_cut_service import DataCutService
from main.apps.marketdata.services.fx.fx_option_provider import InterpolatedAtmVolTermStructure, AtmVolTermStructure
from main.apps.marketdata.services.universe_provider import UniverseProviderService
from main.apps.account.models.account import Account, AccountTypes
from main.apps.account.services.cashflow_pricer import CashFlowPricerService
from main.apps.currency.models.currency import Currency, CurrencyTypes

from hdlib.Universe.Universe import Universe
from hdlib.DateTime.DayCounter import DayCounter_HD
from hdlib.Hedge.Fx.MinVar.PnLRiskCalculator import PnLRiskCalculator
from hdlib.DateTime.Calendar.Calendar import CustomCalendar
from hdlib.DateTime.Date import Date
from hdlib.Universe.Risk.CashFlowRiskEngine_MC import CashFlowRiskEngine_MC
from hdlib.Hedge.Fx.HedgeAccount import CashExposures_Cached, HedgeAccountSettings, HedgeMethod
from hdlib.Instrument.CashFlow import CashFlows
from hdlib.Core.AccountInterface import BasicAccount
from hdlib.Core.CompanyInterface import BasicCompany

from typing import Union, Sequence, Tuple, Optional, Dict, Iterable, List
import numpy as np
import pandas as pd
from scipy.stats import norm
import logging

logger = logging.getLogger(__name__)


class FxRiskService(object):
    def __init__(self,
                 universe_provider_service: UniverseProviderService = UniverseProviderService()):
        self._universe_provider_service = universe_provider_service
        self._fx_spot_provider = universe_provider_service.fx_spot_provider

    def get_single_fx_risk_cones(self,
                                 fx_pair: FxPairTypes,
                                 start_date: Date,
                                 end_date: Date,
                                 prob_levels: Optional[Sequence[float]] = (
                                     0.7, 0.95, 0.99),
                                 std_dev_levels: Optional[Sequence[float]] = (
                                     1, 2, 3),
                                 do_std_dev_cones: bool = True
                                 ) -> Dict[str, list]:

        # =========================
        # Begin Validations
        # =========================
        if fx_pair is None:
            raise RuntimeError("You must supply an fx_pair")

        fx_pair_ = FxPair.get_pair(pair=fx_pair)
        usd = Currency.get_currency('USD')
        if fx_pair_.quote != usd and fx_pair_.base != usd:
            raise NotImplementedError(
                "Currently we only support pairs of the form XXX/USD, USD/XXX")

        if not do_std_dev_cones:
            raise NotImplementedError(
                "Only std dev based cones are currently supported")

        if not prob_levels or len(prob_levels) == 0:
            prob_levels = (0.7, 0.95, 0.99)
        if not std_dev_levels or len(std_dev_levels) == 0:
            std_dev_levels = (1, 2, 3)

        for i in range(len(prob_levels)):
            if prob_levels[i] >= 1. or prob_levels[i] <= 0:
                raise ValueError(
                    "Prob levels must be within (0, 1), exclusive")

        # Round the start date down. If date was None, most date from most recent EOD data cut.
        if start_date is None:
            start_date = DataCutService.get_eod_cut().cut_time

        if end_date.start_of_next_day() <= start_date:
            raise ValueError(
                "End date must be the same or after start_date")

        # =========================
        # End Validations
        # =========================

        return self._get_single_fx_risk_cones_gaussian_model(fx_pair=fx_pair_,
                                                             start_date=start_date,
                                                             end_date=end_date,
                                                             prob_levels=prob_levels,
                                                             std_dev_levels=std_dev_levels,
                                                             do_std_dev_cones=do_std_dev_cones)

    def _get_single_fx_risk_cones_gaussian_model(self,
                                                 fx_pair: FxPair,
                                                 start_date: Date,
                                                 end_date: Date,
                                                 prob_levels: Optional[Sequence[float]] = (
                                                     0.7, 0.95, 0.99),
                                                 std_dev_levels: Optional[Sequence[float]] = (
                                                     1, 2, 3),
                                                 do_std_dev_cones: bool = True
                                                 ) -> Dict[str, list]:
        usd = Currency.get_currency('USD')
        domestic = fx_pair.quote

        # Construct the Financial Universe
        if domestic == usd:
            usd_pair = fx_pair
        else:
            usd_pair = FxPair.get_pair_from_currency(
                base_currency=fx_pair.quote, quote_currency=usd)

        universe_usd = self._universe_provider_service.make_cntr_currency_universe(
            ref_date=start_date,
            domestic=usd,
            fx_pairs=(usd_pair,),
            flat_forward=True,
            flat_discount=True)

        # NOTE: we dont need to switch universe if pair is of the form XXX/USD or USD/XXX
        universe = universe_usd

        spot = universe.fx_universe.fx_assets.get_fx_spot(pair=fx_pair)
        vol = universe.fx_universe.fx_vols.vol_spot(pair=fx_pair)

        if np.isnan(vol):
            raise RuntimeError(
                f"Nan Vols were retrieved from universe, likely missing data for: {fx_pair}")

        calendar = CustomCalendar.new_western_no_holidays()

        date = start_date
        dates = [start_date]
        means = [0.]

        uppers = []
        lowers = []

        num_levels = len(
            std_dev_levels) if do_std_dev_cones else len(prob_levels)
        for i in range(num_levels):
            uppers.append([0., ])
            lowers.append([0., ])

        raw_cumulative_var = 0
        mean_val = 0.  # NOTE: for now we assume means are zero, this could change

        initial_value = spot
        dt = 1 / 252.
        daily_var = dt * vol * vol

        while date <= end_date:
            means.append(mean_val)
            raw_cumulative_var += daily_var

            if do_std_dev_cones:
                std_dev = np.sqrt(raw_cumulative_var)
                for i in range(len(std_dev_levels)):
                    bound = std_dev_levels[i] * std_dev
                    uppers[i].append(mean_val + bound)
                    lowers[i].append(mean_val - bound)

            else:
                raise NotImplementedError("TODO")

            date = calendar.adjust(date + 1)  # Go to the next date
            # This is the risk associated with the next date
            dates.append(date)

        upper_max_exposures, lower_max_exposures = [], []
        upper_max_exposure_percs, lower_max_exposure_percs = [], []
        for i in range(num_levels):
            upper = uppers[i][-1]
            upper_max_exposures.append(upper)
            upper_max_exposure_percs.append(
                100 * np.abs(upper / max(1.0, abs(initial_value))))

            lower = lowers[i][-1]
            lower_max_exposures.append(lower)
            lower_max_exposure_percs.append(-100 *
                                            np.abs(lower / max(1.0, abs(initial_value))))

        out = {"dates": dates,
               "means": means,
               "uppers": uppers,
               "lowers": lowers,
               "upper_maxs": upper_max_exposures,
               "upper_max_percents": upper_max_exposure_percs,
               "lower_maxs": lower_max_exposures,
               "lower_max_percents": lower_max_exposure_percs,
               "initial_value": initial_value,
               "previous_value": initial_value,
               "update_value": initial_value
               }
        if do_std_dev_cones:
            probs = [1 - 2 * norm.cdf(-std_dev) for std_dev in std_dev_levels]
            out["std_probs"] = probs

        return out


class CashFlowRiskService(object):
    """
    Service responsible for retrieving hedge positions for an account, based on their hedge settings
    Not responsible for recording, updating hedge positions, etc. This just tells you what it thinks the positions
    should be.
    """

    def __init__(self,
                 cashflow_pricer: CashFlowPricerService = CashFlowPricerService(),
                 universe_provider_service: UniverseProviderService = UniverseProviderService()):
        self._cashflow_pricer = cashflow_pricer
        self._universe_provider_service = universe_provider_service
        self._fx_spot_provider = universe_provider_service.fx_spot_provider
        self._fx_option_strategy_provider = universe_provider_service.fx_option_strategy_provider

    def get_simulated_risk_for_account(self,
                                       date: Date,
                                       account: AccountTypes,
                                       max_horizon: Optional[int] = None):
        """ Get the (unhedged) cashflow risk for a specific account """
        account_ = Account.get_account(account=account)
        if account_ is None:
            raise ValueError(
                f"The supplied account_id ({account}) doesnt exist")

        # ====================
        # Get Cashflow Info
        # ====================
        cashflows, fx_pairs, domestic = self._cashflow_pricer.get_flows_for_account(account=account_, date=date,
                                                                                    max_horizon=max_horizon)

        # ====================
        # Run Simulation
        # ====================

        # Construct the Financial Universe
        universe = self._universe_provider_service.make_cntr_currency_universe(ref_date=date,
                                                                               domestic=domestic,
                                                                               fx_pairs=tuple(fx_pairs))

        # Construct the Cash Flow Risk Engine (Monte Carlo)
        engine = CashFlowRiskEngine_MC(universe=universe, n_trials=1000)

        # Compute the Risk metrics and PnL values
        metrics, pnl = engine.calc_risk_metrics(
            cashflows, domestic_currency=domestic)

        return metrics, pnl

    def get_fxpair_realized_volatility(self,
                                       last_date: Date,
                                       fxpair: FxPairTypes,
                                       averaging_window: int = 90):
        """
        Get the estimated annualized volatility for an FxPair over some period of time (calendar days).
        """

        rates = self._fx_spot_provider.get_spot_rates(start_date=last_date - averaging_window,
                                                      end_date=last_date, pair=fxpair)

        dc = DayCounter_HD()
        var, num, last_spot = 0.0, 0, None
        for rate in rates:
            if last_spot:
                # The time between days may not be constant.
                dt = dc.year_fraction(last_date, rate.data_time)
                log_return = np.log(rate.rate / last_spot) ** 2 / dt
                var += log_return
                num += 1
            last_spot, last_date = rate.rate, rate.data_time
        return np.sqrt(var / num)

    def get_account_risk_cones(self,
                               account: AccountTypes,
                               start_date: Date,
                               end_date: Date,
                               risk_reductions: Optional[Sequence[float]] = (
                                   0.0,),
                               std_dev_levels: Optional[Sequence[float]] = (
                                   1, 2, 3),
                               do_std_dev_cones: bool = False,
                               max_horizon: int = np.inf,
                               lower_risk_bound_percent=-np.inf,
                               upper_risk_bound_percent=np.inf) -> Dict[str, list]:
        """
        Get the risk cone for a specific account.
        """

        account_ = Account.get_account(account=account)
        if account_ is None:
            raise ValueError(
                f"The supplied account_id ({account}) doesnt exist")

        # ====================
        # Get Cashflow Info
        # ====================
        cashflows, _, domestic = self._cashflow_pricer.get_flows_for_account(account=account_, date=start_date,
                                                                             max_horizon=max_horizon)

        # Reformat cashflows to be a Dict[Currency, Sequence[Cashflow]]
        cashflow_map = {}
        for flow in cashflows:
            cashflow_map.setdefault(flow.currency, []).append(flow)

        return CashFlowRiskService().get_cashflow_risk_cones(domestic=domestic,
                                                             cashflows=cashflow_map,
                                                             start_date=start_date,
                                                             end_date=end_date,
                                                             risk_reductions=risk_reductions,
                                                             std_dev_levels=std_dev_levels,
                                                             do_std_dev_cones=do_std_dev_cones,
                                                             max_horizon=max_horizon,
                                                             lower_risk_bound_percent=lower_risk_bound_percent,
                                                             upper_risk_bound_percent=upper_risk_bound_percent)

    def get_cashflow_risk_cones(self,
                                domestic: CurrencyTypes,
                                cashflows: Dict[Currency, Sequence[CashFlow]],
                                start_date: Date,
                                end_date: Date,
                                risk_reductions: Optional[Sequence[float]] = (
                                    0.0,),
                                std_dev_levels: Optional[Sequence[float]] = (
                                    1, 2, 3),
                                do_std_dev_cones: bool = False,
                                max_horizon: int = np.inf,
                                lower_risk_bound_percent=-np.inf,
                                upper_risk_bound_percent=np.inf,
                                account: Optional[AccountTypes] = None) -> Dict[str, list]:
        """
        Method to get "cashflow risk cones" for showing cashflow risk, with and without hedging. Supports computing
        multiple risk reduction levels (from 0. to 1.0) simultaneously.
        Also supports computing the cones of an unhedged position at multiple std deviation levels

        :param domestic: Currency identifier, the domestic currency
        :param cashflows: Dictionary mapping currencies to the cashflows in those currencies, assumed to be in
            ascending order of payment date for each currency
        :param start_date: Date, the reference date of the calculation
        :param end_date: Date, the last date in the risk window, ie the further date in future along the risk cone
        :param risk_reductions: Sequence[float], the risk reduction levels at which to compute the cones
            If none are supplied, the raw (unhedged) risk is computed only.
            NOTE: the reductions are interpreted as VOLATILITY reduction percentages, not variance reduction
            Note: this only applies if do_std_dev_cones = False
        :param std_dev_levels: Sequence[float], the risk std deviation levels at which to compute the cones
            If none are supplied, a default of (1, 2, 3) is used
            Note: this only applies if do_std_dev_cones = True
        :param do_std_dev_cones: bool, if true then do the risk cones based on std deviation levels of raw, unhedged
            risk. If false, the do risk cones based on risk reduction levels for a hedged position
        :param max_horizon: int (optional), ability to ignore all cashflows that are more than this many days into the
                future. By default, none are ignored
        :param lower_risk_bound_percent: float, number < 0, representing max percentage of initial value lost
            in any of the risk cones. This acts as a floor level on losses. e.g. 5.0 = 5% of initial value can be lost
            Note: this only applies if do_std_dev_cones = False
        :param upper_risk_bound_percent: float, number < 0, representing max percentage of initial value gained
            in any of the risk cones. This acts as a cap level on PnL gains. e.g. 5.0 = 5% of initial value can be gained
            Note: this only applies if do_std_dev_cones = False
        :return: Dictionary, with these key value pairs:
                {
                "dates": [Date, Date, ..., Date],   (x-axis of the cones)
                "means": [0.0, 0.0, ..., 0.0],    (expected PnL as of each date)
                "uppers": [[float, float, float], [float, float, float]],   (upper PnL cones as of each date)
                "lowers": [[float, float, float], [float, float, float]],   (lower PnL cones as of each date)
                "upper_maxs": [float, float, float],          (upper max gains, one per cone)
                "upper_max_percents": [float, float, float],  (upper max gains in percent of init value, one per cone)
                "lower_maxs": [float, float, float],          (upper max losses, one per cone)
                "lower_max_percents": [float, float, float],  (upper max losses in percent of init value, one per cone)
                "initial_value": float    (initial value of the cash exposures in units of domestic)
                "previous_value": float   (total of existing amount of cashflows converted in units of domestic)
                "update_value": float     (previous_value plus new amount of cashflows converted in units of domestic)
                }
                Note that for uppers and lowers, each will have as many lists as there are risk_reductions
        """

        self._validate_inputs(domestic, cashflows, risk_reductions, std_dev_levels,
                              max_horizon, lower_risk_bound_percent, upper_risk_bound_percent)

        account_ = None
        domestic = Currency.get_currency(domestic)
        if account is not None and account > 0:
            account_ = Account.get_account(account=account)
            if account_ is None:
                raise ValueError(
                    f"The supplied account_id ({account}) doesnt exist")
        # Round the start date down. If date was None, most date from most recent EOD data cut.
        if start_date is None:
            start_date = DataCutService.get_eod_cut().cut_time

        if end_date.start_of_next_day() <= start_date:
            raise ValueError(
                "End date must be the same or after start_date")

        new_cashflows = cashflows
        existing_cashflows = {}
        merged_cashflows = defaultdict(list)

        if account_ is not None:
            filters = {
                "account": account_,
                "date__gte": Date.now().date(),
                "status__in": [CashFlow.CashflowStatus.ACTIVE, CashFlow.CashflowStatus.PENDING_ACTIVATION]
            }
            cfs = CashFlow.objects.filter(**filters).order_by('date')

            for cashflow in cfs:
                existing_cashflows.setdefault(
                    cashflow.currency, []).append(cashflow)

        for _cfs in (new_cashflows, existing_cashflows):
            for currency, _cashflows in _cfs.items():
                merged_cashflows[currency].extend(_cashflows)

        cashflows_hdl: Dict[Currency, CashFlows] = {}
        existing_cashflows_hdl: Dict[Currency, CashFlows] = {}
        new_cashflows_hdl: Dict[Currency, CashFlows] = {}

        max_date_in_future = end_date + \
            max_horizon if not np.isinf(max_horizon) else None

        for currency, cfs in merged_cashflows.items():
            cashflows_hdl[currency] = CashFlows(
                [cf for cf in iter_active_cashflows(
                    cfs, start_date, max_date_in_future=max_date_in_future)]
            )
        for currency, cfs in existing_cashflows.items():
            existing_cashflows_hdl[currency] = CashFlows(
                [cf for cf in iter_active_cashflows(
                    cfs, start_date, max_date_in_future=max_date_in_future)]
            )
        for currency, cfs in new_cashflows.items():
            new_cashflows_hdl[currency] = CashFlows(
                [cf for cf in iter_active_cashflows(
                    cfs, start_date, max_date_in_future=max_date_in_future)]
            )

        existing_foreign_ids = [
            currency.id for currency in existing_cashflows.keys()]
        new_foreign_ids = [currency.id for currency in new_cashflows.keys()]
        foreign_ids = [currency.id for currency in merged_cashflows.keys()]

        new_fx_pairs_ = FxPair.get_foreign_to_domestic_pairs(
            foreign_ids=new_foreign_ids,
            domestic=domestic
        )
        if len(new_fx_pairs_) == 0:
            raise RuntimeError(
                "Couldn't find any foreign currencies in these new cashflows")

        existing_fx_pairs_ = FxPair.objects.none()
        if len(existing_foreign_ids) > 0:
            existing_fx_pairs_ = FxPair.get_foreign_to_domestic_pairs(
                foreign_ids=existing_foreign_ids,
                domestic=domestic
            )
            if len(existing_fx_pairs_) == 0:
                raise RuntimeError(
                    "Couldn't find any foreign currencies in these cashflows")
        fx_pairs_ = FxPair.get_foreign_to_domestic_pairs(
            foreign_ids=foreign_ids,
            domestic=domestic
        )
        if len(fx_pairs_) == 0:
            raise RuntimeError(
                "Couldn't find any foreign currencies in these cashflows")

        # TODO: put this sorting inside of the function (with flag to sort based on requested inputs)
        # Sort the Fx pairs in same order as requested to ensure all data values line up (spots vs exposures)
        fx_pairs: List[FxPair] = []
        for foreign_id in foreign_ids:
            for pair in fx_pairs_:
                if pair.get_base_currency().id == foreign_id:
                    fx_pairs.append(pair)

        usd = Currency.get_currency('USD')
        if domestic != usd:
            foreign_ids_with_domestic = list(set(foreign_ids + [domestic.id]))
            fx_pairs_usd_ = FxPair.get_foreign_to_domestic_pairs(
                foreign_ids=foreign_ids_with_domestic,
                domestic=usd
            )
            fx_pairs_usd: List[FxPair] = []

            for foreign_id in foreign_ids_with_domestic:
                for pair in fx_pairs_usd_:
                    if pair.get_base_currency().id == foreign_id:
                        fx_pairs_usd.append(pair)
        else:
            fx_pairs_usd = fx_pairs

        dummy_company = BasicCompany(name="Dummy", domestic=domestic)
        dummy_account = BasicAccount(name="Dummy", company=dummy_company)

        settings = HedgeAccountSettings(account=dummy_account, method=HedgeMethod.MIN_VAR,
                                        max_horizon=max_horizon, margin_budget=np.inf)

        existing_cash_exposures = CashExposures_Cached(date=start_date, cashflows=existing_cashflows_hdl,
                                                       settings=settings)
        new_cash_exposures = CashExposures_Cached(
            date=start_date, cashflows=new_cashflows_hdl, settings=settings)
        cash_exposures = CashExposures_Cached(
            date=start_date, cashflows=cashflows_hdl, settings=settings)

        # Construct the Financial Universe
        universe_usd = self._universe_provider_service.make_cntr_currency_universe(
            ref_date=start_date,
            domestic=usd,
            fx_pairs=tuple(fx_pairs_usd),
            flat_forward=True,
            flat_discount=True)

        if domestic != usd:
            switcher = FxUniverseCounterSwitcher()
            new_pairs_map = {pair.get_base_currency().get_mnemonic(): pair for pair in fx_pairs
                             if pair.get_base_currency() != domestic}
            universe = switcher.switch_counter(
                universe=universe_usd, new_domestic=domestic, new_pairs=new_pairs_map)
        else:
            universe = universe_usd

        new_spots = universe.fx_universe.fx_assets.get_fx_spots(
            pairs=new_fx_pairs_)
        existing_spots = universe.fx_universe.fx_assets.get_fx_spots(
            pairs=existing_fx_pairs_)
        spots = universe.fx_universe.fx_assets.get_fx_spots(pairs=fx_pairs)

        vols = self._get_cone_vols(cashflows_hdl=cashflows_hdl, fx_pairs=fx_pairs, universe=universe,
                                   use_options_vol=domestic == usd)

        # Check is any vols are Nan
        if np.any(np.isnan(vols)):
            vols_with_nan = []
            for i in range(len(vols)):
                if np.isnan(vols[i]):
                    vols_with_nan.append(fx_pairs[i].name)
            vols_with_nan = ",".join(vols_with_nan)
            raise RuntimeError(
                f"Nan Vols were retrieved from universe, likely missing data for: {vols_with_nan}")

        corrs = universe.fx_universe.fx_corrs.instant_fx_spot_corr_matrix(
            pairs=fx_pairs)
        if np.any(np.isnan(corrs)):
            raise RuntimeError(
                "Nan Correlations were retrieved from universe, likely missing data")

        # Create risk calculator, keeps everything fixed to its known values today.
        risk_calc = PnLRiskCalculator(
            forwards=spots.values, vols=vols.values, correlations=corrs.values)

        calendar = CustomCalendar.new_western_no_holidays()

        date = start_date
        dates = [start_date]
        means = [0.]

        uppers = []
        lowers = []

        num_levels = len(std_dev_levels) if do_std_dev_cones else len(
            risk_reductions)
        for i in range(num_levels):
            uppers.append([0., ])
            lowers.append([0., ])

        num_std_devs_for_risk_reduction = 3
        raw_cumulative_var = 0
        mean_val = 0.  # NOTE: for now we assume means are zero, this could change

        initial_value, previous_value, update_value = None, None, None

        lower_risk_bound, upper_risk_bound = -np.inf, np.inf

        while date <= end_date:
            means.append(mean_val)
            exposures = cash_exposures.net_exposures()
            existing_exposures = existing_cash_exposures.net_exposures()
            new_exposures = new_cash_exposures.net_exposures()

            if initial_value is None:
                # Need to convert initial value to domestic.
                initial_value = 0
                for key, values in spots.items():
                    initial_value += values * abs(exposures[key])

                # Note: these are PnL bounds, so they are centered around zero
                # NOTE: the lower_risk_bound is a negative number
                lower_risk_bound = abs(initial_value) * \
                    (lower_risk_bound_percent / 100.)
                upper_risk_bound = abs(initial_value) * \
                    (upper_risk_bound_percent / 100.)
            if previous_value is None:
                previous_value = 0
                for key, values in existing_spots.items():
                    previous_value += values * abs(existing_exposures[key])
            if update_value is None:
                update_value = previous_value
                for key, values in new_spots.items():
                    update_value += values * abs(new_exposures[key])

            raw_cumulative_var += risk_calc.variance(exposures.values)
            if np.isnan(raw_cumulative_var):
                if np.any(np.isnan(exposures)):
                    raise RuntimeError(
                        "Nan detected in cash exposures, unexpected error")
                raise RuntimeError(
                    "Variance is nan, unexpected error as vols and corrs were validated")

            if do_std_dev_cones:
                std_dev = np.sqrt(raw_cumulative_var)
                for i in range(len(std_dev_levels)):
                    bound = std_dev_levels[i] * std_dev
                    uppers[i].append(mean_val + bound)
                    lowers[i].append(mean_val - bound)

            else:
                for i in range(len(risk_reductions)):
                    bound = num_std_devs_for_risk_reduction * (1 - risk_reductions[i]) * np.sqrt(
                        raw_cumulative_var)
                    uppers[i].append(min(upper_risk_bound, mean_val + bound))
                    lowers[i].append(max(lower_risk_bound, mean_val - bound))

            date = calendar.adjust(date + 1)  # Go to the next date
            # This is the risk associated with the next date
            dates.append(date)
            if date <= end_date:
                cash_exposures.refresh(date=date)

        upper_max_exposures, lower_max_exposures = [], []
        upper_max_exposure_percs, lower_max_exposure_percs = [], []
        for i in range(num_levels):
            upper = uppers[i][-1]
            upper_max_exposures.append(upper)
            upper_max_exposure_percs.append(
                100 * np.abs(upper / max(1e-10, abs(initial_value))))

            lower = lowers[i][-1]
            lower_max_exposures.append(lower)
            lower_max_exposure_percs.append(
                -100 * np.abs(lower / max(1e-10, abs(initial_value))))

        out = {"dates": dates,
               "means": means,
               "uppers": uppers,
               "lowers": lowers,
               "upper_maxs": upper_max_exposures,
               "upper_max_percents": upper_max_exposure_percs,
               "lower_maxs": lower_max_exposures,
               "lower_max_percents": lower_max_exposure_percs,
               "initial_value": initial_value,
               "previous_value": previous_value,
               "update_value": update_value}

        if do_std_dev_cones:
            probs = [1 - 2 * norm.cdf(-std_dev) for std_dev in std_dev_levels]
            out["std_probs"] = probs

        return out

    def _validate_inputs(self, domestic, cashflows, risk_reductions, std_dev_levels,
                         max_horizon, lower_risk_bound_percent, upper_risk_bound_percent):
        # =========================
        # Begin Validations
        # =========================
        if lower_risk_bound_percent >= 0:
            raise ValueError("Lower risk bound must be less than zero")
        if upper_risk_bound_percent <= 0:
            raise ValueError("Upper risk bound must be greater than zero")
        if lower_risk_bound_percent is None:
            lower_risk_bound_percent = -np.inf
        if upper_risk_bound_percent is None:
            upper_risk_bound_percent = np.inf

        if max_horizon <= 0:
            raise ValueError(
                "Max horizon (days) must be > 0")
        if len(cashflows) == 0:
            raise ValueError(
                "You supplied no cashflows")

        if not risk_reductions or len(risk_reductions) == 0:
            risk_reductions = (0.,)  # No reduction

        for i in range(len(risk_reductions)):
            if risk_reductions[i] > 1. or risk_reductions[i] < 0:
                raise ValueError(
                    "Risk reduction levels must be within [0, 1]")

        if not std_dev_levels or len(std_dev_levels) == 0:
            std_dev_levels = (1, 2, 3)

        for i in range(len(std_dev_levels)):
            if std_dev_levels[i] <= 0:
                raise ValueError(
                    "Std dev levels must be greater than zero")

        if domestic is None:
            raise ValueError(
                "You must supply a domestic currency")

        # =========================
        # End Validations
        # =========================

    def _get_cone_vols(self,
                       cashflows_hdl: Dict[Currency, CashFlows],
                       fx_pairs: List[FxPair],
                       universe: Universe,
                       use_options_vol: bool = False) -> pd.Series:
        vols = universe.fx_universe.fx_vols.vols_spots(pairs=fx_pairs)
        if not use_options_vol:
            return vols

        try:
            # Retrieve the atm vols for all Fx pairs, will allow us to build atm vol term structure
            df = self._fx_option_strategy_provider.get_atm_vols_for_pairs_on_date(date=universe.ref_date,
                                                                                  fx_pairs=fx_pairs,
                                                                                  latest_available=True)
        except Exception as e:
            logger.error(f"Error retrieving ATM vol dataframe: {e},"
                         " falling back on historical vol")
            return vols

        if df.empty:
            logger.error('Empty data frame retreived trying to get atm strategy vols for risk cones,'
                         ' falling back on historical vol (likely a date / data cut misalignment)')
            return vols

        # Find all pairs that actually support options strategy data
        unique_pair_ids = set(df['pair'].unique())

        for pair in fx_pairs:
            # Only a subset of fx pairs support option strategy data, so only use option vol approach for those pairs
            if pair.id not in unique_pair_ids:
                continue

            try:
                # Construct the atm vol term structure for the pair
                df_pair = df[df['pair'] == pair.id]
                ts = InterpolatedAtmVolTermStructure.from_linear(dtms=df_pair['dtm'].values,
                                                                 vols=df_pair['mid_value'].values,
                                                                 ref_date=universe.ref_date,
                                                                 dc=universe.day_counter)
                """
                Compute the volatility estimate to use, based on cashflow weighted average of total variance:

                sigma^2 = sum_i[ sigma_atm(T_i)^2 * T_i * |C_i| ]  /  sum[ T_i * |C_i| ]

                where:
                    T_i = time to maturity of ith cashflow
                    C_i = amount of ith cashflow
                    sigma_atm(T_i) = atm volatility evaluated at the ith cashflow time
                """
                base = pair.get_base_currency()
                cashflows = cashflows_hdl.get(base, None)
                if not cashflows:
                    continue

                numer = 0
                denom = 0
                for cashflow in cashflows:
                    if cashflow.pay_date <= universe.ref_date:
                        continue
                    ttm = ts.day_counter.year_fraction(
                        start=universe.ref_date, end=cashflow.pay_date)
                    vol = ts.at_T(ttm)
                    ttm_c = ttm * abs(cashflow.amount)
                    # total variance for this cashflow, multiplied by cashflow size
                    numer += vol ** 2 * ttm_c
                    denom += ttm_c

                if denom != 0:
                    old_vol = vols[pair]
                    new_vol = np.sqrt(numer / denom)
                    # Ensure that the new volatility estimate (from options) is within 25% of the EWMA vol estimate
                    new_vol = max(0.75 * old_vol, min(1.25 * old_vol, new_vol))
                    vols[pair] = new_vol

            except Exception as e:
                logger.warning(f"Error constructing ATM vol term structure for pair: {e},"
                               " falling back on historical vol")

        return vols
