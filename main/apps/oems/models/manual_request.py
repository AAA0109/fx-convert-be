from typing import Optional
import uuid

from datetime import datetime, timedelta

from django.db import models
from django_extensions.db.models import TimeStampedModel
import pytz

from main.apps.core.models.choices import LockSides
from main.apps.currency.models import Currency
from main.apps.oems.models import Ticket
from main.apps.oems.models.extensions import DateTimeWithoutTZField
from main.apps.currency.models.fxpair import FxPair
from main.apps.core.utils.slack import SlackNotification
from main.apps.oems.backend.date_utils import check_after
from main.apps.oems.backend.ccy_utils import determine_rate_side
from main.apps.oems.backend.slack_utils import make_markdown_ladder, make_buttons, make_input_section

SLACK_CLIENT = None

class ManualRequest(TimeStampedModel):

    sell_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="+")
    buy_currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="+")
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="manual_request")
    # ticket = models.IntegerField(null=False)

    external_id = models.UUIDField(primary_key=False, default=uuid.uuid4)
    expiration_time = DateTimeWithoutTZField(null=True, blank=True)

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        EXPIRED = 'expired', 'Expired'
        COMPLETE = 'complete', 'Complete'
        CANCELED = 'canceled', 'Canceled'

    status = models.CharField(choices=Status.choices, default=Status.PENDING, max_length=8, )

    # LockSides = LockSides
    # lock_side = models.CharField(choices=LockSides.choices, max_length=4)
    lock_side = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="+")
    market_name = models.TextField(null=True, blank=True)
    side = models.TextField(null=True, blank=True)
    instrument_type = models.TextField(null=True, blank=True)
    action = models.TextField(null=True, blank=True)
    exec_broker = models.TextField(null=True, blank=True)
    clearing_broker = models.TextField(null=True, blank=True)
    amount = models.FloatField(null=True, blank=True)
    on_behalf_of = models.TextField(null=True, blank=True)
    fee = models.FloatField(null=True, blank=True)

    class TimeInForces(models.TextChoices):
        _15MIN = '15min', '15min'
        _1HOUR = '1hour', '1hour'
        _DAY = 'day', 'day'
        _GTC = 'gtc', 'gtc'

    time_in_force = models.CharField(choices=TimeInForces.choices, default=TimeInForces._1HOUR, max_length=5)

    value_date = models.DateField(null=True, blank=True)
    fixing_date = models.DateField(null=True, blank=True)

    # TODO: add support for B/S swaps
    far_value_date = models.DateField(null=True, blank=True)
    far_fixing_date = models.DateField(null=True, blank=True)

    ref_rate = models.FloatField(null=True, blank=True)
    fwd_points = models.FloatField(null=True, blank=True)
    booked_rate = models.FloatField(null=True, blank=True)
    booked_all_in_rate = models.FloatField(null=True, blank=True)
    booked_amount = models.FloatField(null=True, blank=True)
    booked_cntr_amount = models.FloatField(null=True, blank=True)
    booked_premium = models.FloatField(null=True, blank=True)
    broker_id = models.CharField(null=True, blank=True, max_length=256)

    exec_user = models.CharField(null=True, blank=True, max_length=40)
    slack_channel = models.CharField(null=True, blank=True, max_length=100)
    slack_ts = models.CharField(null=True, blank=True, max_length=100)
    text = models.TextField(null=True, blank=True)
    exec_text = models.TextField(null=True, blank=True)
    email_status = models.CharField(null=True, blank=True, max_length=100)
    victor_ops_id = models.CharField(null=True, blank=True)

    last_reminder_sent = models.DateTimeField(null=True)
    slack_form_link = models.CharField(null=True)

    # ================

    @classmethod
    def set_expiry( cls, tif ):

        now = datetime.utcnow()

        if tif == cls.TimeInForces._15MIN:
            return now + timedelta(minutes=15)
        elif tif == cls.TimeInForces._1HOUR:
            return now + timedelta(minutes=60)
        elif tif == cls.TimeInForces._DAY:
            # TODO: should be end of trading day
            return now + timedelta(days=1)
        elif tif == cls.TimeInForces._GTC:
            return now + timedelta(days=7)
        else:
            raise NotImplementedError

    @classmethod
    def _create(cls, **kwargs):

        kwargs['status'] = cls.Status.PENDING
        kwargs['expiration_time'] = cls.set_expiry( kwargs['time_in_force'] if 'time_in_force' in kwargs else cls.TimeInForces._DAY )

        from_ccy = Currency.objects.get(pk=kwargs['sell_currency_id'])
        to_ccy = Currency.objects.get(pk=kwargs['buy_currency_id'])
        lock_side = Currency.objects.get(pk=kwargs['lock_side_id'])

        if 'market_name' not in kwargs or not kwargs['market_name']:
            fxpair, side = determine_rate_side( from_ccy, to_ccy )
            kwargs['market_name'] = fxpair.market
            kwargs['side'] = side

        return cls(**kwargs)

    # ================

    EXPORT_BLACKLIST = { 'update_modified' }

    def export( self ):
        return { k: v for k, v in vars(self).items() if not k.startswith('_') and k not in self.EXPORT_BLACKLIST }

    def is_expired( self ):
        if check_after( self.expiration_time ):
            self.status = self.Status.EXPIRED
            self.save()
            self.close()
            return True
        return False

    def is_cancelled( self ):
        return (self.status == self.Status.CANCELED)

    def close( self ):
        if self.status == self.Status.PENDING:
            if self.booked_rate:
                self.status = self.Status.COMPLETE
            else:
                self.status = self.Status.EXPIRED
            self.save()

        if self.slack_ts:
            # TODO: could edit with a wrap-up message
            if self.status == self.Status.EXPIRED or self.status == self.Status.CANCELED:
                self.delete_slack_msg()
            else:
                text = f'{self.action} {self.side} {self.market_name} completed by {self.exec_user or "unknown"} @ {self.booked_rate} {self.booked_amount or ""}'
                new_quote_form = []
                new_quote_form.append( make_markdown_ladder({'COMPLETED': text}) )
                self.edit_slack_msg(text, new_quote_form)
        if self.victor_ops_id:
            self.resolve_victor_ops_alert()

    def get_slack_client( self ):
        global SLACK_CLIENT
        if SLACK_CLIENT is None:
            SLACK_CLIENT = SlackNotification()
        return SLACK_CLIENT

    def send_slack_msg( self, text, blocks, channel ):
        if not channel:
            raise
        sn = self.get_slack_client()
        resp = sn.send_blocks(channel=channel, text=text, blocks=blocks, return_data=True)
        if resp:
            self.slack_channel = resp['channel']
            self.slack_ts = resp['ts']
            self.save()

    def edit_slack_msg( self, text, blocks ):
        if not self.slack_channel or not self.slack_ts:
            return None # ERROR
        sn = self.get_slack_client()
        sn.edit_message(channel=self.slack_channel, thread_ts=self.slack_ts, text=text, blocks=blocks)

    def delete_slack_msg( self ):
        if not self.slack_channel or not self.slack_ts:
            return None # ERROR
        sn = self.get_slack_client()
        sn.delete_message(channel=self.slack_channel, thread_ts=self.slack_ts)
        self.save()

    def resolve_victor_ops_alert( self ):
        if self.victor_ops_id and self.victor_ops_id != 'ERROR':
            pass # kill the alert

    def send_victor_ops_alert( self, msg, routing_key='EXEC_DESK', entity_display_name="from Pangea Exec Desk. ", **kwargs ):
        req = call_victor_ops(msg=msg, routing_key=routing_key, entity_display_name=entity_display_name, **kwargs)
        try:
            entity_id = req.json()['entity_id']
        except:
            entity_id = "ERROR"

        self.victor_ops_id = entity_id
        self.save()

    def send_email_alert( self ):
        pass

    def get_manual_request_permalink(self) -> Optional[str]:
        if not self.slack_channel or not self.slack_ts:
            return None # ERROR
        sn = self.get_slack_client()
        resp = sn.get_permalink(channel=self.slack_channel, thread_ts=self.slack_ts)
        if resp:
            return resp.get('permalink', None)
        return None

    def send_reminder_msg( self, text, blocks, channel ) -> dict:
        if not channel:
            raise
        sn = self.get_slack_client()
        return sn.send_blocks(channel=channel, text=text, blocks=blocks, return_data=True)

    def update_reminder_time(self) -> None:
        self.last_reminder_sent = datetime.now(tz=pytz.UTC)
        self.save()

    def upsert_manual_request_form_link(self) -> Optional[None]:
        if self.slack_form_link:
            return self.slack_form_link

        if self.slack_channel and self.slack_ts:
            resp = self.get_manual_request_permalink()
            self.slack_form_link = resp
            self.save()
            return resp
        return None

