
from main.apps.oems.backend.date_utils import now, add_time
from main.apps.oems.backend.ems        import EmsBase
from main.apps.oems.backend.states     import INTERNAL_STATES, ERRORS
from main.apps.oems.backend.enums      import EXEC_STATUS

# =============================================================================

class StratExEms(EmsBase):

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )

    # ==========================================

    def check_upper_trigger( self, mkt, value_date, px ):
        # TODO: get current price (need to add value date for non-spot pricing)
        cur_px = state['mid']
        return (cur_px >= px)

    def check_lower_trigger( self, mkt, value_date, px ):
        # TODO: get current price (need to add value date for non-spot pricing)
        cur_px = state['mid'] # THIS IS LEGACY
        return (cur_px <= px)

    def is_market_open( self, ticket ):
        # TODO: lookup if the market is open using holiday calendars
        return True

    def check_triggers(self, ticket):

        # TODO: fix trigger code to actually work

        if ticket.market_name:

            if ticket.upper_trigger:
                ret = self.check_limit( ticket.market_name, ticket.value_date, ticket.upper_trigger )
                if ret:
                    return True

            if ticket.lower_trigger:
                ret = self.check_stop( ticket.market_name, ticket.value_date, ticket.lower_trigger )
                if ret:
                    return True

        return False

    def is_ticket_ready( self, ticket, now ):
        return False
        # need a function to get order_configs (and presumably populate?)
        order_configs = get_order_configs( ticket )
        for order_config in order_configs:
            # TODO imports
            if isinstance(order_config, TimeOrderConfig) and order_config.time_threshold <= now:
                return True
            elif isinstance(order_config, PriceOrderConfig):
                return is_price_reach_threshold() # TODO: 
        return False

    def check_waiting( self, ticket ):

        if self.is_ticket_ready( ticket, now() ): # if its time to execute:
            # TODO: check for value_date cutover?
            ticket.execution_status = EXEC_STATUS.READY
            ticket.change_internal_state( INTERNAL_STATES.ACCEPTED )
            self.rem_ticket( ticket )
        return

        # TODO: this isn't needed
        if spread_model_passes:
            pass
        elif self.check_triggers( ticket ):
            ticket.execution_status = EXEC_STATUS.TRIGGERED
            ticket.change_internal_state( INTERNAL_STATES.ACCEPTED )
            self.rem_ticket( ticket )
        else:
            if self.is_market_open( ticket ):
                ticket.change_internal_state( INTERNAL_STATES.ACCEPTED )
                self.rem_ticket( ticket )
            else:
                pass # TODO: some indication of when the market will open in ticket.execution_status

    def check_error( self, ticket ):
        # handle strat_ex specific error stuff
        pass


