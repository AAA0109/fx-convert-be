import pandas as pd
from auditlog.registry import auditlog
from hdlib.Hedge.Fx.Util.FxMarketConventionConverter import FxMarketConverter

from hdlib.Hedge.Fx.Util.SpotFxCache import SpotFxCache

from hdlib.DateTime.Date import Date
from main.apps.account.models import Company, CompanyTypes
from main.apps.broker.models import BrokerAccount
from main.apps.currency.models import FxPair, FxPairTypes

from django.db import models

from main.apps.hedge.models import CompanyHedgeAction, CompanyHedgeActionId
from main.apps.oems.support.tickets import OrderTicket
from main.apps.util import ActionStatus

import numpy as np
from typing import Union, Sequence, Tuple, Optional, Dict, List, Iterable

import logging

logger = logging.getLogger(__name__)


class DemoOrders(models.Model):
    """
    Tracks what positions demo account for a company would have submitted to the OMS if they were real accounts.
    Allows us to construct demo company positions.
    """

    # ================================================================================
    #  Members.
    # ================================================================================

    # The company hedge request that was translated to produce this order request.
    company_hedge_action = models.ForeignKey(CompanyHedgeAction, on_delete=models.CASCADE, null=False)

    # The fx pair for this order.
    pair = models.ForeignKey(FxPair, on_delete=models.CASCADE, null=False)

    # The original, un-rounded amount that was requested by the company. This was rounded to be in accordance with lot
    # size conventions, yielding the amount
    unrounded_amount = models.FloatField()

    # The amount of the fx pair that would have been submitted to the OMS if this were a live account
    requested_amount = models.FloatField()

    # The total price of this order. Will initially be null, then will be updated. Can be positive or negative.
    total_price = models.FloatField(null=True)

    @staticmethod
    def create_orders_from_delta(company_hedge_action: CompanyHedgeAction,
                                 aggregated_changes: pd.Series,
                                 spot_fx_cache: SpotFxCache,
                                 fx_converter: FxMarketConverter) -> Iterable['DemoOrders']:
        orders = []
        for fxpair, amount in aggregated_changes.items():
            final_amount = fx_converter.round_to_lot(fx_pair=fxpair, amount=amount)

            price = spot_fx_cache.get_fx(fx_pair=fxpair) * final_amount
            orders.append(DemoOrders(company_hedge_action=company_hedge_action,
                                     pair=FxPair.get_pair(fxpair),
                                     unrounded_amount=amount,
                                     requested_amount=final_amount,
                                     total_price=price))
        if 0 < len(orders):
            return DemoOrders.objects.bulk_create(orders)
        return []

    @staticmethod
    def get_fills_in_range(company: CompanyTypes, start_time: Date, end_time: Date):
        company_ = Company.get_company(company)
        if not company_:
            raise Company.NotFound(company)

        filters = {"company_hedge_action__company": company_}
        if start_time and end_time:
            # NOTE: Range only works if neither time is None.
            filters["company_hedge_action__time__range"] = (start_time, end_time)
        elif start_time:
            filters["company_hedge_action__time__gte"] = start_time
        elif end_time:
            filters["company_hedge_action__time__lte"] = end_time
        else:
            raise ValueError(f"at least one of start_time and end_time should not be null")

        return DemoOrders.objects.filter(**filters)
