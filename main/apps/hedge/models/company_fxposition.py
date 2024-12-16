import numpy as np
from auditlog.registry import auditlog
from django.db import models

from hdlib.DateTime.Date import Date
from main.apps.account.models import CompanyTypes, Company
from main.apps.broker.models import Broker, BrokerAccount
from main.apps.currency.models.fxpair import FxPair, Currency
from main.apps.hedge.models import CompanyEvent
from main.apps.util import get_or_none

from typing import Sequence, Optional, Tuple, Dict, List

import logging
from django.db.models import Q
logger = logging.getLogger(__name__)


class Positions:
    def __init__(self,
                 time: Date,
                 company: Company,
                 positions: Dict[FxPair, Tuple[float, float]],  # Amount, total price
                 broker: Optional[Broker] = None,
                 ):
        self.time = time
        self.company = company
        self.broker = broker
        self.positions = positions

    def has_broker(self) -> bool:
        return self.broker is not None


# ==================
# Type definitions
# ==================


class CompanyFxPosition(models.Model):
    """
    Represents the FX hedge position associated with an entire company. These are the literal, actual positions that
    the company holds, as opposed to FxPosition, which is an attribution of the action positions (these) back to
    company "accounts."
    """

    class Meta:
        verbose_name_plural = "Company FX Positions"
        unique_together = (("snapshot_event", "company", "broker_account", "fxpair"),
                           )

    # The snapshot even that caused this positions snapshot.
    snapshot_event = models.ForeignKey(CompanyEvent, on_delete=models.CASCADE, null=False)

    # The company.
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='fxcompany', null=False)

    # The broker with which this position is held. Broker account being null means these are positions for a
    # DEMO account.
    broker_account = models.ForeignKey(BrokerAccount, on_delete=models.CASCADE,
                                       related_name="fxbroker_account", null=True)

    # The FX pair in which we have a position (these are always stored in the MARKET traded convention)
    fxpair = models.ForeignKey(FxPair, on_delete=models.CASCADE, related_name='company_fxpair', null=False)

    # Amount of this fx pair which defines the position (also = total price in the base currency)
    amount = models.FloatField(null=False, default=0.)

    # Total price for the entire position (always positive), in the quote currency: sum_i (|Q_i| * Spot(t_i))
    # Note that trades in the opposite direction of the current amount will reduce the total price
    total_price = models.FloatField(null=True, default=0.)

    # ============================
    # Properties
    # ============================

    @property
    def average_price(self) -> Tuple[float, Currency]:
        """ Receive the average price (always positive) paid or received on the position, in the quote currency """
        value = self.total_price / self.amount if self.amount != 0 else 0
        return np.abs(value), self.fxpair.quote_currency

    @property
    def is_long(self) -> bool:
        """ Is this a long position (else short) """
        return 0 <= self.amount

    @property
    def is_empty(self) -> bool:
        return self.amount == 0

    def unrealized_pnl(self, current_rate: float) -> Tuple[float, Currency]:
        """
        Retrieve the unrealized PnL in the quote currency
        :param current_rate: float, the current FX rate corresponding to this position
        :return: [PnL, Currency], the unrealized pnl of this position at the current rate
        """
        return self.amount * current_rate - np.sign(self.amount) * self.total_price, self.fxpair.quote_currency

    # ============================
    # Accessors
    # ============================

    @staticmethod
    def get_consolidated_positions(company: Company,
                                   time: Optional[Date],
                                   live_positions: bool = True,
                                   inclusive: bool = True
                                   ) -> Tuple[Dict[FxPair, float], Optional[CompanyEvent]]:

        snapshot_event = CompanyEvent.get_event_of_most_recent_positions(company=company,
                                                                         time=time,
                                                                         inclusive=inclusive)
        if not snapshot_event:
            return {}, None
        return CompanyFxPosition.get_consolidated_positions_for_event(snapshot_event,
                                                                      live_positions=live_positions), snapshot_event

    @staticmethod
    def get_consolidated_positions_for_event(company_event: CompanyEvent, live_positions: bool = True):
        filters = [Q(snapshot_event=company_event)]
        if live_positions:
            filters.append((Q(broker_account__isnull=False) &
                            Q(broker_account__account_type=BrokerAccount.AccountType.LIVE))
                           # If you are backtesting, it is not a live account. Allowing null here broke the backtester.
                           # | Q(broker_account__isnull=True) # this is for the case when we are backtesting a company
                           )
        else:
            # Really, this should be EITHER is null, or the broker account is not null and is type PAPER.
            filters.append(
                Q(broker_account__isnull=False) & Q(broker_account__account_type=BrokerAccount.AccountType.PAPER)
                | Q(broker_account__isnull=True)
            )

        qs = CompanyFxPosition.objects.filter(*filters)
        # Get all the positions from that time.
        output: Dict[FxPair, float] = {}
        for position in qs:
            value = output.setdefault(position.fxpair, 0.) + position.amount
            output[position.fxpair] = value
        return output

    @staticmethod
    def get_consolidated_positions_by_snapshot(company: Company,
                                               start_time: Optional[Date] = None,
                                               end_time: Optional[Date] = None,
                                               live_positions: bool = True,
                                               include_start: bool = True,
                                               include_end: bool = True
                                               ) -> Dict[CompanyEvent, Dict[FxPair, List[float]]]:
        filters = [Q(company=company)]
        if start_time:
            # TODO: Change after deprecating record type.
            if include_start:
                filters.append(Q(snapshot_event__time__gte=start_time))
            else:
                filters.append(Q(snapshot_event__time__gt=start_time))
        if end_time:
            if include_end:
                filters.append(Q(snapshot_event__time__lte=end_time))
            else:
                filters.append(Q(snapshot_event__time__lt=end_time))
        if live_positions:
            filters.append((Q(broker_account__isnull=False) &
                            Q(broker_account__account_type=BrokerAccount.AccountType.LIVE))
                           | Q(broker_account__isnull=True))  # this is for the case when we are backtesting a company
        else:
            # Really, this should be EITHER is null, or the broker account is not null and is type PAPER.
            filters.append(
                Q(broker_account__isnull=False) & Q(broker_account__account_type=BrokerAccount.AccountType.PAPER))

        output: Dict[CompanyEvent, Dict[FxPair, List[float]]] = {}
        for position in CompanyFxPosition.objects.filter(*filters):
            event = position.snapshot_event

            data = output.setdefault(event, {}).get(position.fxpair, [0., 0.])

            value = position.amount + data[0]
            total_price = position.total_price + data[1]
            output[event][position.fxpair] = [value, total_price]
        return output

    @staticmethod
    @get_or_none
    def get_position_objs_for_company(company: Company,
                                      positions_type: Optional[BrokerAccount.AccountType] = None,
                                      time: Optional[Date] = None,
                                      brokers: Optional[Sequence[Broker]] = None,
                                      ) -> Tuple[Optional[CompanyEvent], Sequence['CompanyFxPosition']]:
        """
        Get the Company Fx positions for a company.

        :param company: CompanyTypes, identifier for a company.
        :param time: Date, the positions the company held at this time will be returned. Either this or
            company_hedge_action should be supplied, but not both.
        :param positions_type: CompanyAccountType, What types of positions (live or demo) do we want to get.
        :param brokers, Optional[Sequence[Broker]], optionally, we only select positions from these brokers.
        :return: Dict, the positions in the database, in market traded convention
        """

        event = CompanyEvent.get_event_of_most_recent_positions(company=company, time=time)
        if not event:
            return None, []

        filters = {"company": company}
        if positions_type:
            filters["broker_account__account_type"] = positions_type
        if event:
            filters["snapshot_event"] = event
        if brokers:
            filters["broker_account__in"] = brokers
        return event, CompanyFxPosition.objects.filter(**filters)

    @staticmethod
    @get_or_none
    def get_account_positions_by_broker_account(company: Company,
                                                positions_type: Optional[BrokerAccount.AccountType] = None,
                                                time: Optional[Date] = None,
                                                brokers: Optional[Sequence[Broker]] = None
                                                ) -> Tuple[Optional[Date], Dict[BrokerAccount, Dict[FxPair, float]]]:
        last_event, objs = CompanyFxPosition.get_position_objs_for_company(company=company,
                                                                           time=time,
                                                                           positions_type=positions_type,
                                                                           brokers=brokers)
        positions_by_broker_account = {}
        for position in objs:
            broker_account = position.broker_account
            if broker_account not in positions_by_broker_account:
                positions_by_broker_account[broker_account] = {}
            fxpair = position.fxpair
            positions_by_broker_account[broker_account][fxpair] = position.amount

        return last_event, positions_by_broker_account

    @staticmethod
    @get_or_none
    def get_positions_object(company: Optional[CompanyTypes],
                             time: Optional[Date],
                             positions_type: BrokerAccount.AccountType,
                             ) -> Positions:
        _, positions = CompanyFxPosition.get_position_objs_for_company(company=company,
                                                                       time=time,
                                                                       positions_type=positions_type)

        pos_map = {}
        for pos in positions:
            pos_map[pos.fxpair] = (pos.amount, pos.total_price)

        positions_obj = Positions(company=company,
                                  time=time,
                                  broker=None,
                                  positions=pos_map)
        return positions_obj

    @staticmethod
    def create_company_positions(company: Company,
                                 broker_account: Optional[BrokerAccount],
                                 positions: Dict[FxPair, Tuple[float, float]],
                                 time: Optional[Date] = None,
                                 event: Optional[CompanyEvent] = None
                                 ) -> Tuple[List['CompanyFxPosition'], CompanyEvent]:
        if broker_account is not None and broker_account.company != company:
            raise ValueError(f"the company ({company}) and company of the broker account "
                             f"({broker_account.company}) do not match")
        if time is None and event is None:
            raise ValueError(f"either a time or a company must be provided in create_company_positions")

        # Get or create a company event for recording the positions.
        if time:
            snapshot_event = CompanyEvent.get_or_create_event(time=time, company=company)
        else:
            snapshot_event = event
        snapshot_event.has_company_fx_snapshot = True
        snapshot_event.save()

        logger.debug(f"In create_company_positions, using snapshot event id = {snapshot_event}, reference time {time}.")

        created_positions = []
        for fx_pair, (amount, total_price) in positions.items():
            pos = CompanyFxPosition(snapshot_event=snapshot_event,
                                    company=company,
                                    broker_account=broker_account,
                                    fxpair=fx_pair,
                                    amount=amount,
                                    total_price=total_price)
            created_positions.append(pos)
        if 0 < len(created_positions):
            CompanyFxPosition.objects.bulk_create(created_positions)
            logger.debug(f"Bulk created {len(created_positions)} positions.")

        return created_positions, snapshot_event


auditlog.register(CompanyFxPosition)
