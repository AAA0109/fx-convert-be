from typing import Dict, Tuple, Optional

from hdlib.DateTime.Date import Date
from main.apps.account.models import Account
from main.apps.account.services.cashflow_provider import CashFlowProviderService
from main.apps.hedge.models import CompanyHedgeAction, FxPosition
from main.apps.hedge.services.pnl import PnLProviderService, PnLData
from main.apps.marketdata.services.fx.fx_provider import FxSpotProvider
from main.apps.util import ActionStatus

PrimaryKey = int


class HedgingAPIService:
    """
    API object that provides a static interface to get information about accounts' hedges and the hedges' performance.
    """

    def __init__(self, pnl_provider: PnLProviderService = PnLProviderService()):
        self._pnl_provider = pnl_provider

    def get_realized_pnl_for_account(self, account_id: PrimaryKey) -> Tuple[ActionStatus, Optional[float]]:
        """ Get the realized PnL of an account. """
        account = Account.get_account(account=account_id)
        if account is None:
            return ActionStatus.log_and_error(f"Could not find account pk={account_id}."), \
                   None

        raise NotImplementedError

    def get_unrealized_pnl_for_account(self,
                                       account_id: PrimaryKey,
                                       date: Optional[Date] = None) -> Tuple[ActionStatus, Optional[PnLData]]:
        """ Get the unrealized PnL of an account. """
        account = Account.get_account(account=account_id)
        if account is None:
            return ActionStatus.log_and_error(f"Could not find account pk={account_id}."), \
                   None

        if date is None:
            date = Date.now()
        return ActionStatus.log_and_success(f"Got realized PnL."), \
               self._pnl_provider.get_unrealized_pnl(date=date, account=account_id)

    def get_positions_for_account(self, account_id: PrimaryKey) -> Tuple[ActionStatus, Optional[Dict[str, float]]]:
        """ Get all the positions for an account. """
        account = Account.get_account(account=account_id)
        if account is None:
            return ActionStatus.log_and_error(f"Could not find account pk={account_id}."), \
                   None

        current_time = Date.now()
        fx_positions, event = FxPosition.get_position_objs(time=current_time, account=account)
        output = {}
        for position in fx_positions:
            output[position.fxpair.name] = position.amount
        return ActionStatus.log_and_success(f"Got {len(output)} positions for account."), output

    def get_cash_exposures(self, account_id: PrimaryKey):
        account = Account.get_account(account=account_id)
        if account is None:
            return ActionStatus.log_and_error(f"Could not find account pk={account_id}."), \
                   None

        current_time = Date.now()

        exposures = CashFlowProviderService().get_cash_exposures_for_account(time=current_time, account=account)
        exposures = exposures.net_exposures()
        spot_cache = FxSpotProvider().get_spot_cache(time=current_time)

        total = 0.
        for fx_pair, amount in exposures:
            spot_cache.get_fx(fx_pair=fx_pair)


        # Exposures always have domestic as the quote currency, which may not be the market convention. Change
        # to market convention.
        exposures = converter.convert_positions_to_market(fx_positions=exposures, fx_cache=spot_cache)

    def get_realized_variance_for_account(self, account_id: PrimaryKey) -> Tuple[ActionStatus, Optional[float]]:
        """ NOTE(Nate): Not sure about this one, but could be a good statistic. """
        account = Account.get_account(account=account_id)
        if account is None:
            return ActionStatus.log_and_error(f"Could not find account pk={account_id}."), \
                   None

        raise NotImplementedError
