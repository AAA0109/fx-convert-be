import logging
import pytz

from datetime import datetime, timedelta
from typing import List, Optional, Union
from django.conf import settings
from main.apps.cashflow.models.cashflow import SingleCashFlow
from main.apps.oems.backend.date_utils import check_after

from main.apps.oems.backend.slack_utils import make_buttons, make_input_section, make_markdown_ladder
from main.apps.oems.backend.ticket import Ticket
from main.apps.oems.models.ticket import Ticket as DjangoTicket
from main.apps.oems.models.cny import CnyExecution
from main.apps.oems.models.manual_request import ManualRequest
from main.apps.payment.models.payment import Payment

logger = logging.getLogger(__name__)


class NDFTicketNotif:
    ticket:Union[Ticket, DjangoTicket]
    NY_TZ:pytz.tzinfo.DstTzInfo = pytz.timezone('America/New_York')
    UTC_TZ:pytz.tzinfo.DstTzInfo = pytz.timezone('UTC')

    def __init__(self, ticket:Union[Ticket, DjangoTicket, str]) -> None:
        self.ticket = ticket
        if isinstance(ticket, str):
            self.ticket = DjangoTicket.objects.get(ticket_id=ticket)

    def get_manual_request_kwargs(self) -> dict:
        kwargs = {}

        ticket = self.ticket.as_django_model() if isinstance(self.ticket, Ticket) else \
            self.ticket

        sell_currency_id = self.ticket.sell_currency_id if isinstance(self.ticket, Ticket) else \
            self.ticket.sell_currency.pk
        buy_currency_id = self.ticket.buy_currency_id if isinstance(self.ticket, Ticket) else \
            self.ticket.buy_currency.pk
        lock_side_id = self.ticket.lock_side_id if isinstance(self.ticket, Ticket) else \
            self.ticket.lock_side.pk

        kwargs = {
            'sell_currency_id': sell_currency_id,
            'buy_currency_id': buy_currency_id,
            'ticket': ticket,
            'lock_side_id': lock_side_id,
            'action': self.ticket.action,
            'instrument_type': self.ticket.instrument_type,
            'exec_broker': self.ticket.broker,
            'clearing_broker': self.ticket.broker,
            'amount': self.ticket.amount,
            'time_in_force': ManualRequest.TimeInForces._15MIN,
            'value_date': self.ticket.value_date,
            'fixing_date': self.ticket.fixing_date,
            'on_behalf_of': self.ticket.get_company().name,
            'text': self.ticket.notes,
        }

        return kwargs

    def generate_manual_request(self) -> ManualRequest:

        kwargs = self.get_manual_request_kwargs()

        try:
            mreq = ManualRequest._create(**kwargs)
            mreq.save()
            return mreq
        except Exception as e:
            logger.exception(e)
            raise e

    def get_execution_timing(self) -> Optional[str]:
        try:
            cashflow = SingleCashFlow.objects.get(ticket_id=self.ticket.ticket_id)
            payment = Payment.objects.get(cashflow_generator=cashflow.generator)
            return payment.execution_timing
        except Exception as e:
            logger.exception(e, exc_info=True)
            return ''

    def generate_mark_down_ladder(self, mreq:ManualRequest) -> dict:
        execution_time = self.ticket.trigger_time if self.ticket.trigger_time \
              else self.ticket.end_time
        if not execution_time:
            execution_time = datetime.now()
        if isinstance(execution_time, str):
            execution_time = datetime.fromisoformat(execution_time)

        kv_pairs = {
            'TICKET_ID': str(self.ticket.ticket_id),
            'EXECUTION_STRATEGY': self.get_execution_timing(),
            'EXECUTION_TIME': execution_time.astimezone(tz=self.NY_TZ),
            'ACTION': mreq.action.upper(),
            'ON_BEHALF_OF': mreq.on_behalf_of,
            'SELL_CCY': mreq.sell_currency.get_mnemonic(),
            'BUY_CCY': mreq.buy_currency.get_mnemonic(),
            'LOCK_SIDE': mreq.lock_side,
            'AMOUNT': mreq.amount,
            'VALUE_DATE': mreq.value_date,
            'EXEC_BROKER': mreq.exec_broker,
            'CLR_BROKER': mreq.clearing_broker,
            'TEXT': mreq.text,
        }

        return kv_pairs

    def get_text(self, manual_req:ManualRequest, manual_request_id:Optional[str] = None,
                 permalink:Optional[str] = None) -> Optional[str]:
        if self.ticket.instrument_type != DjangoTicket.InstrumentTypes.NDF:
            return None

        if manual_request_id:
            return manual_request_id

        now = datetime.now(tz=self.UTC_TZ)
        reminder_time = manual_req.last_reminder_sent
        first_mreq_time = manual_req.created

        if isinstance(first_mreq_time, str):
            first_mreq_time = datetime.fromisoformat(first_mreq_time)

        if reminder_time is None:
            return None

        execution_timing = self.get_execution_timing()

        # logger.info(f"{now} {reminder_time} : {timedelta(seconds=(now - reminder_time).seconds)}")

        # TO DO : Send once on the best ex, not spam
        if execution_timing == Payment.ExecutionTiming.STRATEGIC_EXECUTION and \
            self.ticket.trigger_time and check_after(self.ticket.trigger_time):
                # return f"Ticket {self.ticket.id} Strategic Execution Has Triggered. " + \
                #         f"If you have not booked this ticket, please attend to it. {permalink}"
            return ''
        elif execution_timing in [Payment.ExecutionTiming.IMMEDIATE, Payment.ExecutionTiming.STRATEGIC_EXECUTION] and \
            abs(now.minute - reminder_time.minute) >= 15:
            diff = now - first_mreq_time

            return f"Ticket {self.ticket.ticket_id} Remains OPEN. " + \
                f"It has been open for {str(timedelta(seconds=diff.seconds))}, please attend to it. {permalink}"

        return None

    def get_button_action(self, include_button:bool = True) -> dict:
        if not include_button:
            return False
        if self.ticket.action == DjangoTicket.Actions.RFQ:
            return {'rfq_submit_action': 'submit', 'rfq_cancel_action': 'cancel'}
        elif self.ticket.action == DjangoTicket.Actions.EXECUTE:
            return {'execute_submit_action': 'submit', 'execute_cancel_action': 'cancel'}
        return {}

    def get_form_field(self, quote_form:List[dict]) -> List[dict]:
        if self.ticket.action == DjangoTicket.Actions.RFQ:
            quote_form.append(make_input_section('rate', 'Enter the rate'))
            quote_form.append(make_input_section('note', 'Enter notes'))
        elif self.ticket.action == DjangoTicket.Actions.EXECUTE:
            quote_form.append( make_input_section( 'broker_id', 'Enter the broker deal number' ) )
            quote_form.append( make_input_section( 'all_in_rate', 'Enter the all in rate' ) )
            quote_form.append( make_input_section( 'amount', 'Enter the amount' ) )
            quote_form.append( make_input_section( 'cntr_amount', 'Enter the cntr amount' ) )
            quote_form.append( make_input_section( 'note', 'Enter notes' ) )
        return quote_form

    def send_manual_request(self, mreq:Optional[ManualRequest] = None) -> None:
        if self.ticket.instrument_type == DjangoTicket.InstrumentTypes.NDF and \
            self.ticket.tenor == DjangoTicket.Tenors.FWD and \
            self.ticket.rfq_type == CnyExecution.RfqTypes.MANUAL:

            try:
                if mreq is None:
                    mreq = self.generate_manual_request()

                subject = f'{mreq.action} Request'

                kv_pairs = self.generate_mark_down_ladder(mreq=mreq)

                quote_form = []
                quote_form.append(make_markdown_ladder(kv_pairs))
                quote_form.append(make_input_section('rate', 'Enter the rate'))
                quote_form.append(make_input_section('note', 'Enter notes'))
                quote_form.append(make_buttons(self.get_button_action()))

                text = self.get_text()

                if settings.SLACK_NOTIFICATIONS_CHANNEL:
                    channel = settings.SLACK_NOTIFICATIONS_CHANNEL
                    mreq.send_slack_msg(str(mreq.pk), quote_form, channel=channel)
            except Exception as e:
                logger.exception(e, exc_info=True)
