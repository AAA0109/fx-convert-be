
from main.apps.oems.backend.date_utils import now, add_time, check_after
from main.apps.oems.backend.rfq_mp_ems import RfqMpEms
from main.apps.currency.models         import Currency
from main.apps.oems.backend.states     import INTERNAL_STATES, ERRORS
from main.apps.oems.backend.enums      import RfqType
from main.apps.oems.backend.api        import pangea_client
from main.apps.oems.models.cny         import CnyExecution

# =============================================================================

class CorpayMpEms(RfqMpEms):

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        # self.register_ticket_dispatch( INTERNAL_STATES.PEND_RFQ, self.check_pend_rfq )

    def check_quote_refresh( self, ticket ):
        # TODO: make sure that new internal quote is not outside our external_quote otherwise we lose money
        # what do we do when that happens?
        pass

    def do_accept( self, ticket ):

        # TODO: do the shit to start the payment here with the corpay api
        # Put ticket on order_queue to corpay

        if ticket.rfq_type != CnyExecution.RfqTypes.API:
            ticket.error_message='ERROR: cannot use corpay mass-payments with non-api markets.'
            ticket.change_internal_state( INTERNAL_STATES.FAILED )
            return True

        quote_id = ticket.external_quote_id or ticket.internal_quote_id

        # print('accepting ticket', ticket.external_quote_id, ticket.internal_quote_id )

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
                if ticket.instrument_type == 'spot':
                    qid, sid = ticket.internal_quote_id.split('|')
                    data = pangea_client.corpay_mass_payments_rfq_execute( qid, sid, combine_settlements=True )
                elif ticket.instrument_type == 'fwd':
                    # TODO: could go to working and try again
                    ticket.error_message='ERROR: cannot use corpay mass-payments with forwards.'
                    ticket.change_internal_state( INTERNAL_STATES.FAILED )
                    return True
                else:
                    data = None

                # TODO if quote has expired, get a new quote or try again

                if data:
                    ticket.trade_details = data
                    ticket.done = ticket.amount
                    ticket.all_in_rate = ticket.external_quote
                    ticket.change_internal_state( INTERNAL_STATES.FILLED )
                    self.rem_ticket( ticket )
                    return False
                else:
                    # TODO: could go to working and try again
                    ticket.change_internal_state( INTERNAL_STATES.FAILED )
                    return True

            # if settlement information is filled out deal with it now
            # otherwise pass it back ??

            # TODO: setup settlement in another
            # print('deal with settlement now')
            # self.enqueue_oms( ticket, OMS_EMS_ACTIONS.UPDATE )
            # ticket.save()

        elif ticket.internal_quote_id:
            # check if internal_quote has expired?
            pass

        # change phase to settlement
        # instruct the deal

        return True

    def check_pend_rfq( self, ticket ):
        pass # for right now this is synchronous

    def check_working( self, ticket ):
        # ask broker for update
        # TODO: for corpay api, ask for an update! see existing code.
        # TODO: ask order_queue for update and update ticket state.
        pass

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

