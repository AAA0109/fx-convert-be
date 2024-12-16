import logging
from typing import List

from dateutil.parser import parse
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.dispatch.dispatcher import Signal
from django_context_request import request

import main.libs.pubsub.publisher as pubsub
from main.apps.account.models import Company
from main.apps.corpay.models import FXBalance, Confirm
from main.apps.corpay.models.forward.update import UpdateRequest, ManualForwardRequest
from main.apps.corpay.models.fx_forwards import SpotRate
from main.apps.currency.models import FxPair, Currency
from main.apps.notification.utils.email import send_non_sellable_forward_email
from main.apps.oems.backend.states import INTERNAL_STATES
from main.apps.oems.models.ticket import Ticket

logger = logging.getLogger(__name__)
call_spot_rate = Signal()
call_book_spot_deal = Signal()
new_manual_forward = Signal()


@receiver(post_save, sender=UpdateRequest)
def update_pubsub_handler(sender, instance: UpdateRequest, created, **kwargs):
    if not created:
        return None

    if instance.type in [instance.RequestType.CASHFLOW, instance.RequestType.RISK_DETAILS]:
        pubsub.publish("hedge.forward.edit", {"cashflow_id": instance.pk})

    if instance.type == instance.RequestType.DRAWDOWN:
        pubsub.publish("hedge.forward.delete", {"cashflow_id": instance.pk})


@receiver(post_save, sender=ManualForwardRequest)
def update_pubsub_handler_ndf(sender, instance: UpdateRequest, created, **kwargs):
    if not created:
        return None

    pubsub.publish("hedge.forward.manual", {"manual": instance.pk})


@receiver(call_spot_rate)
def spot_rate_handler(response_content, **_):
    user = None
    company = None
    try:
        if request.user.is_authenticated:
            user = request.user
            company = request.user.company
    except Exception as e:
        logger.debug(f"Unable to get user from request: {e}")

    SpotRate.objects.update_or_create(
        quote_id=response_content['quoteId'],
        defaults=dict(
            user=user,
            company=company,
            rate_value=response_content['rate']['value'],
            rate_lockside=response_content['rate']['lockSide'],
            fx_pair=FxPair.get_pair(response_content['rate']['rateType']),
            rate_operation=response_content['rate']['operation'],
            payment_currency=Currency.get_currency(response_content['payment']['currency']),
            payment_amount=response_content['payment']['amount'],
            settlement_currency=Currency.get_currency(
                response_content['settlement']['currency']),
            settlement_amount=response_content['settlement']['amount'],
        )
    )


@receiver(call_book_spot_deal)
def call_book_spot_deal_handler(quote_id, order_number, **_):
    SpotRate.objects.filter(quote_id=quote_id) \
        .update(order_number=order_number)


@receiver(post_save, sender=FXBalance)
def bind_fx_balance_spot_rate_handler(instance: FXBalance, **_):
    try:
        spot_rate = SpotRate.objects.get(order_number=instance.order_number)
        spot_rate.fx_balances.add(instance)
    except SpotRate.DoesNotExist:
        pass


@receiver(new_manual_forward)
def notify_non_sellable_forward_handler(company: Company, instances: List[ManualForwardRequest], **_):
    send_non_sellable_forward_email(company, instances)


@receiver(post_save, sender=Confirm)
def create_ticket_on_confirm_save_handler(instance: Confirm, created, **_):
    if not created:
        return None

    content = instance.content
    order_number = str(content['orderDetail']['ordNum']).upper()
    qs = Ticket.objects.filter(company=instance.company, broker_id=order_number)
    if qs.exists():
        logger.warning(f"Ticket for transaction exists: {instance.company}/{order_number}")

    Ticket.objects.create(
        company=instance.company,
        internal_state=INTERNAL_STATES.MANUAL,
        side=Ticket.Sides.BUY.value if content['orderDetail']['ourAction'] == "BUY" else Ticket.Sides.SELL.value,
        value_date=parse(content['valueDate']).date(),
        buy_currency=Currency.get_currency(content['orderDetail']['buy']),
        sell_currency=Currency.get_currency(content['orderDetail']['sell']),
        broker_id=order_number,
        amount=content['orderDetail']['sellAmount'],
    )
