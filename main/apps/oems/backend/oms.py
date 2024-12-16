import logging
import os
import signal
import traceback
from collections import deque
from datetime import datetime, timedelta

from django.conf import settings
from main.apps.broker.models.constants import BrokerProviderOption

from main.apps.core.utils.slack import send_exception_to_slack
from main.apps.currency.models.fxpair import FxPair
from main.apps.marketdata.services.initial_marketdata import get_recent_data
from main.apps.oems.backend.date_utils import now, check_after
from main.apps.oems.backend.db import init_db
from main.apps.oems.backend.rfq_utils import do_api_complete, do_api_settle, do_api_tts
from main.apps.oems.backend.states import OMS_EMS_ACTIONS, OMS_API_ACTIONS, INTERNAL_STATES, EXTERNAL_STATES, PHASES, \
    ERRORS
from main.apps.oems.backend.ticket import Ticket
from main.apps.oems.backend.utils import sleep_for
from main.apps.oems.models.ticket import Ticket as DjangoTicket
from main.apps.oems.validators.ticket import evaluate_best_ex, evaluate_smart_ex

# ==============================================

ENV = settings.APP_ENVIRONMENT


# ==============================================

class OmsBase:

    def __init__(self, oms_id, oms_typ, log_level=None, regen=False, queue_name='global1', batch_size=1, timeout=1.0,
                 child=False):

        # to avoid collisions
        oms_id = f'{oms_id}{oms_typ}'

        self.oms_id = oms_id
        self.oms_typ = oms_typ
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
        self.API_QUEUE_NAME = f'api2oms_{ENV}'
        self._ems_queue_name = f'ems2oms_{ENV}_{oms_id}'
        self._api_queue_name = f'api2oms_{ENV}_{oms_id}'

        # only one at a time. If you disconnect from the database, you must shutdown.
        success = self._db.acquire_lock(self.oms_id)  # nowait=True do we want to block forever?

        if not regen:
            self.load()

        # ensure schema + queues
        self.ensure_db()

        if not child:
            # shutdown signals
            signal.signal(signal.SIGINT, self.on_shutdown)
            signal.signal(signal.SIGTERM, self.on_shutdown)

        self.MAX_SETTLEMENT_RETRY_ATTEMPT = 3

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

    def rem_ticket(self, ticket):
        if ticket.oms_owner:  # prevents removing twice
            self.log('INFO', 'removing ticket id', ticket.id)
            self.remove_tickets.append(ticket.id)
            ticket.change_external_state(
                EXTERNAL_STATES.FAILED if ticket.internal_state == INTERNAL_STATES.FAILED else EXTERNAL_STATES.DONE)
            ticket.oms_owner = None  # give it up
            ticket.save()

    def load(self):

        # states     = ','.join(map(self._db.pytype, INTERNAL_STATES.OMS_TERMINAL_STATES))
        sql = f"select * from \"{Ticket.DJANGO_MODEL_NAME}\" where \"oms_owner\" = '{self.oms_id}'"  # and \"internal_state\" not in ({states})"

        try:
            ret = self._db.fetch_and_commit(sql, one_call=False)
        except:
            print("SQL ERROR", sql)
            ret = []

        for row in ret:
            ticket = Ticket(**row)
            # TODO: refactor how replay works and do it on a per-ticket basis pulling relevant events from queues
            self.add_ticket(ticket)
            self.log('INFO', 'loading ticket', ticket.id, ticket.internal_state)
            self.replay(ticket)

    def schedule_update(self, ticket, next_update=None, **kwargs):
        # hidden field to control how often we are cycling

        ticket._next_update = next_update or (now() + timedelta(**kwargs))

    # =========================================================================

    def ensure_db(self):

        topics = [self.API_QUEUE_NAME, self._ems_queue_name, self._api_queue_name]
        self._db.ensure_queue(topics, queue_table=self._queue_table)

        # TODO: ensure django model here!

    def enqueue_ems(self, ticket, action, topic=None):
        if not topic:
            if ticket.ems_owner:
                topic = 'oms2ems_{ENV}_{ticket.ems_owner}'
            else:
                # TODO: route via Dest. Lookup Corpay, NIUM, etc.
                dest = ticket.destination  # todo could do .lower()
                if not dest: return False
                topic = f'oms2ems_{ENV}_{dest}'
        self.log("INFO", "ENQUEUE", topic, now().isoformat())
        ticket.save()
        ret = self._db.enqueue(topic, ticket.export(), action=action, source=self.oms_id, uid=ticket.id,
                               queue_table=self._queue_table)
        if isinstance(ret, int):
            ticket.last_message_id = ret
        return True

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
            self.cycle_internal_queue(self._ems_queue_name, event_queue=event_queue)

        # replay api queue
        event_queue = self._db.replay_queue(self._api_queue_name, ticket.last_message_id, ticket.id)
        if event_queue:
            self.cycle_api_queue(self._api_queue_name, event_queue=event_queue)

    def notify(self):
        pass

    # =========================================================================

    def on_shutdown(self, *args):
        self.clean_up()
        self.save()
        self._kill_sig = True

    def log(self, log_type, *args):

        msg = ' '.join(map(str, args))

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

    def check_new(self, ticket):

        if ticket.paused: return

        # assume validation is already done
        ticket.change_internal_state(INTERNAL_STATES.PENDAUTH)
        self.cycle_ticket(ticket)
        ticket.save()
        self.mark_dirty()

    def check_for_auth(self, ticket):

        if ticket.paused: return

        # TODO: make a call that checks if ticket.trade is authorized else wait for authorization
        # This should be an api endpoint.

        is_authed = (ticket.action == DjangoTicket.Actions.RFQ) or ticket.auth_user

        if is_authed:

            if ticket.action == DjangoTicket.Actions.RFQ:
                ticket.change_internal_state(INTERNAL_STATES.SCHEDULED)
            elif ticket.funding == DjangoTicket.FundingModel.PREMARGINED:
                ticket.change_internal_state(INTERNAL_STATES.PENDMARGIN)
            else:  # prefunded ??
                ticket.change_internal_state(INTERNAL_STATES.SCHEDULED)

            self.cycle_ticket(ticket)
            ticket.save()
            self.mark_dirty()

    def check_for_margin(self, ticket):

        if ticket.paused: return

        # make an external call to check if trade has sufficient margin
        # NOTE: this may or may not be relevant for payments

        is_funded = (ticket.action == DjangoTicket.Actions.RFQ) or True  # can make a call here

        if is_funded:
            ticket.change_internal_state(INTERNAL_STATES.SCHEDULED)
            self.cycle_ticket(ticket)
            ticket.save()
            self.mark_dirty()

    def check_for_funds(self, ticket):
        pass

    def check_scheduled(self, ticket):

        if ticket.paused: return

        # check for queue release
        if not ticket.start_time or check_after(ticket.start_time):
            ticket.change_internal_state(INTERNAL_STATES.WAITING)
            self.cycle_ticket(ticket)
            ticket.save()
            self.mark_dirty()
        else:
            self.schedule_update(ticket, next_update=ticket.start_time, minutes=1)

    # ================================================

    def check_upper_trigger(self, mkt, px, cur_px):
        # TODO: get current price (need to add value date for non-spot pricing)
        return (cur_px >= px)

    def check_lower_trigger(self, mkt, px, cur_px):
        # TODO: get current price (need to add value date for non-spot pricing)
        return (cur_px <= px)

    def check_limit_trigger(self, mkt, side, px, cur_px):
        if side == 'Buy':
            return (cur_px <= px)
        else:
            return (cur_px >= px)

    def check_stop_trigger(self, mkt, side, px, cur_px):
        if side == 'Buy':
            return (cur_px >= px)
        else:
            return (cur_px <= px)

    def is_market_open(self, ticket):
        # TODO
        return True

    def check_triggers(self, ticket):

        """
        LimitTrigger and StopTrigger always force and execution to begin.
        For a Buy Order, the LimitTrigger is the price below the market where
        we want to enter, and the StopTrigger is the price above the market where
        we would like to enter.
        """

        # TODO: fix trigger code to actually work

        # Converting trigger time to be naive, so check_after can compare
        if ticket.trigger_time and check_after(ticket.trigger_time.replace(tzinfo=None)):
            return True

        if ticket.market_name:

            if all(getattr(ticket, fld) is None for fld in
                   ('upper_trigger', 'lower_trigger', 'limit_trigger', 'stop_trigger')):
                return False

            try:
                fxpair = FxPair.get_pair(ticket.market_name)
                spot_rate, fwd_points, ws_feed = get_recent_data(fxpair, ticket.value_date)
                cur_px = spot_rate['bid'] + fwd_points['bid'] if ticket.side == 'Sell' else spot_rate['ask'] + \
                                                                                            fwd_points['ask']
            except Exception as e:
                cur_px = None
                send_exception_to_slack(e, key='oems-execute')

            if not isinstance(cur_px, float):
                return False

            if ticket.upper_trigger:

                ret = self.check_upper_trigger(ticket.market_name, ticket.upper_trigger, cur_px)
                if ret:
                    return True
            if ticket.lower_trigger:
                ret = self.check_lower_trigger(ticket.market_name, ticket.lower_trigger, cur_px)
                if ret:
                    return True

            if ticket.limit_trigger:
                ret = self.check_limit_trigger(ticket.market_name, ticket.side, ticket.limit_trigger, cur_px)
                if ret:
                    return True

            if ticket.stop_trigger:
                ret = self.check_stop_trigger(ticket.market_name, ticket.side, ticket.stop_trigger, cur_px)
                if ret:
                    return True

        return False

    def check_exec_strategy(self, ticket):
        # just do it for now
        return True

    # =========================================================================

    def check_waiting(self, ticket):

        if ticket.paused: return

        if ticket.execution_strategy == DjangoTicket.ExecutionStrategies.BESTX:
            evaluate_best_ex(ticket)
        elif ticket.execution_strategy == DjangoTicket.ExecutionStrategies.SMART:
            check = evaluate_smart_ex(ticket)
            # check could be a flag to return if you want... better to use fields though
            # so you get trigger checks for free...

        if ticket.execution_strategy in (DjangoTicket.ExecutionStrategies.LIMIT, DjangoTicket.ExecutionStrategies.STOP,
                                         DjangoTicket.ExecutionStrategies.TRIGGER):
            if self.check_triggers(ticket):
                ticket.change_internal_state(INTERNAL_STATES.ACCEPTED)
                self.cycle_ticket(ticket)
                ticket.save()
                self.mark_dirty()
            else:
                self.schedule_update(ticket, minutes=1)
        elif ticket.execution_strategy == DjangoTicket.ExecutionStrategies.MARKET:
            if self.is_market_open(ticket):
                ticket.change_internal_state(INTERNAL_STATES.ACCEPTED)
                self.cycle_ticket(ticket)
                ticket.save()
                self.mark_dirty()
            else:
                self.schedule_update(ticket, minutes=1)
        elif ticket.execution_strategy:
            if not ticket.execution_status:
                # send to execution strategy ems
                ticket.execution_status = 'PENDING'
                ticket.save()
                topic = f'oms2ems_{ENV}_{ticket.execution_strategy}'
                self.enqueue_ems(ticket, OMS_EMS_ACTIONS.CREATE, topic=topic)
        else:
            ticket.change_internal_state(INTERNAL_STATES.ACCEPTED)
            self.cycle_ticket(ticket)
            ticket.save()
            self.mark_dirty()

    def check_accepted(self, ticket):

        # TODO: somewhere needs to decide where to send stuff (global ems queue, local ems queue)

        # only send to the EMS once... could be dangerous for retry purposes
        if ticket.paused or ticket.phase == PHASES.WORKING: return

        # there could be a dead-letter situation where an EMS needs to accept it
        # ticket.change_external_state( EXTERNAL_STATES. )
        if self.enqueue_ems(ticket, OMS_EMS_ACTIONS.CREATE):
            ticket.change_phase(PHASES.WORKING)
            ticket.save()
            self.mark_dirty()
        else:
            ticket.set_error(ERRORS.NO_DESTINATION)
            ticket.save()
            self.mark_dirty()

    # =====================
    # the ticket is underway... you can't really modify or cancel except settlement information

    def check_filled(self, ticket):

        # send email confirmation

        try:

            ticket.send_confirm()
        except Exception as e:
            self._logger.exception(e)

        # TODO: could pass back to the settlement ems to handle instructions
        ticket.change_phase(PHASES.SETTLE)
        ticket.change_external_state(EXTERNAL_STATES.DONE)

        if ticket.beneficiaries:
            if not do_api_complete(ticket):
                ticket.change_internal_state(INTERNAL_STATES.BOOKING_FAILURE)
            else:
                ticket.change_internal_state(INTERNAL_STATES.PENDSETTLE)
        else:
            ticket.change_internal_state(INTERNAL_STATES.PENDBENE)

        ticket.save()

        self.mark_dirty()

    def check_settlement(self, ticket):

        # ======================

        # could go into PENDFUNDS if we are POSTFUNDING

        if ticket.internal_state == INTERNAL_STATES.PENDBENE and ticket.beneficiaries:
            if not do_api_complete(ticket):
                send_exception_to_slack(f'{ticket.ticket_id} failed to complete', key='oems-complete')
                ticket.change_internal_state(INTERNAL_STATES.BOOKING_FAILURE)
            else:
                ticket.change_internal_state(INTERNAL_STATES.PENDSETTLE)
            ticket.save()

        if ticket.internal_state == INTERNAL_STATES.PENDSETTLE:
            if ticket.instrument_type == DjangoTicket.InstrumentTypes.NDF and \
                do_api_tts(ticket=ticket):
                ticket.change_phase(PHASES.SETTLE)
                ticket.change_internal_state(INTERNAL_STATES.DONE_PENDSETTLE)
                ticket.save()
            elif ticket.instrument_type == DjangoTicket.InstrumentTypes.FWD and \
                ticket.broker == BrokerProviderOption.MONEX and do_api_tts(ticket=ticket):
                ticket.change_phase(PHASES.SETTLE)
                ticket.change_internal_state(INTERNAL_STATES.DONE_PENDSETTLE)
                ticket.save()
            elif do_api_tts(ticket):  # time to settle
                if not do_api_settle(ticket):
                    send_exception_to_slack(f'{ticket.ticket_id} failed to settle', key='oems-settle')
                    ticket.change_internal_state(INTERNAL_STATES.SETTLE_FAIL)
                else:
                    ticket.change_phase(PHASES.RECON)
                    ticket.change_internal_state(INTERNAL_STATES.PENDRECON)
                ticket.save()
            else:
                self.schedule_update(ticket, minutes=60)

            # do the import above
            # from main.apps.oems.backend.rfq_utils import do_api_complete, do_api_settle
            # if spot... complete + settle: do_api_complete(ticket); do_api_settle(ticket);
            # if fwd... complete... do_api_complete(ticket);
            # if post-fundings. put in pendfunds state

        # if you are a FWD_TO_SPOT or NDF_TO_SPOT create the new linked ticket here
        # use BESTX for this ticket.

        # ======================

        # clean up
        if hasattr(ticket, '_cleanup_date'):
            cleanup_dt = ticket._cleanup_date
        else:
            cleanup_dt = datetime.combine(ticket.value_date + timedelta(days=7), datetime.min.time())
            ticket._cleanup_date = cleanup_dt

        if check_after(cleanup_dt):
            ticket.change_internal_state(INTERNAL_STATES.DONE_PENDSETTLE)
            self.rem_ticket(ticket)
            return

    def check_pendcancel(self, ticket):
        # ask EMS if cancelled
        pass

    def check_working(self, ticket):
        # ask EMS if we are done
        pass

    def check_paused(self, ticket):
        # if state is a pausable state, set state to paused
        pass

    def check_resumed(self, ticket):
        # if state is a resumable state, set state to resumed
        pass

    def check_error(self, ticket):
        pass

    # =========================================================================

    def check_cancelled(self, ticket):
        self.rem_ticket(ticket)
        self.mark_dirty()

    def check_failed(self, ticket):
        self.rem_ticket(ticket)
        self.mark_dirty()

    def check_done(self, ticket):
        if ( ticket.instrument_type == DjangoTicket.InstrumentTypes.NDF ) or \
            ( ticket.instrument_type == DjangoTicket.InstrumentTypes.FWD and \
             ticket.broker == BrokerProviderOption.MONEX ):
            if ticket.internal_state == INTERNAL_STATES.DONE_PENDSETTLE:
                settle_complete_date = ticket.value_date + timedelta(days=2)
                now_date = datetime.now().date()

                # auto complete ticket on settlement date + 2 days
                if now_date >= settle_complete_date:
                    self.rem_ticket(ticket)
                    self.mark_dirty()
        else:
            self.rem_ticket(ticket)
            self.mark_dirty()

    def check_rfq_done(self, ticket):
        self.rem_ticket(ticket)
        self.mark_dirty()

    def check_recon(self, ticket):

        # TODO: recon ticket here

        # clean up
        if hasattr(ticket, '_cleanup_date'):
            cleanup_dt = ticket._cleanup_date
        else:
            cleanup_dt = datetime.combine(ticket.value_date, datetime.min.time()) + timedelta(hours=18)
            ticket._cleanup_date = cleanup_dt

        if check_after(cleanup_dt):
            ticket.change_internal_state(INTERNAL_STATES.DONE)
            self.rem_ticket(ticket)
            return

        self.schedule_update(ticket, minutes=17)

    # =========================================================================

    def check_expiry(self, ticket):
        # check for expiry
        if ticket.phase in PHASES.TRADING and not ticket.ems_owner and ticket.end_time and check_after(
            ticket.end_time):
            self.cancel_ticket(None, ticket=ticket)
            return True
        return False

    # =========================================================================

    def check_failed_settle(self, ticket:Ticket):
        settlement_attempt = ticket.settlement_attempt
        if settlement_attempt is None:
            settlement_attempt = 0

        if settlement_attempt < self.MAX_SETTLEMENT_RETRY_ATTEMPT:
            self.schedule_update(ticket, minutes=(settlement_attempt + 1) * 5)
            self.retry_failed_settle_ticket(ticket=ticket)

    # =========================================================================

    def create_async_api_response(self):
        # reference the request id and place the response somewhere that can be polled
        return {'source': self.oms_id, 'success': None, 'error': None}

    # =========================================================================

    def cycle_api_queue(self, queue_name, event_queue=None):

        # read from the api request queue where dequeue time is None
        # in order to ignore new requests, if not self.active: filter out actions CREATE
        if event_queue is None:
            event_queue = self.dequeue(queue_name, n=self._batch_size)

        for req in event_queue:

            self.log("INFO", "API REQUEST:", req['uid'], req['action'], req['source'], now().isoformat())

            action = req['action']

            if action == OMS_API_ACTIONS.CREATE:
                # assume create has been validated and ticket exists in the database
                # load the ticket from the database
                # in the case of an RFQ_DONE ticket, it will be re-added to an OMS
                resp = self.create_ticket(req)
                # no response necessary because creating a ticket can be synchronous
            elif action == OMS_API_ACTIONS.EXECUTE_RFQ:
                resp = self.execute_rfq_ticket(req)
            elif action == OMS_API_ACTIONS.MODIFY:
                # load the ticket from the database
                # apply the modifications
                resp = self.modify_ticket(req)
                # create async api response here
                pass
            elif action == OMS_API_ACTIONS.CANCEL:
                # load the ticket from the database
                # cancel the ticket
                resp = self.cancel_ticket(req)
                # create async api response here
            elif action == OMS_API_ACTIONS.PAUSE:
                resp = self.pause_ticket(req)
            elif action == OMS_API_ACTIONS.RESUME:
                resp = self.resume_ticket(req)
            elif action == OMS_API_ACTIONS.ACTIVATE:
                resp = self.activate_ticket(req)
            elif action == OMS_API_ACTIONS.DBSYNC:
                resp = self.sync_ticket(req)
            elif action == OMS_API_ACTIONS.DELETE:
                # forceable internal action
                resp = self.delete_ticket(req)
            elif action == OMS_API_ACTIONS.AUTHORIZE:
                resp = self.authorize_ticket(req)
            elif action == 'SHUTDOWN':  # TODO HACK
                self._kill_sig = True

            # put the response back into the queue!
            if resp:
                self.resp_queue(req, resp)
            else:
                self.del_queue(req)

    def cycle_internal_queue(self, queue_name, event_queue=None):

        # read from the internal api request queue where dequeue time is None
        if event_queue is None:
            event_queue = self.dequeue(queue_name, n=self._batch_size)

        for req in event_queue:

            action = req['action']

            self.log("INFO", "EMS REQUEST:", req['uid'], req['action'], req['source'], now().isoformat())

            if action == OMS_EMS_ACTIONS.UPDATE:

                # sync the ticket with the EMS

                try:
                    ticket = self.get_ticket(req['data']['id'])
                except KeyError:
                    self.log("ERROR", "ticket id missing", req)
                    continue

                ticket.refresh_from_db()

            elif action == OMS_EMS_ACTIONS.ACCEPT:

                try:
                    ticket = self.get_ticket(req['data']['id'])
                except KeyError:
                    self.log("ERROR", "ticket id missing", req)
                    continue

                ticket.refresh_from_db()

            elif action == OMS_EMS_ACTIONS.DONE:

                # push onwards to next phase
                # from EMS to SETTLEMENT
                # from SETTLEMENT to RECON
                try:
                    ticket = self.get_ticket(req['data']['id'])
                except KeyError:
                    self.log("ERROR", "ticket id missing", req)
                    continue

                ticket.refresh_from_db()

            elif action == OMS_EMS_ACTIONS.CANCEL:

                try:
                    ticket = self.get_ticket(req['data']['id'])
                except KeyError:
                    self.log("ERROR", "ticket id missing", req)
                    continue

                ticket.refresh_from_db()

            elif action == OMS_EMS_ACTIONS.CANCELREJECT:

                try:
                    ticket = self.get_ticket(req['data']['id'])
                except KeyError:
                    self.log("ERROR", "ticket id missing", req)
                    continue

                ticket.refresh_from_db()

            # In theory, there could be ACCEPT and CANCELED explicitly but not necessary right now
            else:

                self.log('WARN', f'unknown action: {action} ', req)

            self.del_queue(req)
            # if we separate the EMS from the Settlement EMS (SMS)
            # there should really be a req['action'] == 'EMS_DONE'
            # that passes the EmsOwner back to the next part of the queue
            # this will work the same for the reconciliation part of the process
            # could use PENDSETTLE and PENDRECON for this

    def cycle_queues(self):
        # TODO: these will need try..catch to prevent a bad egg from messing up the OMS
        # inbox stuff from ems
        self.cycle_internal_queue(self._ems_queue_name)
        # inbox stuff from api
        self.cycle_api_queue(self._api_queue_name)
        # new stuff queue - ignore if draining
        if self.active: self.cycle_api_queue(self.API_QUEUE_NAME)

    def cycle_ticket(self, ticket):

        state = ticket.internal_state

        # ticket has expired
        if state in INTERNAL_STATES.CANCELLABLE_STATES and self.check_expiry(ticket):
            return
        elif state == INTERNAL_STATES.NEW:
            self.check_new(ticket)
        elif state == INTERNAL_STATES.PENDAUTH:
            self.check_for_auth(ticket)
        elif state == INTERNAL_STATES.PENDMARGIN:
            self.check_for_margin(ticket)
        elif state == INTERNAL_STATES.PENDFUNDS:
            self.check_for_funds(ticket)
        elif state == INTERNAL_STATES.SCHEDULED:
            self.check_scheduled(ticket)
        elif state == INTERNAL_STATES.PENDPAUSE:
            self.check_paused(ticket)
        elif state == INTERNAL_STATES.PENDRESUME:
            self.check_resumed(ticket)
        elif state == INTERNAL_STATES.WAITING:
            self.check_waiting(ticket)
        elif state == INTERNAL_STATES.ACCEPTED:
            self.check_accepted(ticket)
        elif state == INTERNAL_STATES.PENDCANCEL:
            self.check_pendcancel(ticket)
        elif state == INTERNAL_STATES.CANCELED:
            self.check_cancelled(ticket)
        elif state in INTERNAL_STATES.SETTLEMENT_STATES:
            self.check_filled(ticket)
        elif state in INTERNAL_STATES.PENDSETTLE_STATES:
            self.check_settlement(ticket)
        elif state == INTERNAL_STATES.SETTLE_FAIL:
            self.check_failed_settle(ticket=ticket)
        elif state in INTERNAL_STATES.WORKING_STATES:
            self.check_working(ticket)
        elif state == INTERNAL_STATES.ERROR:
            self.check_error(ticket)
        elif state == INTERNAL_STATES.FAILED:
            self.check_failed(ticket)
        elif state == INTERNAL_STATES.DONE:
            self.check_done(ticket)
        elif state == INTERNAL_STATES.EXPIRED:
            self.check_done(ticket)
        elif state == INTERNAL_STATES.DONE_PENDSETTLE:
            self.check_done(ticket)
        elif state == INTERNAL_STATES.RFQ_DONE:
            self.check_rfq_done(ticket)
        elif state == INTERNAL_STATES.PENDRECON:
            self.check_recon(ticket)
        elif state == INTERNAL_STATES.DRAFT:
            pass  # should never get here

    def cycle_tickets(self):

        curtime = now()

        for ticket in self.tickets.values():
            try:
                if ticket._next_update and curtime < ticket._next_update:
                    continue
            except Exception as e:
                pass
            try:
                self.cycle_ticket(ticket)
            except Exception as e:
                self._logger.error(f"Cycling ticket {ticket.ticket_id} id")
                self._logger.exception(e)

        self.clean_up()
        self.save()

    def cycle(self):
        self.cycle_queues()
        self.cycle_tickets()

    # ==========================================================================
    # these are requests from the external api queue

    def execute_rfq_ticket(self, ticket_req, cycle=True):

        # resp   = self.create_async_api_response()
        ticket = Ticket(**ticket_req['data'])
        if ticket.oms_owner:
            self.log('WARN', 'ticket already has an oms owner', ticket.oms_owner)
        ticket.change_internal_state(INTERNAL_STATES.ACCEPTED)
        ticket.change_external_state(EXTERNAL_STATES.ACTIVE)
        ticket.change_phase(PHASES.PRETRADE)
        ticket.last_message_id = ticket_req['id'] + 1
        ticket.oms_owner = self.oms_id
        ticket.save()
        self.add_ticket(ticket)
        if cycle: self.cycle_ticket(ticket)

    def activate_ticket(self, ticket_req):

        ticket_id = ticket_req['data']['id']

        resp = self.create_async_api_response()

        try:
            ticket = self.get_ticket(ticket_id)
        except:
            resp['error'] = f'id not found: {ticket_id}'
            return resp

        ticket.last_message_id = ticket_req['id'] + 1

        if ticket.internal_state == INTERNAL_STATES.DRAFT:
            # TODO: validate that we can do this
            ticket.change_internal_state(INTERNAL_STATES.NEW)
            ticket.change_external_state(EXTERNAL_STATES.ACTIVE)
            # ticket.change_phase( PHASES.PRETRADE )
            ticket.save()
            resp['success'] = True
        else:
            resp['error'] = f'Ticket already active'

        return resp

    def sync_ticket(self, ticket_req):

        ticket_id = ticket_req['data']['id']

        try:
            ticket = self.get_ticket(ticket_id)
        except:
            return

        ticket.refresh_from_db()
        ticket.last_message_id = ticket_req['id'] + 1
        ticket.save()

    def pause_ticket(self, ticket_req):

        ticket_id = ticket_req['data']['id']

        resp = self.create_async_api_response()

        try:
            ticket = self.get_ticket(ticket_id)
        except:
            resp['error'] = f'id not found: {ticket_id}'
            return resp

        ticket.last_message_id = ticket_req['id'] + 1

        if not ticket.paused:
            # TODO: validate that we can do this
            if ticket.internal_state in INTERNAL_STATES.PAUSEABLE_STATES:
                ticket.paused = True
                ticket.change_external_state(EXTERNAL_STATES.PAUSED)
                ticket.save()
                resp['success'] = True
            else:
                resp['error'] = f'Too late to pause ticket: {ticket_id}'
        else:
            resp['error'] = f'Ticket already paused: {ticket_id}'

        return resp

    def resume_ticket(self, ticket_req):

        ticket_id = ticket_req['data']['id']

        resp = self.create_async_api_response()

        try:
            ticket = self.get_ticket(ticket_id)
        except:
            resp['error'] = f'id not found: {ticket_id}'
            return resp

        ticket.last_message_id = ticket_req['id'] + 1

        if ticket.paused:
            # TODO: validate that we can do this
            ticket.paused = False
            ticket.change_external_state(EXTERNAL_STATES.ACTIVE)
            ticket.save()
            resp['success'] = True
        else:
            resp['error'] = f'Ticket already active: {ticket_id}'

        return resp

    def authorize_ticket(self, ticket_req, cycle=True):
        # need user
        # if EMS owner, send cancel to ems queue and change state to PENDCANCEL
        ticket_id = ticket_req['data']['id']
        resp = self.create_async_api_response()

        try:
            ticket = self.get_ticket(ticket_id)
        except:
            resp['error'] = f'id not found: {ticket_id}'
            return resp

        ticket.last_message_id = ticket_req['id'] + 1

        if ticket.internal_state in INTERNAL_STATES.PENDAUTH:
            ticket.auth_user = ticket_req['data']['auth_user']
            ticket.auth_time = now()
            ticket.change_internal_state(INTERNAL_STATES.PENDFUNDS)
            if cycle: self.cycle_ticket(ticket)
            ticket.save()
            self.mark_dirty()

    def cancel_ticket(self, ticket_req, ticket=None, cycle=True):

        resp = self.create_async_api_response()

        if ticket is None:
            # if EMS owner, send cancel to ems queue and change state to PENDCANCEL
            ticket_id = ticket_req['data']['id']

            try:
                ticket = self.get_ticket(ticket_id)
            except:
                resp['error'] = f'id not found: {ticket_id}'
                return resp

            ticket.last_message_id = ticket_req['id'] + 1

        if ticket.internal_state in INTERNAL_STATES.CANCELLABLE_STATES:
            if ticket.ems_owner:
                ticket.change_external_state(INTERNAL_STATES.PENDCANCEL)
                ticket.save()
                self.enqueue_ems(ticket, OMS_EMS_ACTIONS.CANCEL)
                resp['success'] = 'pending'
                resp['message'] = 'trying to cancel'
            else:
                ticket.change_internal_state(INTERNAL_STATES.CANCELED)
                ticket.save()
                resp['success'] = True
            if cycle: self.cycle_ticket(ticket)
        else:
            resp['error'] = f'Ticket cannot be cancelled: {ticket_id}'

        return resp

    def modify_ticket(self, ticket_req):

        ticket_id = ticket_req['data']['id']
        resp = self.create_async_api_response()

        try:
            ticket = self.get_ticket(ticket_id)
        except:
            resp['error'] = f'id not found: {ticket_id}'
            return resp

        ticket.last_message_id = ticket_req['id'] + 1
        ticket.save()

        resp['error'] = 'Modication not supported'
        return resp

    def create_ticket(self, ticket_req, cycle=True):

        ticket = Ticket(**ticket_req['data'])
        if ticket.oms_owner:
            self.log('WARN', 'ticket already has an oms owner', ticket.oms_owner)
        ticket.last_message_id = ticket_req['id'] + 1
        ticket.oms_owner = self.oms_id
        ticket.save()
        self.add_ticket(ticket)
        if cycle: self.cycle_ticket(ticket)

    def delete_ticket(self, ticket_req):
        # TODO
        # tell the ems to delete
        # clear the queues
        # remove from oms
        pass

    def retry_failed_settle_ticket(self, ticket:Ticket):
        """
        Retry failed ticket settlement
        """
        ticket.settlement_attempt = ticket.settlement_attempt + 1 \
            if ticket.settlement_attempt else 1
        ticket.change_internal_state(INTERNAL_STATES.PENDSETTLE)
        ticket.save()

    # =========================================================================

    def run(self):

        try:
            while not self._kill_sig:
                self.cycle()
                if isinstance(self._timeout, float): sleep_for(self._timeout)
        except KeyboardInterrupt:
            pass

        return 0


# ============================================================================

if __name__ == "__main__":
    import atexit

    atexit.register(os._exit, 0)

    # import settings

    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument('--oms-id', default='TEST_PAYMENT_OMS1')  # settings.OMS_ID)
    parser.add_argument('--oms-typ', default='CORPAY')
    parser.add_argument('--log-level', default=None)
    parser.add_argument('--regen', action='store_true', default=False)

    args = parser.parse_args()

    # ==========================

    server = OmsBase(args.oms_id, args.oms_typ, log_level=args.log_level, regen=args.regen)
    server.run()
