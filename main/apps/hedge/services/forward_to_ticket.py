import logging
import uuid

from abc import ABC, abstractmethod
from datetime import datetime
from django.db import transaction
from typing import List, Optional, Union

from main.apps.core.models.choices import LockSides
from main.apps.currency.models.fxpair import FxPair
from main.apps.hedge.dataclasses.hard_limit import AutopilotHardLimits
from main.apps.hedge.models.draft_fx_forward import DraftFxForwardPosition
from main.apps.hedge.services.hard_limits import AutopilotHardLimitProvider
from main.apps.oems.models.ticket import Ticket
from main.apps.strategy.models.choices import Strategies

logger = logging.getLogger(__name__)


class ForwardToTicketService(ABC):
    draft_fwd_position: DraftFxForwardPosition
    ticket_attributes: dict

    def __init__(self, draft_fwd_position: Union[int, DraftFxForwardPosition]) -> None:
        if isinstance(draft_fwd_position, int):
            self.draft_fwd_position = draft_fwd_position
        elif isinstance(draft_fwd_position, DraftFxForwardPosition):
            self.draft_fwd_position = draft_fwd_position

        self.ticket_attributes = self.__init_base_ticket_attributes()

    def __init_base_ticket_attributes(self) -> dict:
        from_currency = self.draft_fwd_position.account.company.currency
        to_currency = self.draft_fwd_position.cashflow.currency

        market_name = FxPair.get_pair_from_currency(
            base_currency=from_currency,
            quote_currency=to_currency
        ).market

        # Flip buy/sell currency if amount is negative
        if self.draft_fwd_position.cashflow.amount < 0:
            from_currency = self.draft_fwd_position.cashflow.currency
            to_currency = self.draft_fwd_position.account.company.currency
            market_name = FxPair.get_inverse_pair(pair=market_name)

        value_date: datetime = self.draft_fwd_position.cashflow.date
        trigger_time = self.draft_fwd_position.cashflow.date

        attributes = {
            'action': Ticket.Actions.EXECUTE,
            'amount': abs(self.draft_fwd_position.cashflow.amount),
            'cashflow_id': self.draft_fwd_position.cashflow.pk,
            'company': self.draft_fwd_position.account.company,
            'date_conversion': Ticket.DateConvs.NEXT.value,
            'draft': False,
            'execution_strategy': Ticket.ExecutionStrategies.TRIGGER.value,
            'sell_currency': from_currency,
            'lock_side': to_currency,
            'lower_trigger': None,
            'market_name': market_name,
            'tenor': Ticket.Tenors.FWD,
            'ticket_type': Ticket.TicketTypes.HEDGE,
            'time_in_force': Ticket.TimeInForces._GTC.value,
            'buy_currency': to_currency,
            'trader': None,
            'trigger_time': self.remove_tzinfo(date=trigger_time),
            'upper_trigger': None,
            'value_date': value_date.date(),
        }
        return attributes

    def remove_tzinfo(self, date: datetime) -> datetime:
        if not date:
            return date
        try:
            new_date = date.replace(tzinfo=None)
            return new_date
        except Exception as e:
            return date

    def convert_forward_to_ticket(self) -> List[Ticket]:
        self.modify_ticket_attributes()
        ticket = Ticket._create(**self.ticket_attributes)
        ticket.save()

        self.draft_fwd_position.status = DraftFxForwardPosition.Status.ACTIVE
        self.draft_fwd_position.save()

        return [ticket]

    @abstractmethod
    def modify_ticket_attributes(self):
        return NotImplementedError


class AutopilotForwardToTicketService(ForwardToTicketService):

    hard_limit_provider: AutopilotHardLimitProvider
    triggers: AutopilotHardLimits = None

    def __init__(self, draft_fwd_position: Union[int, DraftFxForwardPosition]) -> None:
        super().__init__(draft_fwd_position)
        self.hard_limit_provider = AutopilotHardLimitProvider(draft_fwd_position=draft_fwd_position)
        if self.draft_fwd_position.risk_reduction < 1:
            self.triggers = self.hard_limit_provider.calculate_hard_limit()

    def modify_ticket_attributes(self):
        additional_attributes = {
                'hedge_strategy': Ticket.HedgeStrategies.AUTOPILOT
        }

        if self.triggers:
            additional_attributes['upper_trigger'] = self.triggers.upper_target
            additional_attributes['lower_trigger'] = self.triggers.lower_target

        self.ticket_attributes.update(additional_attributes)

    def convert_forward_to_ticket(self) -> List[Ticket]:
        if not self.triggers:
            return super().convert_forward_to_ticket()

        tickets = super().convert_forward_to_ticket()

        additional_attributes = {
            'upper_trigger': None,
            'lower_trigger': None
        }

        self.ticket_attributes.update(additional_attributes)

        ticket_with_no_limits = Ticket._create(**self.ticket_attributes)
        ticket_with_no_limits.save()
        tickets.append(ticket_with_no_limits)
        return tickets


class ForwardToTicketFactory:

    @staticmethod
    def populate_forward_to_convert(strategy: str) -> List[DraftFxForwardPosition]:
        fwd_to_convert: List[DraftFxForwardPosition] = []

        now = datetime.utcnow()

        fwd_drafts = DraftFxForwardPosition.objects.filter(
            status=DraftFxForwardPosition.Status.PENDING_ACTIVATION,
            cashflow__isnull=False,
            cashflow__date__gte=now)
        for draft in fwd_drafts:
            if draft.strategy == strategy:
                fwd_to_convert.append(draft)
        return fwd_drafts

    @staticmethod
    def convert_forward_to_ticket(draft_fwd_position: Union[int, DraftFxForwardPosition], strategy: str) -> Optional[List[Ticket]]:
        fwd_to_ticket_service = None

        if strategy == Strategies.AUTOPILOT:
            fwd_to_ticket_service = AutopilotForwardToTicketService(draft_fwd_position=draft_fwd_position)
        elif strategy == Strategies.PARACHUTE:
            fwd_to_ticket_service = None

        if fwd_to_ticket_service:
            try:
                with transaction.atomic():
                    ticket = fwd_to_ticket_service.convert_forward_to_ticket()
                    return ticket
            except Exception as e:
                logger.error(f"{e}")

        return None

    @staticmethod
    def strategy_exist(strategy:str) -> bool:
        strategy = strategy.lower()

        for value, text in Strategies.choices:
            if value == strategy:
                return True

        return False
