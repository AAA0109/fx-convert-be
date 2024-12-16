import numpy as np

from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache

from hdlib.DateTime.Date import Date
from main.apps.account.models import Company
from main.apps.broker.models import BrokerAccount
from main.apps.hedge.models.company_fxposition import CompanyFxPosition


class CompanyPositionsSummary:
    def __init__(self, current_value: float, total_price: float):
        self.current_value = current_value
        self.total_price = total_price

    @property
    def unrealized_pnl(self):
        return self.current_value - self.total_price


class CompanyPositionsService(object):
    @staticmethod
    def get_company_positions_summary(time: Date,
                                      company: Company,
                                      positions_type: BrokerAccount.AccountType,
                                      spot_fx_cache: SpotFxCache):
        positions = CompanyFxPosition.get_positions_object(company=company, time=time, positions_type=positions_type)
        current_value, total_price = 0.0, 0.0
        for fx_pair, (amount, price) in positions.positions.items():
            total_price += price * np.sign(amount)
            current_value += amount * spot_fx_cache.get_fx(fx_pair=fx_pair)

        return CompanyPositionsSummary(current_value=current_value, total_price=total_price)
