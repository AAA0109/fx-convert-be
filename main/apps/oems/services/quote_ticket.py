from abc import ABC, abstractmethod
from datetime import datetime

from main.apps.core.models.choices import LockSides
from main.apps.corpay.models.spot.instruct_request import InstructRequest
from main.apps.currency.models.fxpair import FxPair
from main.apps.oems.models.quote import Quote
from main.apps.oems.models.ticket import Ticket
from main.apps.oems.models.wait_condition import WaitCondition
from typing import Optional
import uuid


class QuoteToTicketService(ABC):
    quote: Quote
    wait_condition: WaitCondition
    ticket_payload: dict

    def __init__(self, quote_id: int, wait_condition_id: Optional[int] = None) -> None:
        self.quote = Quote.get_quote(quote_id=quote_id)
        if wait_condition_id:
            self.wait_condition = WaitCondition.objects.get(
                pk=wait_condition_id)
        else:
            self.wait_condition = WaitCondition.get_waitcondition_by_quote(quote=self.quote)

        self.ticket_payload = self.__init_base_ticket_payload()

    def __init_base_ticket_payload(self) -> dict:
        if self.quote.pair:
            market_name = FxPair.get_pair_from_currency(
                self.quote.pair.base_currency, self.quote.pair.quote_currency).market
        else:
            market_name = FxPair(
                base_currency=self.quote.from_currency,
                quote_currency=self.quote.to_currency
            ).market

        now = datetime.now()

        value_date = self.wait_condition.recommendation_time.date() if self.wait_condition else now.date()

        from_currency = self.quote.pair.base_currency if self.quote.pair else self.quote.from_currency
        to_currency = self.quote.pair.quote_currency if self.quote.pair else self.quote.to_currency

        trigger_time = self.wait_condition.recommendation_time if self.wait_condition else value_date

        payload = {
            "transaction_id": uuid.uuid4(),
            "company": self.quote.company,
            "sell_currency": from_currency,
            "buy_currency": to_currency,
            "value_date": value_date,
            "draft": False,
            "execution_strategy": Ticket.ExecutionStrategies.TRIGGER.value,
            "trader": None,
            "market_name": market_name,
            "upper_trigger": self.wait_condition.upper_bound if self.wait_condition else None,
            "lower_trigger": self.wait_condition.lower_bound if self.wait_condition else None,
            "trigger_time": self.remove_tzinfo(date=trigger_time)
        }
        return payload

    def convert_quote_to_ticket(self) -> Ticket:
        self.modify_ticket_payload()
        ticket = Ticket._create(**self.ticket_payload)
        ticket.save()
        return ticket

    @abstractmethod
    def modify_ticket_payload(self) -> dict:
        return NotImplementedError

    def remove_tzinfo(self, date: datetime) -> datetime:
        if not date:
            return date
        try:
            new_date = date.replace(tzinfo=None)
            return new_date
        except Exception as e:
            return date

class QuoteToPaymentTicketService(QuoteToTicketService):

    instruct_request: InstructRequest

    def __init__(self, quote_id: int, payment_id: int, wait_condition_id: Optional[int] = None) -> None:
        self.instruct_request = InstructRequest.objects.get(pk=payment_id)
        super().__init__(quote_id, wait_condition_id)

    def modify_ticket_payload(self) -> None:
        from_currency = self.quote.pair.base_currency if self.quote.pair else self.instruct_request.from_currency
        to_currency = self.quote.pair.quote_currency if self.quote.pair else self.instruct_request.to_currency

        ticket_type = Ticket.TicketTypes.PAYMENT_RFQ.value
        action = Ticket.Actions.RFQ

        if from_currency == to_currency:
            ticket_type = Ticket.TicketTypes.PAYMENT.value
            action = Ticket.Actions.EXECUTE

        payload = {
            "sell_currency": from_currency,
            "buy_currency": to_currency,
            'amount': self.instruct_request.amount,
            'lock_side': to_currency,
            'tenor': Ticket.Tenors.SPOT.value,
            'time_in_force': Ticket.TimeInForces._GTC.value,
            'ticket_type': ticket_type,
            'action': action,
        }

        self.ticket_payload.update(payload)


class QuoteToTicketFactory():
    """ Quote to Ticket Service Factory """

    @staticmethod
    def quote_to_ticket(quote_id: int, wait_condition_id: Optional[int] = None, payment_id: Optional[int] = None) -> Ticket:
        if payment_id:
            quote_to_spot_ticket = QuoteToPaymentTicketService(
                quote_id=quote_id, wait_condition_id=wait_condition_id, payment_id=payment_id)
            return quote_to_spot_ticket.convert_quote_to_ticket()
        else:
            raise Exception(
                "Must provide instruct request id")
