import logging
from typing import Union, Sequence, Tuple, Optional, Dict, Iterable, List

import numpy as np
from auditlog.models import LogEntry

from main.apps.account.models import get_hdl_cashflows, CashFlow, iter_active_cashflows
from main.apps.account.services.cashflow_provider import CashFlowProviderService
from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.services.data_cut_service import DataCutService
from main.apps.marketdata.services.universe_provider import UniverseProvider, UniverseProviderService
from main.apps.currency.models.currency import Currency
from main.apps.account.models.account import Account

from hdlib.Universe.Universe import Universe
from hdlib.Instrument.CashFlow import CashFlows
from hdlib.DateTime.Date import Date
from hdlib.Universe.Pricing.CashFlowPricer import CashFlowPricer, CashflowValueSummary

logger = logging.getLogger(__name__)


class CashFlowChange:
    """ Structure that helps reconstruct cashflows """

    def __init__(self):
        self.cashflow = None
        self.changes_per_field = {}
        self.was_created = False


class CashFlowPricerService(object):
    """
    Service responsible for retrieving hedge positions for an account, based on their hedge settings
    Not responsible for recording, updating hedge positions, etc. This just tells you what it thinks the positions
    should be.
    """

    def __init__(self,
                 cashflow_provider: CashFlowProviderService = CashFlowProviderService(),
                 universe_provider_service: UniverseProviderService = UniverseProviderService()):
        self._cashflow_provider = cashflow_provider
        self._universe_provider_service = universe_provider_service
        self._fx_spot_provider = universe_provider_service.fx_spot_provider

    def get_changed_cashflows_as_of(self,
                                    time: Date,
                                    account: Account,
                                    max_days_away: int = 730,
                                    max_date_in_future: Optional[Date] = None,
                                    include_cashflows_on_vd: bool = False,
                                    include_end: bool = False
                                    ) -> Tuple[Optional[List[CashFlow]], Optional[List[CashFlow]]]:
        """
        Function that gets cashflows that were changed between some time and now, and returns the list of original
        and final HDL cashflows for the DB cashflows that changed.

        This allows us to compute the difference in value of the two sets of cashflows at the same time, determining
        what changes in account values are due to changes to the cashflows themselves (as opposed to the normal types
        of changes, like changes in the market).
        """

        entries = LogEntry.objects.get_for_model(CashFlow).filter(timestamp__gte=time, timestamp__lte=time)
        if not entries:
            return None, None

        changes_by_cashflow = {}
        for entry in sorted(entries, key=lambda x: x.timestamp):
            changes_by_cashflow.setdefault(entry.object_pk, []).append(entry)

        if len(changes_by_cashflow) == 0:
            return None, None

        cashflow_change_summaries = {}
        for pk, changes in changes_by_cashflow.items():
            try:
                cashflow = CashFlow.objects.get(pk=int(pk))
            except Exception:
                # Object must have been deleted.
                # logger.error(f"Could not find cashflow with pk = {pk}, it may have been deleted.")
                continue

            if cashflow.account != account:
                continue

            # Create an object to track all the changes.
            change = CashFlowChange()

            for entry in changes:
                change.cashflow = cashflow

                changes_object = eval(entry.changes)

                for field, (before, after) in changes_object.items():
                    change_list = change.changes_per_field.setdefault(field, [])
                    if len(change_list) == 0:
                        change_list.append((before, None))
                    # Make sure the after from the last change matches the before for this change.
                    if change_list[-1][0] != before:
                        raise ValueError(f"last 'after' ({change_list[-1][0]}) does not match this 'before' {before}")
                    change_list.append((after, entry.timestamp))

            cashflow_change_summaries[pk] = change

        original_cashflows, final_cashflows = [], []
        for _, changes in cashflow_change_summaries.items():
            # Get all data from the current cashflow.
            data_dict = {"name": changes.cashflow.name,
                         "amount": changes.cashflow.amount,
                         "currency": changes.cashflow.currency,
                         "calendar": changes.cashflow.calendar,
                         "roll_convention": changes.cashflow.roll_convention,
                         "date": changes.cashflow.date,
                         "end_date": changes.cashflow.end_date,
                         "is_recurring": changes.cashflow.is_recurring,
                         "periodicity": changes.cashflow.periodicity}

            # Changed cashflows as they are now.
            final_cashflows += list(iter_active_cashflows(get_hdl_cashflows(**data_dict),
                                                          max_days_away=max_days_away, ref_date=time,
                                                          max_date_in_future=max_date_in_future,
                                                          include_cashflows_on_vd=include_cashflows_on_vd,
                                                          include_end=include_end))

            if changes.was_created:
                # The cashflow did not exist at all on the original date.
                continue

            argument_names = data_dict.keys()
            for field_name, change_list in changes.changes_per_field.items():
                if field_name not in argument_names:
                    continue
                data_dict[field_name] = change_list[0]

            # Changed cashflows, as they originally were.
            try:
                original_cashflows += list(iter_active_cashflows(get_hdl_cashflows(**data_dict),
                                                                 max_days_away=max_days_away, ref_date=time,
                                                                 max_date_in_future=max_date_in_future,
                                                                 include_cashflows_on_vd=include_cashflows_on_vd,
                                                                 include_end=include_end))
            except Exception as ex:
                logger.error(f"Could not get original cashflows: {ex}")

        return original_cashflows, final_cashflows

    def calculate_cashflow_adjustment(self,
                                      current_universe: Universe,
                                      start_date: Date,
                                      account: Account,
                                      max_days_away: int = 730,
                                      max_date_in_future: Optional[Date] = None,
                                      include_cashflows_on_vd: bool = False,
                                      include_end: bool = False) -> Tuple[Optional[float], Optional[float]]:
        try:
            original, final = self.get_changed_cashflows_as_of(time=start_date,
                                                               account=account,
                                                               max_days_away=max_days_away,
                                                               max_date_in_future=max_date_in_future,
                                                               include_cashflows_on_vd=include_cashflows_on_vd,
                                                               include_end=include_end)
        except Exception as ex:
            logger.error(f"Could not get changed cashflows: {ex}")
            return None, None

        if original is None:
            return None, None

        original = CashFlows(cashflows=original)
        original_npv, _ = self.get_npv_for_cashflows(cashflows=original, universe=current_universe,
                                                     domestic=account.company.currency)

        final = CashFlows(cashflows=final)
        final_npv, _ = self.get_npv_for_cashflows(cashflows=final, universe=current_universe,
                                                  domestic=account.company.currency)

        return original_npv, final_npv

    def get_historical_cashflows_value_for_account(self,
                                                   start_date: Date,
                                                   end_date: Date,
                                                   account: Account,
                                                   inclusive: bool = True,
                                                   include_end: bool = False) -> Tuple[float, int]:
        """
        Get the value of cashflows, fx converted at the time they were received
        :param start_date: Date, start date of the region of interest.
        :param end_date: Date, end date of the region of interest,
        :param account: AccountTypes, the account whose cashflows are desired.
        :param inclusive: bool, if false, cashflows exactly at the start time (note Date is a date *time*) are
            not included.
        :return (float, int) -> (value of historical cashflows, number of cashflows)
        """
        max_date = self._fx_spot_provider.get_max_date()
        if end_date > max_date:
            # TODO: Temporary fix to get past error when running EOD, this needs to be looked at later
            logging.warning(
                f"Cannot get historical values for cashflows in the future, using max date ({max_date}, "
                f"which comes from the fx spot provider) instead of end_date ({end_date}).")
            end_date = max_date

        cashflows, fx_pairs, domestic = self.get_flows_for_account(account=account,
                                                                   date=start_date,
                                                                   max_date=end_date,
                                                                   inclusive=inclusive,
                                                                   include_end=include_end)

        if cashflows.empty:
            return 0.0, 0

        pair_map: Dict[Currency, FxPair] = {}
        for pair in fx_pairs:
            pair_map[pair.base_currency] = pair

        value = 0.
        for flow in cashflows:
            spot = self._fx_spot_provider.get_spot_value(fx_pair=pair_map[flow.currency], date=flow.pay_date)
            if np.isnan(spot):
                logger.warning(f"Could not find a most recent spot value for {pair_map[flow.currency]} "
                               f"on or before {flow.pay_date}. Not counting towards roll cost.")
            value += flow.amount * spot

        return value, len(cashflows)

    def get_npv_for_account(self,
                            date: Date,
                            account: Account,
                            max_horizon: Optional[int] = None,
                            max_date: Optional[Date] = None,
                            inclusive: bool = False,
                            universe: Optional[Universe] = None) -> Tuple[float, float]:
        """ Compute the net present value for cashflows in an account """
        cashflows, fx_pairs, domestic = self.get_flows_for_account(account=account, date=date,
                                                                   max_horizon=max_horizon,
                                                                   max_date=max_date,
                                                                   inclusive=inclusive)
        if cashflows.empty:
            return 0., 0.

        # Construct the Financial Universe
        if not universe:
            universe = self._universe_provider_service.make_cntr_currency_universe(ref_date=date,
                                                                                   domestic=domestic,
                                                                                   fx_pairs=tuple(fx_pairs),
                                                                                   create_corr=False,
                                                                                   create_vols=False)

        return self.get_npv_for_cashflows(cashflows=cashflows, universe=universe, domestic=domestic)

    def get_npv_for_cashflows_in_range(self,
                                       date: Date,
                                       account: Account,
                                       start_date: Date,
                                       end_date: Date,
                                       universe: Optional[Universe] = None,
                                       inclusive: bool = True,
                                       include_end: bool = False) -> Tuple[float, float, int]:
        logger.debug(f"Getting npv for cashflows in range {start_date} to {end_date} for account {account}, "
                     f"inclusive = {inclusive}, include_end = {include_end}")
        # Get the cashflows that are in the supplied date range.
        cashflows, fx_pairs, domestic = self.get_flows_for_account(account=account,
                                                                   date=start_date,
                                                                   max_date=end_date,
                                                                   inclusive=inclusive,
                                                                   include_end=include_end)
        # Save some time.
        if cashflows.empty or not fx_pairs:
            return 0.0, 0., 0

        # Construct the Financial Universe
        if not universe:
            universe = self._universe_provider_service.make_cntr_currency_universe(ref_date=date,
                                                                                   domestic=domestic,
                                                                                   fx_pairs=tuple(fx_pairs),
                                                                                   create_corr=False,
                                                                                   create_vols=False)
        value, abs_value = self.get_npv_for_cashflows(universe=universe, cashflows=cashflows, domestic=domestic)
        return value, abs_value, len(cashflows)

    def get_npv_for_cashflows(self,
                              universe: Universe,
                              cashflows: CashFlows,
                              domestic: Currency) -> Tuple[float, float]:
        pricer = CashFlowPricer(universe=universe)
        return pricer.price_cashflows(cashflows=cashflows, value_currency=domestic)

    def get_cashflow_value_summary_for_account(self,
                                               date: Date,
                                               account: Account,
                                               max_horizon: Optional[int] = None,
                                               max_date: Optional[Date] = None,
                                               inclusive: bool = False,
                                               universe: Optional[Universe] = None
                                               ) -> CashflowValueSummary:
        cashflows, fx_pairs, domestic = self.get_flows_for_account(account=account, date=date,
                                                                   max_horizon=max_horizon,
                                                                   max_date=max_date,
                                                                   inclusive=inclusive)
        if cashflows.empty:
            return CashflowValueSummary(domestic)

        # Construct the Universe
        if not universe:
            logger.debug(
                f"get_cashflow_value_summary_for_account: no universe was provided, creating universe for domestic {domestic}.")
            universe = self._universe_provider_service.make_cntr_currency_universe(ref_date=date,
                                                                                   domestic=domestic,
                                                                                   fx_pairs=tuple(fx_pairs),
                                                                                   create_vols=False,
                                                                                   create_corr=False)
        return self.get_cashflow_value_summary(cashflows=cashflows, universe=universe, domestic=domestic)

    def get_cashflow_value_summary(self,
                                   cashflows: CashFlows,
                                   universe: Universe,
                                   domestic: Currency) -> CashflowValueSummary:
        pricer = CashFlowPricer(universe=universe)
        return pricer.compute_cashflow_value_summary(cashflows=cashflows, value_currency=domestic)

    def get_flows_for_account(self,
                              account: Account,
                              date: Date,
                              max_horizon: Optional[int] = None,
                              max_date: Optional[Date] = None,
                              inclusive: bool = True,
                              include_end: bool = False) -> Tuple[CashFlows, Sequence[FxPair], Currency]:
        domestic = account.domestic_currency

        # TODO: need to hookup ignore domestic
        unique_currencies = set()
        # unique_currencies.add(domestic)

        flows = self._cashflow_provider.get_active_cashflows(start_date=date, account=account, inclusive=inclusive,
                                                             max_days_away=max_horizon, max_date_in_future=max_date,
                                                             include_end=include_end)

        cashflows = []
        for cf in flows:
            unique_currencies.add(cf.currency)
            cashflows.append(cf)
        logger.debug(f"get_flows_for_account: got {len(cashflows)} cashflows for account {account}, "
                     f"with {len(unique_currencies)} unique currencies.")

        fx_pairs = FxPair.get_foreign_to_domestic_pairs(foreign_ids=unique_currencies,
                                                        domestic=domestic)

        cashflows = CashFlows(cashflows)
        return cashflows, fx_pairs, domestic
