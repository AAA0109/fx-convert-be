from typing import Iterable, Optional

from auditlog.registry import auditlog

from main.apps.broker.models import BrokerTypes
from main.apps.currency.models import CurrencyTypes
from main.apps.hedge.models import TieredRate
from main.apps.util import get_or_none


class InterestRate(TieredRate):

    @staticmethod
    @get_or_none
    def get_rates(currency: CurrencyTypes, broker: BrokerTypes) -> Iterable['InterestRate']:
        return InterestRate.objects.filter(currency=currency, broker=broker).order_by("tier_from")

    @staticmethod
    def set_rate(broker: BrokerTypes, currency: CurrencyTypes, tier_from: float, tier_to: Optional[float], rate: float):
        ir, created = InterestRate.objects.update_or_create(broker=broker, currency=currency,
                                                            tier_from=tier_from, tier_to=tier_to,
                                                            rate=rate)
        return ir

auditlog.register(InterestRate)
