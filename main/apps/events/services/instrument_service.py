import logging
from typing import Optional, Tuple

from hdlib.Universe.Universe import Universe

from hdlib.Core.FxPair import FxPair

from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache
from hdlib.DateTime.Date import Date
from main.apps.account.models import Company, Account, CashFlow, iter_active_cashflows
from main.apps.account.models.parachute_cashflow import ParachuteCashFlow
from main.apps.events.models import ForwardSettlement, CashflowRolloff
from main.apps.hedge.models.fxforwardposition import FxForwardPosition
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider

logger = logging.getLogger(__name__)


class InstrumentService:
    @staticmethod
    def close_delivered_forwards(company: Company,
                                 start_time: Optional[Date],
                                 end_time: Date,
                                 spot_fx_cache: SpotFxCache) -> Tuple[int, float]:
        """
        Close all delivered forwards (that have not already been closed) that closed within a (potentially half open)
        window of time.

        Note: This should eventually just be its own separate step in EOD, not dependent on any one company. We just
        have a step to close all delivered forwards.

        :param company: The company whose forwards are being closed.
        :param start_time: If this is specified, only close forwards in the range [start_time, end_time]. Otherwise,
            close all forwards that delivered before start time.
        :param end_time: The "current time," only close forwards that are unclosed, and delivered on or before this
            time.
        :param spot_fx_cache: A spot cache, used to mark the final spot rate for the forwards.

        :returns: Returns the number of closed forwards, and the realized PnL of the forward positions that were
            closed.
        """
        forwards = FxForwardPosition.get_delivered_forwards(company=company, start_time=start_time, end_time=end_time,
                                                            only_unclosed=True)
        total_pnl, count = 0.0, 0
        for fwd in forwards:
            try:
                unwind_fx_rate = spot_fx_cache.get_fx(fx_pair=fwd.fxpair)
            except Exception as ex:
                logger.warning(f"Exception while looking for spot rate for {fwd.fxpair}: {ex}")
                continue
            if unwind_fx_rate is None:
                logger.warning(f"Could not find Fx spot rate for {fwd.fxpair}")
                continue

            fwd.unwind_time = end_time
            fwd.unwind_price = unwind_fx_rate
            fwd.save()

            # Register the unwind event.
            ForwardSettlement.register_settlement(parent_forward=fwd,
                                                  settlement_time=end_time,
                                                  amount_unwound=fwd.amount,
                                                  amount_remaining=0.,
                                                  unwind_fx_rate=unwind_fx_rate)

            total_pnl += fwd.pnl
            count += 1
        return count, total_pnl

    @staticmethod
    def register_cashflow_rolloffs(company: Company,
                                   start_time: Date,
                                   end_time: Date,
                                   spot_fx_cache: SpotFxCache) -> int:
        """
        Mark any cashflows for a company in the interval as having rolled off, and return the number of cashflows that
        rolled off.
        """
        active_accounts = Account.get_active_accounts(company=company)
        count = 0
        for account in active_accounts:
            cfs = CashFlow.get_cashflow_object(start_date=start_time,
                                               account=account,
                                               exclude_unknown_on_ref_date=False,
                                               include_pending_margin=False)

            for cf_gen in cfs:
                cashflows = iter_active_cashflows(cfs=(cf_gen,), ref_date=start_time,
                                                  include_cashflows_on_vd=True,
                                                  include_end=True,
                                                  max_date_in_future=end_time)

                for cashflow in cashflows:
                    spot_rate = spot_fx_cache.convert_value(value=1,
                                                            from_currency=cashflow.currency_long,
                                                            to_currency=cashflow.currency_short)
                    CashflowRolloff.register_rolloff(parent_cashflow=cf_gen, amount=cashflow.amount,
                                                     rolloff_time=cashflow.pay_date, final_rate=spot_rate)
                    count += 1

        return count

    @staticmethod
    def get_cashflow_rolloffs(account: Account, start_time: Date, end_time: Date):
        return CashflowRolloff.objects.filter(rolloff_time__gte=start_time, rolloff_time__lt=end_time,
                                              parent_cashflow__account=account)

    @staticmethod
    def register_cashflow_rolloffs_eod(time: Date, spot_fx_cache: Optional[SpotFxCache] = None):
        """
        Note(Nate): This should be run as a separate step EOD before any hedging.
        """

        # Get all cashflows that have (time-wise) rolled off, but have not been handled yet.
        cashflows_to_close = list(
            ParachuteCashFlow.objects.filter(pay_date__lte=time, deactivated_by_rolloff__isnull=True))
        logger.debug(f"Found {len(cashflows_to_close)} (parachute) cashflows to close.")
        if len(cashflows_to_close) == 0:
            return

        if not spot_fx_cache:
            spot_fx_cache = FxSpotProvider().get_spot_cache(time=time)

        if not cashflows_to_close:
            return

        for cashflow in cashflows_to_close:
            domestic = cashflow.account.company.currency
            spot = spot_fx_cache.get_fx(FxPair(cashflow.currency, domestic))
            if not spot:
                logger.error(
                    f"Could not find the Fx spot for {cashflow.currency} at time {spot_fx_cache.time} to close the cashflow.")
            cashflow.close_by_rolloff(time=time, final_spot=spot)

    @staticmethod
    def generate_cashflows(time: Date, start_date: Date, end_date: Date, universe: Universe,
                           account: Optional[Account] = None):
        """
        Function to create ParachuteCashflows from CashFlow (generator) objects. This will change when we switch to
        having a true cashflows table.

        Note(Nate): This should be run as a separate step EOD before any hedging.
        """

        # TODO(Nate,Parachute): Figure out how to get this to run in some sort of "EOD" sense.
        # TODO(Nate,Parachute): Figure out what to do when "cashflows" (generators) are deleted.

        if account is None:
            # NOTE(Nate): For now, we will only generate cashflows for actual parachute accounts.
            #   In the future, we will need something like this to generate "true cashflow" from the generators, for
            #   all accounts, then we will go back to calling
            #       accounts = Account.get_active_accounts()
            #
            accounts = Account.get_account_objs(strategy_types=(Account.AccountStrategy.PARACHUTE,),
                                                exclude_hidden=True)
        else:
            accounts = [account]

        for account in accounts:
            # Generate all active cashflows from the cashflow generators.
            cashflows = CashFlow.get_active_cashflows(start_date=time, account=account, max_date_in_future=end_date)
            domestic = account.domestic_currency
            created_cashflows = []
            for cashflow in cashflows:
                if cashflow.pay_date < start_date:
                    continue
                initial_npv = universe.value_cashflow(cashflow, quote_currency=domestic)
                initial_spot = universe.get_spot(FxPair(base=cashflow.currency, quote=domestic))
                new_cashflow = ParachuteCashFlow.create_cashflow(account=account,
                                                                 pay_date=cashflow.pay_date,
                                                                 currency=cashflow.currency,
                                                                 amount=cashflow.amount,
                                                                 generation_time=time,
                                                                 initial_npv=initial_npv,
                                                                 initial_spot=initial_spot)
                created_cashflows.append(new_cashflow)

            return created_cashflows
