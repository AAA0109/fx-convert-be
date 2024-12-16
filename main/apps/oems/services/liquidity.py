from datetime import datetime, timedelta
from typing import List, Optional, Sequence

from main.apps.currency.models.currency import Currency
from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.models import CorpayFxSpot
from main.apps.marketdata.services.spread import SpreadProvider
from main.apps.oems.api.dataclasses.best_execution import BestExecStatus
from main.apps.oems.api.dataclasses.liquidity_insight import LiquidityStatus, MarketStatus
from main.apps.oems.backend.exec_utils import get_best_execution_status


class CurrencyInsightService:
    fx_pair:FxPair
    sell_currency:str
    buy_currency:str
    start_date:datetime
    end_date:datetime
    spot_data: Sequence[CorpayFxSpot]
    spread_provider:SpreadProvider
    now:datetime

    def __init__(self, sell_currency:Currency,buy_currency:Currency,
                 start_date:Optional[datetime] = None,
                 end_date:Optional[datetime] = None) -> None:
        self.now = datetime.now()
        self.sell_currency = sell_currency
        self.buy_currency = buy_currency
        self.fx_pair = FxPair.get_pair_from_currency(
            base_currency=sell_currency,
            quote_currency=buy_currency
        )
        self._set_start_date(start_date=start_date)
        self._set_end_date(end_date=end_date)
        self._set_spot_data()
        self.spread_provider = SpreadProvider(fx_pair=self.fx_pair,
                                              ref_date=self.start_date)

    def _set_start_date(self, start_date:Optional[datetime]) -> None:
        start_date = start_date if start_date else datetime.now()
        self.start_date = start_date.replace(minute=0, second=0, microsecond=0)

    def _set_end_date(self, end_date:Optional[datetime]) -> None:
        self.end_date = end_date.replace(minute=0, second=0, microsecond=0) \
            if end_date else self.start_date + timedelta(days=1)

    def _set_spot_data(self) -> Sequence[CorpayFxSpot]:
        self.spot_data = CorpayFxSpot.objects.filter(
            date__gte=self.start_date,
            date__lte=self.end_date)

    def _find_recommendation_by_liquidity(self, data:List[dict], liquidity_status:str,
                                          min_spread:float) -> Optional[dict]:
        return next((item for item in data if item['liquidity_status'] == liquidity_status \
                     and item['spread_in_bps'] == min_spread), None)

    def _get_spread_values(self, data:List[dict], liquidity_status:str):
        a = [item['spread_in_bps'] for item in data
                if item['spread_in_bps'] != None and item['liquidity_status'] == liquidity_status]
        return a

    def _get_recommended_execution(self, insight_data:List[dict]) -> Optional[dict]:
        recommended_execution = None
        data = [item for item in insight_data if item['market_status'] == MarketStatus.OPEN.value]

        # find recommendation from good liquidity with min spread
        min_spread = min(self._get_spread_values(data=data,
                        liquidity_status=LiquidityStatus.GOOD.value), default=None)
        recommended_execution = self._find_recommendation_by_liquidity(
            data=data, liquidity_status=LiquidityStatus.GOOD.value, min_spread=min_spread
        ) if min_spread != None else None

        # find recommendation from acceptable liquidity with min spread
        if not recommended_execution:
            min_spread = min(self._get_spread_values(data=data,
                            liquidity_status=LiquidityStatus.ACCEPTABLE.value), default=None)
            recommended_execution = self._find_recommendation_by_liquidity(
                data=data, liquidity_status=LiquidityStatus.ACCEPTABLE.value, min_spread=min_spread
            ) if min_spread != None else None

        # find recommendation from poor liquidity with min spread
        if not recommended_execution:
            min_spread = min(self._get_spread_values(data=data,
                            liquidity_status=LiquidityStatus.POOR.value), default=None)
            recommended_execution = self._find_recommendation_by_liquidity(
                data=data, liquidity_status=LiquidityStatus.POOR.value, min_spread=min_spread
            ) if min_spread != None else None
        return recommended_execution

    def _calculate_spread_bps(self, spread_value:Optional[float]) -> Optional[float]:
        if not spread_value:
            return None
        return spread_value * 10000

    def _is_current_hour(self, dt:datetime) -> bool:
        return dt.date() == self.now.date() and dt.hour == self.now.hour

    def _get_spread_data(self, dt:datetime) -> Optional[float]:
        if self._is_current_hour(dt=dt):
            return self.spread_provider.get_current_time_spread(dt=dt)
        return self.spread_provider.get_average_spread(weekday=dt.weekday(),
                                                     hour=dt.hour)

    def _get_liquidity_display(self, liquidity_status:str, recommend:bool, market_status:str) -> str:
        # Adjust liquidity status based on recommendation and spread provider data
        if recommend and liquidity_status == LiquidityStatus.GOOD.value:
            liquidity_status = LiquidityStatus.GOOD.value
        elif market_status == MarketStatus.OPEN.value and liquidity_status is None and recommend:
            liquidity_status = LiquidityStatus.ACCEPTABLE.value
        elif market_status == MarketStatus.OPEN.value and liquidity_status is None and not recommend:
            liquidity_status = LiquidityStatus.POOR.value
        elif liquidity_status in [LiquidityStatus.ACCEPTABLE.value, LiquidityStatus.POOR.value] and recommend:
            liquidity_status = LiquidityStatus.ACCEPTABLE.value
        return liquidity_status

    def get_liquidity_insight(self) -> dict:
        liquidity_insight = []
        current_date = self.start_date

        if self.sell_currency == self.buy_currency:
            while current_date <= self.end_date:
                exec_status = get_best_execution_status(market_name=self.fx_pair.market,
                                                        ref_date=current_date)
                exec_status = BestExecStatus(**exec_status)

                market_status = MarketStatus.OPEN.value if exec_status.execute_before and \
                    exec_status.session != 'Weekend' else MarketStatus.CLOSE.value

                liquidity_insight.append({
                    'liquidity_status': LiquidityStatus.GOOD.value if
                    market_status == MarketStatus.OPEN.value else None,
                    'time': current_date,
                    'market_status': market_status,
                    'spread_in_bps': 0
                })
                current_date = current_date + timedelta(hours=1)
            return {
                'market': self.fx_pair.market,
                'insight_data': liquidity_insight,
                'recommended_execution': self._get_recommended_execution(
                    insight_data=liquidity_insight)
            }

        while current_date <= self.end_date:
            exec_status = get_best_execution_status(market_name=self.fx_pair.market,
                                                    ref_date=current_date)
            exec_status = BestExecStatus(**exec_status)

            market_status = MarketStatus.OPEN.value if exec_status.execute_before and \
                exec_status.session != 'Weekend' else MarketStatus.CLOSE.value

            spread_value = self._get_spread_data(dt=current_date)

            liquidity_status = None
            liquidity_status = self.spread_provider.get_liquidity_status(weekday=current_date.weekday(),
                                                    hour=current_date.hour, spread=spread_value)
            liquidity_status = self._get_liquidity_display(recommend=exec_status.recommend,
                                                            market_status=market_status,
                                                            liquidity_status=liquidity_status)

            spread_in_bps = self._calculate_spread_bps(spread_value=spread_value)

            liquidity_insight.append({
                'liquidity_status': liquidity_status,
                'time': current_date,
                'market_status': market_status,
                'spread_in_bps': spread_in_bps
            })

            current_date = current_date + timedelta(hours=1)

        return {
            'market': self.fx_pair.market,
            'insight_data': liquidity_insight,
            'recommended_execution': self._get_recommended_execution(
                insight_data=liquidity_insight)
        }
