from datetime import datetime
from typing import List
from main.apps.account.models.company import Company
from main.apps.oems.models.cny import CnyExecution
from main.apps.oems.services.currency_execution import CompanyCnyExecutionProvider
from main.apps.oems.services.liquidity import CurrencyInsightService


class MarketLiquidity:
    company:Company
    cny_execs:List[CnyExecution]
    N_DATA:int = 2

    def __init__(self, company:Company) -> None:
        self.company = company

        self.cny_execs = CnyExecution.objects.filter(company=self.company,
                                                     active=True).distinct('fxpair')


    def populate_market_liquidity(self) -> List[dict]:
        start_time = datetime.now()
        end_time = start_time

        market_liquidity = []
        for cny_exec in self.cny_execs:
            currency_insight_svc = CurrencyInsightService(sell_currency=cny_exec.fxpair.base_currency,
                                             buy_currency=cny_exec.fxpair.quote_currency,
                                             start_date=start_time,
                                             end_date=end_time)

            liquidity:dict = currency_insight_svc.get_liquidity_insight()

            liquidity.pop('recommended_execution', None)

            cny_exec_svc = CompanyCnyExecutionProvider(company=self.company)
            is_ndf, fwd_rfq_type = cny_exec_svc.is_ndf(cny_exec=cny_exec)

            liquidity['is_ndf'] = is_ndf
            liquidity['fwd_rfq_type'] = fwd_rfq_type

            market_liquidity.append(liquidity)

        return market_liquidity
