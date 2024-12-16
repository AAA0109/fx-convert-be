import traceback
import sys

from main.apps.oems.backend.date_utils import now, parse_datetime
from main.apps.oems.backend.states import INTERNAL_STATES, EXTERNAL_STATES, PHASES
from main.apps.oems.backend.db import init_db
from main.apps.oems.backend.ticket_shared import TicketBase
from main.apps.oems.models.ticket import Ticket as DjangoTicket

class Ticket(TicketBase):

    ROUND_FACTOR         = 10
    MODIFY_ORDER_FIELDS  = ['amount','algo','time_in_force','start_time','end_time','order_length','paused']
    MODIFY_SETTLE_FIELDS = []
    DJANGO_MODEL_NAME    = 'oems_ticket'
    SYNC_FLDS            = None
    DATETIME_FLDS        = { 'start_time','end_time','external_quote_expiry','internal_quote_expiry', 'trigger_time', 'funding_deadline', 'transaction_time' } # value_date, internal_state_start, external_state_start
    _db = None
    _next_update         = None

    def __init__( self, **kwargs ):
        self.ensure_db()
        self._dirty  = {}
        self._import(kwargs)

    # ========

    @classmethod
    def _create( cls, **kwargs ):
        from main.apps.oems.validators.ticket import shared_ticket_validation
        kwargs = shared_ticket_validation( kwargs )
        return cls(**kwargs)

    def _import( self, dct ):
        for k, v in dct.items():
            if k in self.DATETIME_FLDS and v:
                setattr(self, k, parse_datetime(v))
            else:
                setattr(self, k, v)
        self.mark_clean()

    def as_django_model( self ) -> DjangoTicket:
        return DjangoTicket.objects.get(pk=self.id)

    # ========

    def __setattr__( self, k, v ):
        # anytime a ticket attribute changes, mark that ticket is dirty
        if not k.startswith('_'):
            self._dirty[k] = v
        super().__setattr__(k, v)

    @classmethod
    def ensure_db( cls ):
        if not cls._db:
            cls._db = init_db()

    def mark_clean( self ):
        self._dirty.clear()

    def save( self, force=False ):

        if not self._dirty: return

        sql = self._db.update_sql( None, self.DJANGO_MODEL_NAME, self._dirty, 'id', self.id )

        # TODO: update a single log with all field changes here and do the same on model for sandbox

        try:
            self._db.execute_and_commit( sql )
        except:
            print(f'ERROR: sql failure - {sql}')
            traceback.print_exc(file=sys.stdout)
            return

        self.mark_clean()

    def refresh_from_db( self, sync_flds=SYNC_FLDS ):

        # sync fields with database
        sql = self._db.select_where( None, self.DJANGO_MODEL_NAME, columns=sync_flds, key='id', value=self.id )

        try:
            ret = self._db.fetch_and_commit( sql )[0]
        except:
            print(f'ERROR: sql failure - {sql}')
            traceback.print_exc(file=sys.stdout)
            return

        if ret:
            for k, v in ret.items():
                setattr(self, k, v)

        self.mark_clean()

    # =========================================================================

    def set_error( self, error_msg ):
        self.change_internal_state( INTERNAL_STATES.ERROR )
        self.error_message = error_msg

    # =========================================================================

    @classmethod
    def fetch(cls, id):
        cls.ensure_db()
        sql = cls._db.select_where( None, cls.DJANGO_MODEL_NAME, key='id', value=id )
        ret = cls._db.fetch_and_commit(sql)
        return cls(**ret[0])

