import logging
from typing import Union, Sequence, Tuple, Optional, Dict, List

import numpy as np
from auditlog.registry import auditlog
from django.conf import settings
from django.db import models
from hdlib.DateTime.Date import Date
from rest_framework.authtoken.models import Token

from main.apps.account.models import Company
from main.apps.broker.models import BrokerAccount
from main.apps.currency.models import FxPair, FxPairTypes
from main.apps.hedge.models import CompanyHedgeAction, CompanyHedgeActionId
from main.apps.oems.support.tickets import OrderTicket
from main.apps.util import ActionStatus

logger = logging.getLogger(__name__)


class OMSOrderRequest(models.Model):
    """
    Table that records requests made to the OMS. This records the request and fulfilment of the request.
    """

    class OrderStatus(models.IntegerChoices):
        OPEN = 1  # An open order (in the sense that we haven't reconciled it yet)
        CLOSED = 2  # A closed order, in the sense that we have fully reconciled it

    # ================================================================================
    #  Members.
    # ================================================================================

    # The company hedge request that was translated to produce this order request.
    company_hedge_action = models.ForeignKey(CompanyHedgeAction, on_delete=models.CASCADE, null=False)

    # The broker account the request is to be sent to.
    broker_account = models.ForeignKey(BrokerAccount, on_delete=models.CASCADE, null=False)

    # The fx pair for this order.
    pair = models.ForeignKey(FxPair, on_delete=models.CASCADE, null=False)

    # The original, un-rounded amount that was requested by the company. This was rounded to be in accordance with lot
    # size conventions, yielding the amount
    unrounded_amount = models.FloatField()

    # The amount of the fx pair that was submitted to the OMS
    requested_amount = models.FloatField()

    # The amount of the fx pair that was filled by the OMS. Will initially be null, then will be updated.
    filled_amount = models.FloatField(null=True)

    # The total price of this order. Will initially be null, then will be updated. Can be positive or negative.
    total_price = models.FloatField(null=True)

    # Commission from trading.
    commission = models.FloatField(null=True)

    # Counter currency commission.
    cntr_commission = models.FloatField(null=True)

    # Status of the order.
    status = models.IntegerField(null=False, default=OrderStatus.OPEN, choices=OrderStatus.choices)

    # Expected cost of the order. This is set using the rate data that was used to make the hedging or trading
    # decision, and can be used to gather statistics on how reliable our spot data is.
    expected_cost = models.FloatField(null=True)

    # ================================================================================
    #  Accessors.
    # ================================================================================

    @property
    def is_closed(self) -> bool:
        return self.status == OMSOrderRequest.OrderStatus.CLOSED

    def to_order_ticket(self) -> OrderTicket:

        try:
            auth_token = Token.objects.get(user__email=settings.DASHBOARD_API_USER)
        except Token.DoesNotExist:
            raise Exception(f"Token for {settings.DASHBOARD_API_USER} does not exist.")

        return OrderTicket(
            fx_pair=self.pair,
            amount=self.requested_amount,
            company_hedge_action=self.company_hedge_action,
            broker_account=self.broker_account,
            base_url=settings.DASHBOARD_API_URL,
            auth_token=auth_token.key
        )

    @property
    def print_status(self) -> str:
        return "CLOSED" if self.status == OMSOrderRequest.OrderStatus.CLOSED else "OPEN"

    @property
    def average_fill_price(self) -> float:
        """ Get the average price that this order was filled at """
        if self.filled_amount != 0:
            # Note that total price is always positive.
            return self.total_price / abs(self.filled_amount)
        return np.nan

    @staticmethod
    def get_requests_for_action(company_hedge_action: Union[CompanyHedgeAction, CompanyHedgeActionId]
                                ) -> Sequence['OMSOrderRequest']:
        """
        Get all account hedge
        """
        objs = OMSOrderRequest.objects.filter(company_hedge_action=company_hedge_action)
        for request in objs:
            yield request

    @staticmethod
    def get_requests_by_event(company: Company,
                              start_time: Optional[Date] = None,
                              end_time: Optional[Date] = None) -> Dict[Date, List['OMSOrderRequest']]:
        filters = {"company_hedge_action__company": company}
        if start_time:
            filters["start_time__gte"] = start_time
        if end_time:
            filters["end_time__lte"] = end_time
        objs = OMSOrderRequest.objects.filter(**filters)

        output: Dict[Date, List[OMSOrderRequest]] = {}
        for obj in objs:
            output.setdefault(Date.from_datetime(obj.company_hedge_action.time), []).append(obj)
        return output

    # ================================================================================
    #  Mutators.
    # ================================================================================

    @staticmethod
    def add_oms_order_request(
        company_hedge_action: CompanyHedgeAction,
        broker_account: BrokerAccount,
        fx_pair: FxPairTypes,
        unrounded_amount: float,
        rounded_amount: float,
        expected_cost: Optional[float] = None
    ) -> Tuple[ActionStatus, Optional['OMSOrderRequest']]:

        logging.info(f"Adding OMS order request for {company_hedge_action.company}, "
                     f"{rounded_amount} of {fx_pair}, to be sent to {broker_account}.")
        if rounded_amount == 0:
            return ActionStatus.log_and_no_change(f"Amount of the order was 0"), None

        fx_pair_ = FxPair.get_pair(fx_pair)
        if fx_pair_ is None:
            return ActionStatus.log_and_error(f"Could not find fx pair {fx_pair}"), None
        try:
            request = OMSOrderRequest.objects.create(company_hedge_action=company_hedge_action,
                                                     pair=fx_pair_,
                                                     requested_amount=rounded_amount,
                                                     unrounded_amount=unrounded_amount,
                                                     broker_account=broker_account,
                                                     expected_cost=expected_cost)
            return ActionStatus.log_and_success("Successfully create the OMSOrderRequest"), request
        except Exception as ex:
            return ActionStatus.log_and_error(f"Error adding oms order request: {ex}"), None


auditlog.register(OMSOrderRequest)
