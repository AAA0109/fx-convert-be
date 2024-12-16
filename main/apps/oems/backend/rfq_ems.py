from datetime import datetime
import logging
from typing import Union

from django.conf import settings
import pytz

from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.services.initial_marketdata import get_recent_data
from main.apps.oems.backend.date_utils import check_after
from main.apps.oems.backend.ems import EmsBase
from main.apps.oems.backend.rfq_utils import do_api_rfq, calculate_external_quote
from main.apps.oems.backend.slack_utils import make_markdown_ladder, make_buttons, make_input_section
from main.apps.oems.backend.states import INTERNAL_STATES
from main.apps.oems.backend.ticket import Ticket
from main.apps.oems.backend.utils import random_decision
from main.apps.oems.models.cny import CnyExecution
from main.apps.oems.models.manual_request import ManualRequest
from main.apps.oems.models.ticket import Ticket as DjangoTicket
from main.apps.oems.services.ndf_ticket_notif import NDFTicketNotif

logger = logging.getLogger(__name__)


# ==================

class RfqEms(EmsBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_ticket_dispatch(INTERNAL_STATES.PEND_RFQ, self.check_pend_rfq)

    def is_rfq_expired(self, ticket):
        if ticket.external_quote_expiry and check_after(ticket.external_quote_expiry):
            return True
        if False and ticket.manual_quote_expiry and check_after(ticket.manual_quote_expiry):
            return True
        # check if a manual rfq has expired bc of unmanned desk
        return False

    def api_rfq(self, ticket):
        return do_api_rfq(ticket)

    # ==================================

    def send_manual_request(self, ticket, mreq:ManualRequest):
        # TODO: send an alert on slack
        # send an alert on victor ops?
        # send an email alert?

        subject = f'{mreq.action} Request'

        quote_form = []
        header = str(mreq.id)

        ndf_notif_svc = NDFTicketNotif(ticket=ticket)
        header = ndf_notif_svc.get_text(manual_request_id=str(mreq.id), manual_req=mreq)
        kv_pairs = ndf_notif_svc.generate_mark_down_ladder(mreq=mreq)
        btn_action = ndf_notif_svc.get_button_action()

        quote_form.append(make_markdown_ladder(kv_pairs))
        quote_form = ndf_notif_svc.get_form_field(quote_form=quote_form)
        quote_form.append(make_buttons(btn_action))

        if settings.SLACK_NOTIFICATIONS_CHANNEL:
            channel = settings.SLACK_NOTIFICATIONS_CHANNEL
            mreq.send_slack_msg(header, quote_form, channel=channel)
            mreq.update_reminder_time()
            mreq.upsert_manual_request_form_link()

        if settings.VICTOR_OPS_ENABLED:
            mreq.send_victor_ops_alert(subject)

    # ==================================

    def do_rfq(self, ticket: Union[Ticket, DjangoTicket], internal_only=False):

        # lookup somewhere for market + customer if its api market or manual

        rfq_type = ticket.rfq_type

        # if API market
        if rfq_type == CnyExecution.RfqTypes.API:
            ticket.quote_type = rfq_type
            return self.api_rfq(ticket)
        elif rfq_type == CnyExecution.RfqTypes.MANUAL:
            # handle desk routing in the config call as well
            # POST to the manual rfq endpoint and get back the rfq_id

            kwargs = {
                'sell_currency_id': ticket.sell_currency_id,
                'buy_currency_id': ticket.buy_currency_id,
                'ticket': ticket.as_django_model(),
                'lock_side_id': ticket.lock_side_id,
                'action': ticket.action,
                'instrument_type': ticket.instrument_type,
                'exec_broker': ticket.broker,
                'clearing_broker': ticket.broker,
                'amount': ticket.amount,
                'time_in_force': ManualRequest.TimeInForces._DAY,
                'value_date': ticket.value_date,
                'fixing_date': ticket.fixing_date,
                'on_behalf_of': ticket.get_company().name,
                'text': ticket.notes,
                'last_reminder_sent': datetime.now(tz=pytz.UTC)
            }

            try:
                mreq = ManualRequest._create(**kwargs)
                mreq.save()
            except Exception as e:
                logger.exception(e)
                ticket.error_message = 'Manual RFQ failed for this ticket'
                ticket.change_internal_state(INTERNAL_STATES.FAILED)
                return False

            self.send_manual_request(ticket, mreq)
            ticket.change_internal_state(INTERNAL_STATES.PEND_RFQ)
            ticket.internal_quote_id = mreq.id
            ticket._mreq = mreq
        elif rfq_type == CnyExecution.RfqTypes.INDICATIVE:
            pass
            # TODO: come up with an indicative price
        else:
            ticket.error_message = 'We are unable to provide RFQ for this ticket'
            ticket.change_internal_state(INTERNAL_STATES.FAILED)
            return False

        return True  # all good to proceed

    def do_accept(self, ticket):
        ret = self.do_rfq(ticket)
        if not ret:
            pass
        return True  # something goes wrong and you want remediation

    def check_pend_rfq(self, ticket):
        super().check_pend_rfq(ticket=ticket)

        if ticket.rfq_type == CnyExecution.RfqTypes.MANUAL:

            # TODO: check for expiry

            if ticket.internal_quote_id is None:
                ticket.notes = 'Something went wrong with RFQ State'
                ticket.change_internal_state(INTERNAL_STATES.FAILED)
                self.rem_ticket(ticket)
            else:
                # if we are waiting for a manual rfq, check if it's ready
                if hasattr(ticket, '_mreq'):
                    mreq = ticket._mreq
                    mreq.refresh_from_db()

                    fake_fill = False
                    # TODO HACK FAKE FILL HERE
                    if fake_fill and self.is_not_prod() and random_decision(0.01):
                        try:
                            fxpair = FxPair.get_pair(ticket.market_name)
                            spot_rate, fwd_points, ws_feed = get_recent_data(fxpair, ticket.value_date)
                            mreq.booked_rate = spot_rate['bid'] + fwd_points['bid'] if ticket.side == 'Sell' else \
                            spot_rate['ask'] + fwd_points['ask']
                        except:
                            pass

                else:
                    mreq = ManualRequest.objects.get(pk=ticket.internal_quote_id)
                    ticket._mreq = mreq

                if mreq.booked_rate is not None:
                    ticket.quote_source = ticket.broker
                    ticket.internal_quote = mreq.booked_rate
                    calculate_external_quote(mreq.booked_rate, ticket)
                    ticket.internal_quote_info = mreq.export()
                    mreq.close()
                    ticket.change_internal_state(INTERNAL_STATES.PENDRECON)
                    if ticket.action == DjangoTicket.Actions.RFQ: self.rem_ticket(ticket)
                elif mreq.is_cancelled():
                    mreq.close()
                    ticket.change_internal_state(INTERNAL_STATES.FAILED)
                    self.rem_ticket(ticket)
                elif mreq.is_expired():
                    # TODO: edit the slack alert/ack victor ops
                    # potentially send a new alert?
                    ticket.change_internal_state(INTERNAL_STATES.EXPIRED)
                    self.rem_ticket(ticket)
                elif self.is_rfq_expired(ticket):  # expired
                    mreq.close()
                    ticket.change_internal_state(INTERNAL_STATES.EXPIRED)
                    self.rem_ticket(ticket)

        elif ticket.rfq_type == CnyExecution.RfqTypes.API:
            pass  # for right now this is synchronous
        elif ticket.rfq_type == CnyExecution.RfqTypes.INDICATIVE:
            pass  # for right now this is synchronous

    def check_error(self, ticket):
        # handle rfq specific error stuff
        pass
