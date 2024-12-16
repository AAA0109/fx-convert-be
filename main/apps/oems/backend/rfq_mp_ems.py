
from main.apps.oems.backend.rfq_ems    import RfqEms
from main.apps.oems.backend.api        import pangea_client
from main.apps.oems.models.cny         import CnyExecution

# ==================

class RfqMpEms(RfqEms):

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.exec_broker = 'CORPAY_MP'
        self.clearing_broker = 'CORPAY_MP'

    def do_rfq( self, ticket, internal_only=False ):

        if ticket.rfq_type != CnyExecution.RfqTypes.API:
            ticket.error_message='ERROR: cannot use corpay mass-payments with non-api markets.'
            ticket.change_internal_state( INTERNAL_STATES.FAILED )
            return True

        ticket.quote_type = rfq_type
        return self.api_rfq( ticket )

    def check_pend_rfq( self, ticket ):
        pass # for right now this is synchronous

        