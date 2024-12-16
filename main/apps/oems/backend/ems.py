from datetime import datetime
import logging
import os
import signal
import time
from collections import deque
from typing import List

from django.conf import settings

from main.apps.oems.backend.date_utils import now, check_after
from main.apps.oems.backend.db import init_db
from main.apps.oems.backend.states import OMS_EMS_ACTIONS, INTERNAL_STATES, EXTERNAL_STATES, PHASES, ERRORS
from main.apps.oems.backend.ticket import Ticket
from main.apps.oems.backend.utils import sleep_for
from main.apps.oems.models.cny import CnyExecution
from main.apps.oems.models.manual_request import ManualRequest
from main.apps.oems.services.ndf_ticket_notif import NDFTicketNotif
from main.apps.payment.models.payment import Payment

ENV = settings.APP_ENVIRONMENT


class EmsBase:

    def __init__(self, ems_id, ems_typ, log_level=None, regen=False, queue_name='global1', batch_size=1, timeout=1.0,
                 child=False):

        # to avoid collisions
        ems_id = f'{ems_id}{ems_typ}'

        self.ems_id = ems_id
        self.ems_typ = ems_typ
        self.active = True  # this servers as a drain function. If you aren't active, you can't receive new tickets
        # NOTE: if you are not active and have no tickets in cache you can safely retire yourself
        self.tickets = {}
        self.remove_tickets = deque()
        self.saved = False

        # set the logger
        self._logger = logging.getLogger(__name__)
        if log_level: self._logger.setLevel(getattr(logging, log_level))

        # server state
        self._dirty = True
        self._kill_sig = False
        self._queue_table = queue_name
        self._batch_size = batch_size
        self._timeout = timeout
        self._db = init_db()
        self._oms_dispatch = {}
        self._ticket_dispatch = {}

        self._EMS_QUEUE_NAME = f'oms2ems_{ENV}_{ems_typ}'  # NOTE: this is: oms2ems_dev_CORPAY
        self._ems_queue_name = f'oms2ems_{ENV}_{ems_id}'  # NOTE: this is more specific: oms2ems_dev_CORPAY1

        # only one at a time. If you disconnect from the database, you must shutdown.
        success = self._db.acquire_lock(self.ems_id)  # nowait=True do we want to block forever?

        if not regen:
            self.load()

        # ensure schema + queues
        self.ensure_db()

        if not child:
            # shutdown signals
            signal.signal(signal.SIGINT, self.on_shutdown)
            signal.signal(signal.SIGTERM, self.on_shutdown)

    # =========================================================================

    NON_PROD_ENVS = {'dev', 'development', 'staging'}

    @classmethod
    def is_not_prod(cls):
        return (settings.APP_ENVIRONMENT in cls.NON_PROD_ENVS)

    # =========================================================================

    def mark_dirty(self):
        pass

    def export(self):
        return {k: v for k, v in vars(self).items() if not k.startswith('_')}

    def save(self, force=False):
        if not force and not self._dirty: return

    def add_ticket(self, ticket):
        self.tickets[ticket.id] = ticket

    def get_ticket(self, ticket_id):
        return self.tickets[ticket_id]

    def rem_ticket(self, ticket, action=OMS_EMS_ACTIONS.DONE):
        if ticket.ems_owner:  # prevents removing twice
            self.remove_tickets.append(ticket.id)
            ticket.ems_owner = None  # give it up
            ticket.save()
            self.enqueue_oms(ticket, action)

    def load(self):

        # states     = ','.join(map(self._db.pytype, INTERNAL_STATES.EMS_TERMINAL_STATES))
        sql = f"select * from \"{Ticket.DJANGO_MODEL_NAME}\" where \"ems_owner\" = '{self.ems_id}'"  # and \"internal_state\" not in ({states})"
        try:
            ret = self._db.fetch_and_commit(sql, one_call=False)
        except:
            print("SQL ERROR", sql)
            ret = []

        for row in ret:
            ticket = Ticket(**row)
            print('loading ems ticket', ticket.id, ticket.internal_state)
            self.add_ticket(ticket)
            self.replay(ticket)

    def register_oms_dispatch(self, action, fnc):
        if not callable(fnc): raise ValueError
        self._oms_dispatch[action] = fnc

    def register_ticket_dispatch(self, state, fnc):
        if not callable(fnc): raise ValueError
        self._ticket_dispatch[state] = fnc

    # =========================================================================

    def ensure_db(self):

        topics = [self._EMS_QUEUE_NAME, self._ems_queue_name]
        self._db.ensure_queue(topics, queue_table=self._queue_table)

        # TODO: ensure django model here!

    def enqueue_oms(self, ticket, action):
        topic = f'ems2oms_{ENV}_{ticket.oms_owner}'
        ticket.save()
        self.log("INFO", "ENQUEUE", topic, ticket.id, now().isoformat())
        ret = self._db.enqueue(topic, ticket.export(), action=action, source=self.ems_id, uid=ticket.id,
                               queue_table=self._queue_table)
        if isinstance(ret, int):
            ticket.last_message_id = ret

    def dequeue(self, topic, n=1):
        # pull n messages from topic
        return self._db.dequeue(topic, n=n, queue_table=self._queue_table)

    def del_queue(self, req):
        self._db.del_queue(req['id'], queue_table=self._queue_table)

    def resp_queue(self, req, resp):
        self._db.upd_queue(req['id'], resp, queue_table=self._queue_table)

    def replay(self, ticket):

        # replay ems queue
        event_queue = self._db.replay_queue(self._ems_queue_name, ticket.last_message_id, ticket.id)
        if event_queue:
            self.cycle_queue(self._ems_queue_name, event_queue=event_queue)

    def notify(self):
        pass

    # =========================================================================

    def on_shutdown(self, *args):
        self.clean_up()
        self.save()
        self._kill_sig = True

    def log(self, log_type, *args):

        msg = str(args)

        if log_type == 'INFO':
            self._logger.info(msg)
        elif log_type == 'WARN':
            self._logger.warning(msg)
        elif log_type == 'DEBUG':
            self._logger.debug(msg)
        elif log_type == 'ERROR':
            self._logger.error(msg)
        else:
            self._logger.debug(msg)

    # =========================================================================

    def clean_up(self):
        if self.remove_tickets:
            for key in self.remove_tickets:
                try:
                    del self.tickets[key]
                except KeyError:
                    pass
            self.remove_tickets.clear()
            self.mark_dirty()

    # =========================================================================

    def do_accept(self, ticket):
        raise NotImplementedError

    # =========================================================================

    def check_accepted(self, ticket):

        if self.do_accept(ticket):
            if ticket.internal_state in INTERNAL_STATES.EMS_TERMINAL_STATES:
                self.rem_ticket(ticket)
            elif ticket.internal_state == INTERNAL_STATES.PEND_RFQ:
                self.enqueue_oms(ticket, OMS_EMS_ACTIONS.UPDATE)
                ticket.save()
            else:
                ticket.change_internal_state(INTERNAL_STATES.WORKING)
                self.enqueue_oms(ticket, OMS_EMS_ACTIONS.UPDATE)
                ticket.save()
            self.mark_dirty()

    def check_working(self, ticket):

        if self.is_rfq_expired(ticket):  # expired
            ticket.change_internal_state(INTERNAL_STATES.EXPIRED)
            self.rem_ticket(ticket)

    def check_waiting(self, ticket):
        pass

    def check_error(self, ticket):
        pass

    # ======================

    def check_cancelled(self, ticket):
        self.rem_ticket(ticket)
        self.mark_dirty()

    def check_done(self, ticket):
        self.rem_ticket(ticket)
        self.mark_dirty()

    def check_failed(self, ticket):
        self.rem_ticket(ticket)
        self.mark_dirty()

    def check_expiry(self, ticket):
        # check for expiry
        if ticket.end_time and check_after(ticket.end_time):
            ticket.change_internal_state(INTERNAL_STATES.EXPIRED)
            self.rem_ticket(ticket)
            self.mark_dirty()
        return False

    # =========================================================================

    def cycle_queue(self, queue_name, event_queue=None):

        if event_queue is None:
            event_queue = self.dequeue(queue_name, n=self._batch_size)

        for req in event_queue:

            action = req['action']

            self.log("INFO", "OMS REQUEST:", req['uid'], req['action'], req['source'], now().isoformat())

            if action == OMS_EMS_ACTIONS.CREATE:
                # assume create has been validated and ticket exists in the database
                # load the ticket from the database
                self.create_ticket(req)
            elif action == OMS_EMS_ACTIONS.UPDATE:
                self.sync_ticket(req)
            elif action == OMS_EMS_ACTIONS.CANCEL:
                self.cancel_ticket(req)
            elif action in self._oms_dispatch:
                self._oms_dispatch[action](req)
            else:
                print(action, req)

            self.del_queue(req)

    def cycle_queues(self):
        self.cycle_queue(self._ems_queue_name)
        # new stuff queue - ignore if draining
        if self.active: self.cycle_queue(self._EMS_QUEUE_NAME)

    def check_pend_rfq(self, ticket:Ticket):
        if ticket.rfq_type == CnyExecution.RfqTypes.MANUAL:
            try:
                mreq = None
                mreqs:List[ManualRequest] = ManualRequest.objects.filter(
                    ticket_id=ticket.id,
                    status=ManualRequest.Status.PENDING
                ).order_by('-created')
                if len(mreqs) > 0:
                    mreq = mreqs[0]

                    permalink = mreq.upsert_manual_request_form_link()

                    if mreq.last_reminder_sent is None:
                        mreq.update_reminder_time()

                    ndf_notif_svc = NDFTicketNotif(ticket=ticket)
                    notif_message = ndf_notif_svc.get_text(permalink=permalink, manual_req=mreq)

                    if permalink and notif_message and settings.SLACK_NOTIFICATIONS_CHANNEL:
                        channel = settings.SLACK_NOTIFICATIONS_CHANNEL
                        mreq.send_reminder_msg(notif_message, None, channel=channel)
                        mreq.update_reminder_time()
            except Exception as e:
                logging.exception(e, exc_info=True)

    def cycle_ticket(self, ticket):

        state = ticket.internal_state

        if self.check_expiry(ticket):
            return

        if state == INTERNAL_STATES.ACCEPTED:
            self.check_accepted(ticket)
        elif state in INTERNAL_STATES.WORKING_STATES:
            self.check_working(ticket)
        elif state == INTERNAL_STATES.WAITING:
            self.check_waiting(ticket)
        elif state == INTERNAL_STATES.CANCELED:
            self.check_cancelled(ticket)
        elif state == INTERNAL_STATES.ERROR:
            self.check_error(ticket)
        elif state == INTERNAL_STATES.FAILED:
            self.check_failed(ticket)
        elif state == INTERNAL_STATES.DONE:
            self.check_done(ticket)
        elif state == INTERNAL_STATES.EXPIRED:
            self.check_done(ticket)
        elif state == INTERNAL_STATES.PEND_RFQ:
            self.check_pend_rfq(ticket)
        elif state == INTERNAL_STATES.RFQ_DONE:
            self.check_working(ticket)
        elif state in self._ticket_dispatch:
            self._ticket_dispatch[state](ticket)

    def cycle_tickets(self):

        curtime = now()

        for ticket in self.tickets.values():
            try:
                if curtime < ticket._next_update:
                    continue
            except:
                pass
            self.cycle_ticket(ticket)

        self.clean_up()
        self.save()

    def cycle(self):
        self.cycle_queues()
        self.cycle_tickets()

    # ==========================================================================

    def create_ticket(self, ticket_req, cycle=True):
        ticket = Ticket(**ticket_req['data'])
        if ticket.ems_owner:
            self.log('WARN:', 'ticket already has an ems owner')
        ticket.ems_owner = self.ems_id
        ticket.last_message_id = ticket_req['id'] + 1
        ticket.save()
        self.enqueue_oms(ticket, OMS_EMS_ACTIONS.ACCEPT)
        self.add_ticket(ticket)
        if cycle: self.cycle_ticket(ticket)

    def sync_ticket(self, ticket_req):

        ticket_id = ticket_req['data']['id']

        try:
            ticket = self.get_ticket(ticket_id)
        except:
            return

        ticket.sync(self._db)
        ticket.last_message_id = ticket_req['id'] + 1
        ticket.save()

    def cancel_ticket(self, ticket_req):

        ticket_id = ticket_req['data']['id']

        try:
            ticket = self.get_ticket(ticket_id)
        except:
            return

        ticket.sync(self._db)
        ticket.last_message_id = ticket_req['id'] + 1

        if ticket.internal_state in INTERNAL_STATES.CANCELLABLE_STATES:
            ticket.change_internal_state(INTERNAL_STATES.CANCELED)
            ticket.change_external_state(EXTERNAL_STATES.CANCELED)
            self.rem_ticket(ticket, action=OMS_EMS_ACTIONS.CANCEL)
        else:
            print('CANCEL REJECT:', ticket.id, ticket.external_state, ticket.internal_state)
            ticket.change_external_state(EXTERNAL_STATES.ACTIVE)
            ticket.save()
            self.enqueue_oms(ticket, OMS_EMS_ACTIONS.CANCELREJECT)

    # ==========================================================================

    def run(self):

        try:
            while not self._kill_sig:
                self.cycle()
                if isinstance(self._timeout, float): sleep_for(self._timeout)
        except KeyboardInterrupt:
            pass

        return 0

    # =========================================================================
