import uuid

from main.apps.oems.backend.date_utils import now, add_time, check_after
from main.apps.oems.backend.rfq_ems    import RfqEms
from main.apps.currency.models         import Currency
from main.apps.oems.models.cny         import CnyExecution
from main.apps.oems.models.ticket      import Ticket
from main.apps.oems.backend.states     import INTERNAL_STATES, ERRORS
from main.apps.oems.backend.enums      import RfqType
from main.apps.oems.backend.api        import pangea_client
from main.apps.account.models.company import Company

from main.apps.oems.models.manual_request import ManualRequest
from main.apps.oems.backend.slack_utils import make_markdown_ladder, make_buttons, make_input_section
from main.apps.oems.backend.utils import random_decision
from main.apps.oems.backend.rfq_utils  import do_api_execute, do_pre_exec_check
from django.conf import settings
from main.apps.marketdata.services.initial_marketdata import get_recent_data
from main.apps.currency.models.fxpair import FxPair

# =============================================================================

class CorpayEms(RfqEms):

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        # self.register_ticket_dispatch( INTERNAL_STATES.PEND_RFQ, self.check_pend_rfq )

    def check_quote_refresh( self, ticket ):
        # TODO: make sure that new internal quote is not outside our external_quote otherwise we lose money
        # what do we do when that happens?
        pass

    def execute_manual_trade( self, ticket ):

        subject = f'{ticket.action} Request'

        kwargs = {
            'sell_currency_id': ticket.sell_currency_id,
            'buy_currency_id': ticket.buy_currency_id,
            'ticket': ticket,
            'lock_side_id': ticket.lock_side_id,
            'action': ticket.action,
            'instrument_type': ticket.instrument_type,
            'exec_broker': ticket.broker,
            'clearing_broker': ticket.broker,
            'amount': ticket.amount,
            'time_in_force': ManualRequest.TimeInForces._1HOUR,
            'value_date': ticket.value_date,
            'fixing_date': ticket.fixing_date,
            'on_behalf_of': Company.objects.get(pk=ticket.company_id).name,
            'text': ticket.notes,
        }

        try:
            mreq = ManualRequest._create(**kwargs)
            mreq.save()
        except:
            ticket.error_message = 'Manual execution failed for this ticket'
            ticket.change_internal_state( INTERNAL_STATES.FAILED )
            return False

        kv_pairs = {
            'ID': f'MR-{mreq.id}',
            'ACTION': mreq.action.upper(),
            'ON_BEHALF_OF': mreq.on_behalf_of,
            'STATUS': mreq.status,
            'EXPIRY': mreq.expiration_time.isoformat(),
            'SELL_CCY': mreq.sell_currency.get_mnemonic(),
            'BUY_CCY': mreq.buy_currency.get_mnemonic(),
            'LOCK_SIDE': mreq.lock_side.get_mnemonic(),
            'AMOUNT': mreq.amount,
            'MARKET_NAME': mreq.market_name,
            'SIDE': mreq.side,
            'INSTRUMENT': mreq.instrument_type,
            'VALUE_DATE': mreq.value_date,
            'EXEC_BROKER': mreq.exec_broker,
            'CLR_BROKER': mreq.clearing_broker,
            'TEXT': mreq.text,
        }

        quote_form = []
        quote_form.append( make_markdown_ladder(kv_pairs) )
        quote_form.append( make_input_section( 'broker_id', 'Enter the broker deal number' ) )
        quote_form.append( make_input_section( 'all_in_rate', 'Enter the all in rate' ) )
        quote_form.append( make_input_section( 'amount', 'Enter the amount' ) )
        quote_form.append( make_input_section( 'cntr_amount', 'Enter the cntr amount' ) )
        quote_form.append( make_input_section( 'note', 'Enter notes' ) )
        quote_form.append( make_buttons({'execute_submit_action': 'submit', 'execute_cancel_action': 'cancel'}) ) # should be reject

        if settings.SLACK_NOTIFICATIONS_CHANNEL:
            channel = settings.SLACK_NOTIFICATIONS_CHANNEL
            mreq.send_slack_msg( str(mreq.id), quote_form, channel=channel )

        if settings.VICTOR_OPS_ENABLED:
            mreq.send_victor_ops_alert( subject )

        ticket.transaction_time = now()
        ticket.change_internal_state( INTERNAL_STATES.WORKING )
        ticket._mreq = mreq

    def do_accept( self, ticket ):

        # TODO: do the shit to start the payment here with the corpay api
        # Put ticket on order_queue to corpay

        if ticket.rfq_type == CnyExecution.RfqTypes.API:

            quote_id = ticket.external_quote_id or ticket.internal_quote_id

            if not quote_id:
                if not self.do_rfq( ticket ):
                    return True

            if ticket.external_quote_id:

                # if internal quote id has expired but not external_quote_id, refresh

                if self.is_rfq_expired( ticket ): # expired
                    ticket.change_internal_state( INTERNAL_STATES.EXPIRED )
                    self.rem_ticket( ticket )
                    return False

                # if internal quote id has expired but not external_quote_id, refresh
                if ticket.internal_quote_expiry and check_after( ticket.internal_quote_expiry ):
                    if not self.do_rfq(ticket, internal_only=True):
                        return True
                    else:
                        self.check_quote_refresh( ticket )

                if ticket.external_quote_id:

                    ticket.save()

                    if do_pre_exec_check( ticket ):
                        ret = do_api_execute( ticket )
                        if not ret:
                            self.rem_ticket( ticket )
                        return ret
                    else:
                        # for right now... this will fail because its easier than otherwise
                        if ticket.internal_state != INTERNAL_STATES.FAILED:
                            ticket.error_message = 'pre-exec failure'
                            ticket.change_internal_state( INTERNAL_STATES.FAILED )
                        self.rem_ticket( ticket )

                    # if settlement information is filled out deal with it now
                    # otherwise pass it back ??

                    # change phase to settlement
                    # instruct the deal
                    # TODO: setup settlement in another
                    # print('deal with settlement now')
                    # self.enqueue_oms( ticket, OMS_EMS_ACTIONS.UPDATE )
                    # ticket.save()

        elif ticket.rfq_type == CnyExecution.RfqTypes.MANUAL:
            quote_id = ticket.external_quote_id or ticket.internal_quote_id
            if not quote_id:
                if not self.do_rfq( ticket ):
                    return True
            if ticket.external_quote_id:
                ticket.save()
                self.execute_manual_trade( ticket )
        elif ticket.rfq_type == CnyExecution.RfqTypes.INDICATIVE:
            self.execute_manual_trade( ticket )
        elif ticket.rfq_type == CnyExecution.RfqTypes.UNSUPPORTED:
            # TODO: generate a manual execution request here
            pass
        elif ticket.rfq_type == CnyExecution.RfqTypes.NORFQ:
            # go right to execution. manual request
            self.execute_manual_trade( ticket )

        return True

    def check_working( self, ticket ):

        # TODO: should be NORFQ_MANUAL, NORFQ_API
        if ticket.rfq_type == CnyExecution.RfqTypes.NORFQ:
            # ask broker for update
            # TODO: for corpay api, ask for an update! see existing code.
            # TODO: ask order_queue for update and update ticket state.
            # if we are waiting for a manual rfq, check if it's ready
            if hasattr(ticket, '_mreq'):
                mreq = ticket._mreq
                mreq.refresh_from_db()

                # TODO HACK FAKE FILL HERE
                if self.is_not_prod() and random_decision(0.01):
                    try:
                        fxpair = FxPair.get_pair(ticket.market_name)
                        data = get_recent_data( fxpair, ticket.value_date )
                        if data:
                            spot_rate = data[0]['bid'] if ticket.side == 'Sell' else data[0]['ask']
                            fwd_points = data[1]['bid'] if ticket.side == 'Sell' else data[1]['ask']
                            rate = spot_rate + fwd_points
                            mreq.ref_rate = spot_rate
                            mreq.fwd_points = fwd_points
                            mreq.booked_rate = mreq.booked_all_in_rate = rate
                            mreq.booked_amount = ticket.amount
                            mreq.booked_cntr_amount = ticket.amount * mreq.booked_rate
                            mreq.broker_id = str(uuid.uuid4())
                    except:
                        pass

            else:
                try:
                    mreq = ManualRequest.objects.get(pk=ticket.internal_quote_id)
                    ticket._mreq = mreq
                except:
                    ticket.error_message = 'problem with manual request'
                    ticket.change_internal_state( INTERNAL_STATES.FAILED )
                    self.rem_ticket( ticket )

            if mreq.booked_all_in_rate or mreq.broker_id:

                ticket.trade_details = mreq.export()

                if not ticket.broker_id:
                    ticket.broker_id = mreq.broker_id

                ticket.rate = mreq.booked_rate
                ticket.all_in_rate = mreq.booked_all_in_rate

                buy_currency = ticket.get_buy_currency()
                sell_currency = ticket.get_sell_currency()
                lock_side = ticket.get_lock_side()

                if lock_side.mnemonic == buy_currency.mnemonic:
                    pay_amount = mreq.booked_amount
                    cost_amount = mreq.booked_cntr_amount
                else:
                    pay_amount = mreq.booked_cntr_amount
                    cost_amount = mreq.booked_amount

                if ticket.side == 'Buy':
                    ticket.done = ticket.all_in_done = pay_amount
                    ticket.cntr_done = ticket.all_in_cntr_done = cost_amount
                else:
                    ticket.done = ticket.all_in_done = cost_amount
                    ticket.cntr_done = ticket.all_in_cntr_done = pay_amount

                # get the reference rate stuff
                if buy_currency.mnemonic == sell_currency.mnemonic:
                    rr = 1.0
                    fp = 0.0
                else:
                    spot_rate, fwd_points, ws_feed = get_recent_data( ticket.fxpair, ticket.tenor if ticket.tenor == Ticket.Tenors.SPOT else ticket.value_date )
                    rr = spot_rate['bid'] if ticket.side == 'Sell' else spot_rate['ask']
                    fp = fwd_points['bid'] if ticket.side == 'Sell' else fwd_points['ask']

                ticket.spot_rate = rr
                ticket.fwd_points = fp
                implied_fwd_rate = rr + ticket.fwd_points

                if ticket.side == 'Sell':
                    ticket.quote_fee = round( ((ticket.external_quote/implied_fwd_rate)-1.0), 5)
                else:
                    ticket.quote_fee = round( -((implied_fwd_rate/ticket.external_quote)-1.0), 5)

                ticket.fee = 0.0

                # ========================

                mreq.close()
                ticket.change_internal_state( INTERNAL_STATES.FILLED )
                self.rem_ticket( ticket )

            elif mreq.is_cancelled():
                mreq.close()
                ticket.change_internal_state( INTERNAL_STATES.CANCELED )
                self.rem_ticket( ticket )
            elif mreq.is_expired():
                # TODO: edit the slack alert/ack victor ops
                # potentially send a new alert?
                ticket.change_internal_state( INTERNAL_STATES.EXPIRED )
                self.rem_ticket( ticket )
            elif self.is_rfq_expired( ticket ): # expired
                mreq.close()
                ticket.change_internal_state( INTERNAL_STATES.EXPIRED )
                self.rem_ticket( ticket )
        elif self.is_rfq_expired( ticket ): # expired
            ticket.change_internal_state( INTERNAL_STATES.EXPIRED )
            self.rem_ticket( ticket )
        # elif ticket.do_fail

    def check_pend_rfq( self, ticket ):
        pass

    def check_error( self, ticket ):
        # handle corpay specific error stuff
        pass

# =============================================================================

if __name__ == "__main__":

    import os
    import atexit
    atexit.register(os._exit, 0)

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('--ems-id', default='CORPAY1' ) # settings.OMS_ID)
    parser.add_argument('--ems-typ', default='CORPAY')
    parser.add_argument('--log-level', default=None)
    parser.add_argument('--regen', action='store_true', default=False)

    args = parser.parse_args()

    # ==========================

    server = CorpayEms( args.ems_id, args.ems_typ, log_level=args.log_level, regen=args.regen )
    server.run()

