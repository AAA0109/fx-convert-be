from typing import Any, List

from django.db import models
import main.libs.pubsub.publisher as publisher
import main.apps.core.utils.klass as klass
from main.apps.account.models.user import User
from main.apps.account.models.account import Account
from main.apps.account.models.company import Company
from main.apps.broker.models.broker import Broker, BrokerAccount
from main.apps.account.models.cashflow import CashFlow
from main.apps.account.models.installment_cashflow import InstallmentCashflow
import django.db.models.signals


# It is a bad idea to have a universal handler here, since Django uses
# the database to save some bookkeeping stuff, so instead we create
# Custom handlers per class


def post_save(senders: List['Any'], **kwargs):
    """
    A decorator for connecting receivers to post_save signal. Used by passing a list of senders to filter on::

        @post_save([Sender1, Sender2...])
        def signal_receiver(sender, **kwargs):
            ...
    """

    def _decorator(func):
        for s in senders:
            django.db.models.signals.post_save.connect(func, sender=s, **kwargs)

        return func

    return _decorator


@post_save([User,
            Account,
            Company,
            Broker,
            BrokerAccount,
            CashFlow,
            InstallmentCashflow])
def user_pubsub_handler(sender, instance, created, **kwargs):
    """
    This is a Pub/Sub :class:`receiver` for model DB events.

    The handler will publish a routing key set to DB.{qualified_class_name} for all DB events.
    """
    cls = klass.fullname(instance),
    data = {
        "id": instance.id,
        "instance": cls,
        "created": created
    }
    # we send 'created' as an attribute to allow filtering on it
    publisher.publish(f"DB.{cls}", data, created=str(created))
