from main.apps.account.services.cashflow_pricer import CashFlowPricerService
from main.apps.hedge.models.hedgesettings import HedgeAccountSettings_DB
from main.apps.hedge.services.hedge_position import HedgePositionService
from main.apps.hedge.services.pnl import PnLProviderService

from hdlib.Universe.Universe import Universe
from hdlib.DateTime.Date import Date
from hdlib.Hedge.Fx.CashPnLAccount import CashPnLAccountHistoryProvider, CashPnLAccount

from typing import Optional, Tuple


class CashPnLAccountHistoryProvider_DB(CashPnLAccountHistoryProvider):
    def __init__(self,
                 settings: HedgeAccountSettings_DB,
                 cashflow_pricer: CashFlowPricerService = CashFlowPricerService(),
                 pnl_provider: PnLProviderService() = PnLProviderService(),
                 hedge_position_service: HedgePositionService = HedgePositionService()):
        self._settings = settings
        self._cashflow_pricer = cashflow_pricer
        self._pnl_provider = pnl_provider
        self._hedge_position_service = hedge_position_service

    def get_pnl_and_initial_exposure(self,
                                     start_date: Optional[Date],
                                     end_date: Date,
                                     universe: Optional[Universe] = None
                                     ) -> Tuple[Optional[float], Optional[float]]:
        """
        Get the PnL between a start and end date, together with the net cash exposure (NPV) as of the start date.
        :param start_date: Date (optional), the start date for PnL calc (inclusive)
        :param end_date: Date, the end date (e.g. current date) for the PnL
        :param universe: Universe (optional), the financial universe as of end_date
        :return: (float, float) = (PnL, NPV of Cash Exposure), if a hedge was in place as of start date. T
            If no hedge was in place as of the start_date, then None, None is returned
        """
        first_date = self.get_first_date()
        if not first_date:
            return None, None

        start_date = min(start_date, first_date) if start_date else first_date
        account = self._settings.account
        realized_pnl = self._pnl_provider.get_realized_pnl(account=account,
                                                           start_date=start_date, end_date=end_date,
                                                           spot_fx_cache=universe)

        unrealized_pnl = self._pnl_provider.get_unrealized_pnl(date=end_date, account=account, universe=universe)
        total_pnl = realized_pnl.total_pnl + unrealized_pnl.total_pnl

        initial_cash_exposure, _ = self._cashflow_pricer.get_npv_for_account(date=start_date,
                                                                             account=self._settings.account,
                                                                             max_horizon=self._settings.max_horizon,
                                                                             universe=universe)
        return total_pnl, initial_cash_exposure

    def get_account_state(self,
                          date: Date = None,
                          roll_down: bool = True,
                          universe: Optional[Universe] = None) -> CashPnLAccount:
        """ If Date is None, supply the first recorded state available """
        if not date:
            if not universe:
                date = universe.ref_date
            else:
                raise ValueError("You must supply either a universe or a date")

        hedge_cash = 0  # TODO: need to implement (currently includes financing cost of initial position...probs shouldnt)
        # TODO: add a lookback to the hedge settings (but make sure that cashflows aren't rolling off mid calc)
        start_date = date - 500
        cash_received, num_cashflows = self._cashflow_pricer.get_historical_cashflows_value_for_account(
            start_date=start_date,
            end_date=date,
            account=self._settings.account)

        # Todo: pull positions and pass into both
        future_cash_npv, _ = self._cashflow_pricer.get_npv_for_account(date=date, account=self._settings.account,
                                                                       max_horizon=self._settings.max_horizon,
                                                                       universe=universe)
        position_value, _ = self._pnl_provider.get_hedge_position_value(account=self._settings.account,
                                                                        date=date,
                                                                        fx_cache=universe)
        return CashPnLAccount(date=date, hedge_cash=hedge_cash, trade_costs=0, roll_costs=0,
                              cashflows_received=cash_received, future_cash_npv=future_cash_npv,
                              hedge_position_value=position_value)

    def get_first_date(self) -> Optional[Date]:
        """ Get first date of recorded history, if available, else None """
        first_event = self._hedge_position_service.get_first_positions_event(account=self._settings.account)
        return Date.from_datetime(first_event.time) if first_event else None
